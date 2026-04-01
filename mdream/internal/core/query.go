package core

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
)

func QueryRows(db *sql.DB, query string, args ...any) ([]map[string]any, error) {
	rows, err := db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, err
	}
	results := make([]map[string]any, 0)
	for rows.Next() {
		values := make([]any, len(columns))
		valuePointers := make([]any, len(columns))
		for i := range columns {
			valuePointers[i] = &values[i]
		}
		if err := rows.Scan(valuePointers...); err != nil {
			return nil, err
		}
		item := make(map[string]any, len(columns))
		for i, column := range columns {
			item[column] = normalizeSQLValue(values[i])
		}
		results = append(results, item)
	}
	return results, rows.Err()
}

func normalizeSQLValue(value any) any {
	switch typed := value.(type) {
	case []byte:
		return string(typed)
	default:
		return typed
	}
}

func LatestRunID(db *sql.DB, table string) (string, error) {
	query := fmt.Sprintf(`SELECT run_id FROM %s GROUP BY run_id ORDER BY MAX(created_at) DESC, run_id DESC LIMIT 1`, table)
	row := db.QueryRow(query)
	var runID string
	if err := row.Scan(&runID); err != nil {
		return "", err
	}
	return runID, nil
}

func ShortJSON(value any, limit int) string {
	payload, _ := json.Marshal(value)
	return TruncateString(string(payload), limit)
}

func TruncateString(value string, limit int) string {
	if limit <= 0 || len(value) <= limit {
		return value
	}
	if limit <= 3 {
		return value[:limit]
	}
	return value[:limit-3] + "..."
}

func LowerLikeQuery(query string) string {
	return "%" + strings.ToLower(strings.TrimSpace(query)) + "%"
}

var tokenSplitPattern = regexp.MustCompile(`[^a-z0-9]+`)

func QueryTokens(query string) []string {
	lowered := strings.ToLower(strings.TrimSpace(query))
	raw := tokenSplitPattern.Split(lowered, -1)
	stopwords := map[string]struct{}{
		"a": {}, "an": {}, "and": {}, "as": {}, "at": {}, "be": {}, "could": {}, "do": {}, "find": {}, "for": {},
		"from": {}, "had": {}, "hadn": {}, "in": {}, "is": {}, "it": {}, "me": {}, "new": {}, "not": {}, "of": {},
		"on": {}, "or": {}, "paper": {}, "realized": {}, "strategy": {}, "surprising": {}, "that": {}, "the": {},
		"this": {}, "to": {}, "trade": {}, "work": {}, "but": {},
	}
	seen := map[string]struct{}{}
	tokens := make([]string, 0, len(raw))
	for _, token := range raw {
		if len(token) < 3 {
			continue
		}
		if _, blocked := stopwords[token]; blocked {
			continue
		}
		if _, exists := seen[token]; exists {
			continue
		}
		seen[token] = struct{}{}
		tokens = append(tokens, token)
	}
	return tokens
}

func ExpandResearchTokens(query string) []string {
	base := QueryTokens(query)
	// @context decision Keep domain-specific prompt terms like "prediction" and
	// "volume" in the token stream. The discovery CLI relies on them to trigger
	// market-specific expansions; stripping them makes broad strategy prompts miss
	// the exact venues and failure modes the agent is trying to uncover.
	extra := map[string][]string{
		"prediction":         {"predictions", "kalshi", "polymarket", "limitless", "event", "binary"},
		"market":             {"markets", "trading", "venue", "exchange"},
		"markets":            {"market", "trading", "venue", "exchange"},
		"low":                {"thin", "illiquid", "sparse"},
		"volume":             {"thin", "illiquid", "liquidity"},
		"unprofessionalized": {"immature", "early", "bootstrap", "retail", "weakly", "arbitraged"},
		"settlement":         {"resolution", "collateral", "margin", "liquidation", "clearing"},
		"repair":             {"parity", "convergence", "delayed", "recovery"},
		"state":              {"graph", "linked", "inconsistency", "basis"},
		"toxic":              {"flow", "imbalance", "manipulation", "sweep"},
		"parity":             {"repair", "mispricing", "cross-market", "basis"},
		"delay":              {"lag", "latency", "slow", "deferred"},
		"delayed":            {"lag", "latency", "slow", "deferred"},
		"thin":               {"low", "volume", "illiquid"},
		"illiquid":           {"thin", "low", "volume"},
		"auction":            {"uncrossing", "handoff", "opening", "closing"},
		"maker":              {"liquidity", "withdrawal", "quote", "retreat"},
	}
	seen := map[string]struct{}{}
	all := make([]string, 0, len(base)+8)
	for _, token := range base {
		if _, ok := seen[token]; !ok {
			seen[token] = struct{}{}
			all = append(all, token)
		}
		if expansions, ok := extra[token]; ok {
			for _, expansion := range expansions {
				if _, exists := seen[expansion]; !exists {
					seen[expansion] = struct{}{}
					all = append(all, expansion)
				}
			}
		}
	}
	return all
}
