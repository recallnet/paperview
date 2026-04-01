package app

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

type discoverLead struct {
	ID                string
	LeadType          string
	Title             string
	LaneFamily        string
	Source            string
	PaperID           string
	PublicationItemID string
	MatchScore        float64
	AgentPriority     float64
	ScoreBreakdown    map[string]float64
	Reason            string
	NextStep          string
}

func newDiscoverCommand() *cobra.Command {
	discoverCmd := &cobra.Command{
		Use:   "discover",
		Short: "Run prompt-driven discovery rounds over the paperview corpus",
	}

	var prompt string
	var limit int
	var paperLimit int
	var sectionLimit int
	var newSession bool
	var allowRepeats bool
	var label string
	var maxDate string
	roundCmd := &cobra.Command{
		Use:   "round",
		Short: "Run one discovery round and store the surfaced leads",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			activePrompt := strings.TrimSpace(prompt)
			if activePrompt == "" {
				return fmt.Errorf("prompt must not be empty")
			}
			sessionID, sessionMode, err := resolveDiscoverSession(runtime, label, activePrompt, newSession)
			if err != nil {
				return err
			}
			tokens := core.ExpandResearchTokens(activePrompt)
			if len(tokens) == 0 {
				tokens = []string{strings.ToLower(activePrompt)}
			}
			focusTokens := discoverFocusTokens(activePrompt)
			seenLeadIDs, roundIndex, err := discoverHistory(runtime.StoreDB, sessionID)
			if err != nil {
				return err
			}

			paperHits, err := discoverPaperHits(runtime.SourceDB, tokens, paperLimit, maxDate)
			if err != nil {
				return err
			}
			sectionHits, err := discoverSectionHits(runtime.SourceDB, tokens, sectionLimit, maxDate)
			if err != nil {
				return err
			}
			surfaceHits, err := discoverSurfaceHits(runtime.SourceDB, tokens, limit*2)
			if err != nil {
				return err
			}
			leads := mergeDiscoverLeads(surfaceHits, paperHits, sectionHits, focusTokens, seenLeadIDs, limit, allowRepeats)
			payloadItems := make([]map[string]any, 0, len(leads))
			for _, lead := range leads {
				payloadItems = append(payloadItems, map[string]any{
					"lead_id":              lead.ID,
					"lead_type":            lead.LeadType,
					"title":                lead.Title,
					"lane_family":          lead.LaneFamily,
					"source":               lead.Source,
					"paper_id":             lead.PaperID,
					"publication_item_id":  lead.PublicationItemID,
					"match_score":          lead.MatchScore,
					"agent_priority_score": lead.AgentPriority,
					"score_breakdown":      lead.ScoreBreakdown,
					"reason":               lead.Reason,
					"next_step":            lead.NextStep,
				})
			}
			nextCommands := buildNextCommands(sessionID, leads)
			summary := buildDiscoverSummary(sessionID, activePrompt, leads, roundIndex)
			payload := map[string]any{
				"items":               payloadItems,
				"prompt":              activePrompt,
				"tokens":              tokens,
				"session_id":          sessionID,
				"session_mode":        sessionMode,
				"round_index":         roundIndex,
				"paper_hits":          paperHits,
				"section_hits":        sectionHits,
				"surface_hits":        surfaceHits,
				"next_commands":       nextCommands,
				"candidate_diversity": candidateDiversity(payloadItems),
			}
			// @context decision Persist all raw supporting hit sets under the
			// discover round so the agent can continue from stored result IDs alone.
			// This keeps the CLI session-based instead of forcing the user back to
			// ad hoc local files or manual SQL when refining a lead.
			return emitAndStoreWithSession(cmd, sessionID, "discover_round", summary, payload, len(payloadItems), map[string]any{
				"prompt":        activePrompt,
				"tokens":        tokens,
				"limit":         limit,
				"paper_limit":   paperLimit,
				"section_limit": sectionLimit,
				"allow_repeats": allowRepeats,
				"max_date":      maxDate,
				"round_index":   roundIndex,
			})
		},
	}
	roundCmd.Flags().StringVar(&prompt, "prompt", "", "Research prompt for this discovery round")
	roundCmd.Flags().IntVar(&limit, "limit", 10, "Maximum surfaced leads")
	roundCmd.Flags().IntVar(&paperLimit, "paper-limit", 12, "Maximum paper matches to consider")
	roundCmd.Flags().IntVar(&sectionLimit, "section-limit", 12, "Maximum section matches to consider")
	roundCmd.Flags().BoolVar(&newSession, "new-session", false, "Force creation of a new session instead of continuing the current one")
	roundCmd.Flags().BoolVar(&allowRepeats, "allow-repeats", false, "Allow previously surfaced leads to compete normally instead of backfilling only when new leads run out")
	roundCmd.Flags().StringVar(&label, "label", "", "Optional label when auto-creating a session")
	roundCmd.Flags().StringVar(&maxDate, "max-date", "2023-12-31", "Only consider papers published on or before this date")
	_ = roundCmd.MarkFlagRequired("prompt")

	discoverCmd.AddCommand(roundCmd)
	return discoverCmd
}

func resolveDiscoverSession(runtime *core.Runtime, label string, prompt string, newSession bool) (string, string, error) {
	if runtime.Output.Session != "" && !newSession {
		return runtime.Output.Session, "continued", nil
	}
	sessionLabel := strings.TrimSpace(label)
	if sessionLabel == "" {
		sessionLabel = core.TruncateString(prompt, 48)
	}
	sessionID, err := core.CreateSession(runtime.StoreDB, sessionLabel, prompt, runtime.SourcePath)
	if err != nil {
		return "", "", err
	}
	return sessionID, "created", nil
}

func discoverHistory(db *sql.DB, sessionID string) (map[string]struct{}, int, error) {
	rows, err := core.QueryRows(db, `SELECT payload_json FROM query_results WHERE session_id = ? AND kind = 'discover_round' ORDER BY created_at DESC LIMIT 20`, sessionID)
	if err != nil {
		return nil, 0, err
	}
	seen := map[string]struct{}{}
	for _, row := range rows {
		payloadRaw, _ := row["payload_json"].(string)
		if payloadRaw == "" {
			continue
		}
		var payload map[string]any
		if err := json.Unmarshal([]byte(payloadRaw), &payload); err != nil {
			continue
		}
		items, _ := payload["items"].([]any)
		for _, item := range items {
			entry, _ := item.(map[string]any)
			if leadID := strings.TrimSpace(fmt.Sprint(entry["lead_id"])); leadID != "" {
				seen[leadID] = struct{}{}
			}
		}
	}
	return seen, len(rows) + 1, nil
}

func discoverPaperHits(db *sql.DB, tokens []string, limit int, maxDate string) ([]map[string]any, error) {
	scoreExpr, whereExpr, args := tokenizedPaperSearch(tokens)
	args = append(args, maxDate, limit)
	return core.QueryRows(db, fmt.Sprintf(`
SELECT
  paper_id,
  title,
  primary_category,
  published_at,
  (%s) AS lexical_score,
  (
    SELECT ds.diamond_score
    FROM diamond_scores ds
    WHERE ds.paper_id = papers.paper_id
    ORDER BY ds.created_at DESC, ds.run_id DESC
    LIMIT 1
  ) AS diamond_score,
  (
    SELECT ds.top_lane
    FROM diamond_scores ds
    WHERE ds.paper_id = papers.paper_id
    ORDER BY ds.created_at DESC, ds.run_id DESC
    LIMIT 1
  ) AS top_lane,
  substr(replace(replace(COALESCE(abstract, ''), char(10), ' '), char(13), ' '), 1, 280) AS abstract_snippet
FROM papers
WHERE (%s)
  AND COALESCE(published_at, '') <= ?
ORDER BY lexical_score DESC, COALESCE(published_at, '') DESC, paper_id
LIMIT ?`, scoreExpr, whereExpr), args...)
}

func discoverSectionHits(db *sql.DB, tokens []string, limit int, maxDate string) ([]map[string]any, error) {
	scoreExpr, whereExpr, args := tokenizedSectionSearch(tokens)
	args = append(args, maxDate, limit)
	return core.QueryRows(db, fmt.Sprintf(`
SELECT
  ps.section_id,
  ps.paper_id,
  p.title,
  ps.section_label,
  ps.section_order,
  (%s) AS lexical_score,
  substr(replace(replace(ps.content_text, char(10), ' '), char(13), ' '), 1, 280) AS snippet
FROM paper_sections ps
JOIN papers p ON p.paper_id = ps.paper_id
WHERE (%s)
  AND lower(COALESCE(ps.section_label, '')) NOT IN ('front_matter', 'references')
  AND COALESCE(p.published_at, '') <= ?
ORDER BY lexical_score DESC, COALESCE(p.published_at, '') DESC, ps.paper_id, ps.section_order
LIMIT ?`, scoreExpr, whereExpr), args...)
}

func discoverSurfaceHits(db *sql.DB, tokens []string, limit int) ([]map[string]any, error) {
	runID, err := core.LatestRunID(db, "diamond_board_entries")
	if err != nil {
		return nil, err
	}
	scoreExpr, whereExpr, scoreArgs, whereArgs := tokenizedDiscoverSurfaceSearch(tokens)
	finalArgs := append([]any{}, scoreArgs...)
	finalArgs = append(finalArgs, runID)
	finalArgs = append(finalArgs, whereArgs...)
	finalArgs = append(finalArgs, limit)
	return core.QueryRows(db, fmt.Sprintf(`
SELECT
  publication_item_id,
  lane_family,
  source_surface,
  confidence,
  title,
  result_summary,
  modern_equivalent,
  first_test,
  gap_to_close,
  board_rank,
  (%s) AS match_score
FROM diamond_board_entries
WHERE run_id = ?
  AND (%s)
ORDER BY match_score DESC, board_rank ASC
LIMIT ?`, scoreExpr, whereExpr), finalArgs...)
}

func tokenizedDiscoverSurfaceSearch(tokens []string) (string, string, []any, []any) {
	scoreParts := make([]string, 0, len(tokens)*5)
	whereParts := make([]string, 0, len(tokens))
	scoreArgs := make([]any, 0, len(tokens)*5)
	whereArgs := make([]any, 0, len(tokens))
	for _, token := range tokens {
		like := "%" + token + "%"
		scoreParts = append(scoreParts,
			"CASE WHEN lower(COALESCE(title, '')) LIKE ? THEN 5 ELSE 0 END",
			"CASE WHEN lower(COALESCE(result_summary, '')) LIKE ? THEN 4 ELSE 0 END",
			"CASE WHEN lower(COALESCE(modern_equivalent, '')) LIKE ? THEN 4 ELSE 0 END",
			"CASE WHEN lower(COALESCE(first_test, '')) LIKE ? THEN 3 ELSE 0 END",
			"CASE WHEN lower(COALESCE(gap_to_close, '')) LIKE ? THEN 2 ELSE 0 END",
		)
		scoreArgs = append(scoreArgs, like, like, like, like, like)
		whereParts = append(whereParts, "lower(COALESCE(title, '') || ' ' || COALESCE(result_summary, '') || ' ' || COALESCE(modern_equivalent, '') || ' ' || COALESCE(first_test, '') || ' ' || COALESCE(gap_to_close, '')) LIKE ?")
		whereArgs = append(whereArgs, like)
	}
	return strings.Join(scoreParts, " + "), strings.Join(whereParts, " OR "), scoreArgs, whereArgs
}

func mergeDiscoverLeads(surfaceHits []map[string]any, paperHits []map[string]any, sectionHits []map[string]any, focusTokens []string, seenLeadIDs map[string]struct{}, limit int, allowRepeats bool) []discoverLead {
	leadMap := map[string]discoverLead{}
	for _, row := range surfaceHits {
		id := normalizeSurfaceLeadID(fmt.Sprint(row["lane_family"]), fmt.Sprint(row["title"]), fmt.Sprint(row["modern_equivalent"]))
		breakdown := map[string]float64{
			"surface_bonus":      40,
			"match":              toFloat(row["match_score"]),
			"rank_bonus":         rankBonus(toFloat(row["board_rank"])),
			"confidence_bonus":   confidenceBonus(fmt.Sprint(row["confidence"])),
			"executability":      executabilityBonus(fmt.Sprint(row["modern_equivalent"]), fmt.Sprint(row["first_test"]), fmt.Sprint(row["gap_to_close"])),
			"focus_bonus":        laneFocusBonus(fmt.Sprint(row["lane_family"]), focusTokens),
			"section_support":    0,
			"repeat_penalty":     0,
			"prompt_fit_penalty": 0,
		}
		lead := discoverLead{
			ID:                id,
			LeadType:          "surface",
			Title:             fmt.Sprint(row["title"]),
			LaneFamily:        fmt.Sprint(row["lane_family"]),
			Source:            fmt.Sprint(row["source_surface"]),
			PublicationItemID: fmt.Sprint(row["publication_item_id"]),
			MatchScore:        toFloat(row["match_score"]),
			AgentPriority:     sumBreakdown(breakdown),
			ScoreBreakdown:    breakdown,
			Reason:            fmt.Sprintf("%s Modern equivalent: %s", strings.TrimSpace(fmt.Sprint(row["result_summary"])), strings.TrimSpace(fmt.Sprint(row["modern_equivalent"]))),
			NextStep:          fmt.Sprintf("mdream surface get --surface diamond-board --item-id %s --full", fmt.Sprint(row["publication_item_id"])),
		}
		if existing, exists := leadMap[id]; !exists || lead.AgentPriority > existing.AgentPriority {
			leadMap[id] = lead
		}
	}
	for _, row := range paperHits {
		id := fmt.Sprintf("paper:%v", row["paper_id"])
		breakdown := map[string]float64{
			"lexical":            toFloat(row["lexical_score"]),
			"diamond_score":      toFloat(row["diamond_score"]) * 25,
			"top_lane_bonus":     laneFocusBonus(fmt.Sprint(row["top_lane"]), focusTokens),
			"focus_bonus":        focusTextBonus(fmt.Sprint(row["title"])+" "+fmt.Sprint(row["abstract_snippet"]), focusTokens),
			"section_support":    0,
			"repeat_penalty":     0,
			"prompt_fit_penalty": 0,
		}
		existing, exists := leadMap[id]
		lead := discoverLead{
			ID:             id,
			LeadType:       "paper",
			Title:          fmt.Sprint(row["title"]),
			LaneFamily:     fmt.Sprint(row["top_lane"]),
			Source:         "paper_search",
			PaperID:        fmt.Sprint(row["paper_id"]),
			MatchScore:     toFloat(row["lexical_score"]),
			AgentPriority:  sumBreakdown(breakdown),
			ScoreBreakdown: breakdown,
			Reason:         strings.TrimSpace(fmt.Sprint(row["abstract_snippet"])),
			NextStep:       fmt.Sprintf("mdream paper get --paper-id %s --full", fmt.Sprint(row["paper_id"])),
		}
		if !exists || lead.AgentPriority > existing.AgentPriority {
			leadMap[id] = lead
		}
	}
	for _, row := range sectionHits {
		id := fmt.Sprintf("paper:%v", row["paper_id"])
		sectionReason := fmt.Sprintf("Section %v: %s", row["section_label"], strings.TrimSpace(fmt.Sprint(row["snippet"])))
		existing, exists := leadMap[id]
		if exists {
			sectionSupport := toFloat(row["lexical_score"]) * 0.35
			existing.AgentPriority += sectionSupport
			existing.ScoreBreakdown["section_support"] += sectionSupport
			if !strings.Contains(existing.Reason, sectionReason) {
				existing.Reason = core.TruncateString(existing.Reason+" "+sectionReason, 420)
			}
			existing.NextStep = fmt.Sprintf("mdream paper sections --paper-id %s --full", fmt.Sprint(row["paper_id"]))
			leadMap[id] = existing
			continue
		}
		leadMap[id] = discoverLead{
			ID:            id,
			LeadType:      "paper",
			Title:         fmt.Sprint(row["title"]),
			Source:        "section_search",
			PaperID:       fmt.Sprint(row["paper_id"]),
			MatchScore:    toFloat(row["lexical_score"]),
			AgentPriority: toFloat(row["lexical_score"]) * 0.75,
			ScoreBreakdown: map[string]float64{
				"lexical":            toFloat(row["lexical_score"]) * 0.75,
				"diamond_score":      0,
				"top_lane_bonus":     0,
				"focus_bonus":        0,
				"section_support":    0,
				"repeat_penalty":     0,
				"prompt_fit_penalty": 0,
			},
			Reason:   sectionReason,
			NextStep: fmt.Sprintf("mdream paper sections --paper-id %s --full", fmt.Sprint(row["paper_id"])),
		}
	}

	primaryLeads := make([]discoverLead, 0, len(leadMap))
	seenLeads := make([]discoverLead, 0, len(leadMap))
	for _, lead := range leadMap {
		if lead.LeadType == "paper" && len(focusTokens) > 0 && !matchesAnyToken(lead.Title+" "+lead.Reason, focusTokens) {
			penalty := lead.AgentPriority * 0.45
			lead.AgentPriority -= penalty
			lead.ScoreBreakdown["prompt_fit_penalty"] -= penalty
			lead.Reason = "Weak prompt-specific match. " + lead.Reason
		}
		if _, seen := seenLeadIDs[lead.ID]; seen {
			penalty := lead.AgentPriority * 0.45
			lead.AgentPriority -= penalty
			lead.ScoreBreakdown["repeat_penalty"] -= penalty
			lead.Reason = "Repeated from an earlier discovery round. " + lead.Reason
			if shouldCarryForwardSeenLead(lead) {
				primaryLeads = append(primaryLeads, lead)
				continue
			}
			seenLeads = append(seenLeads, lead)
			continue
		}
		primaryLeads = append(primaryLeads, lead)
	}

	sortDiscoverLeads(primaryLeads)
	sortDiscoverLeads(seenLeads)

	if allowRepeats {
		leads := append(primaryLeads, seenLeads...)
		sortDiscoverLeads(leads)
		if len(leads) > limit {
			leads = leads[:limit]
		}
		return leads
	}

	// @context decision Continuing a session should surface new candidate families
	// before repeating already-seen leads. Without this novelty-first backfill
	// policy, follow-up rounds collapse into the same top packets and the agent
	// stops making exploratory progress even when fresh, lower-score leads exist.
	leads := append([]discoverLead{}, primaryLeads...)
	if len(leads) < limit {
		remaining := limit - len(leads)
		leads = append(leads, seenLeads[:minInt(remaining, len(seenLeads))]...)
	}
	if len(leads) > limit {
		leads = leads[:limit]
	}
	return leads
}

func sortDiscoverLeads(leads []discoverLead) {
	sort.SliceStable(leads, func(i, j int) bool {
		if leads[i].AgentPriority == leads[j].AgentPriority {
			return leads[i].Title < leads[j].Title
		}
		return leads[i].AgentPriority > leads[j].AgentPriority
	})
}

func shouldCarryForwardSeenLead(lead discoverLead) bool {
	if lead.LeadType != "surface" {
		return false
	}
	if lead.MatchScore < 40 {
		return false
	}
	return lead.ScoreBreakdown["executability"] >= 12
}

func buildDiscoverSummary(sessionID string, prompt string, leads []discoverLead, roundIndex int) string {
	if len(leads) == 0 {
		return fmt.Sprintf("discover_round: session_id=%s round=%d prompt=%q produced no leads", sessionID, roundIndex, prompt)
	}
	topTitles := make([]string, 0, minInt(3, len(leads)))
	for _, lead := range leads[:minInt(3, len(leads))] {
		topTitles = append(topTitles, lead.Title)
	}
	return fmt.Sprintf("discover_round: session_id=%s round=%d %d lead(s). top=%s", sessionID, roundIndex, len(leads), strings.Join(topTitles, " | "))
}

func buildNextCommands(sessionID string, leads []discoverLead) []string {
	commands := []string{
		fmt.Sprintf("mdream note add --session-id %s --kind finding --text '<why this round matters>'", sessionID),
		fmt.Sprintf("mdream --session %s discover round --prompt '<refined prompt>'", sessionID),
	}
	for _, lead := range leads[:minInt(3, len(leads))] {
		commands = append(commands, lead.NextStep)
	}
	return commands
}

func candidateDiversity(items []map[string]any) map[string]int {
	diversity := map[string]int{}
	for _, item := range items {
		lane := strings.TrimSpace(fmt.Sprint(item["lane_family"]))
		if lane == "" {
			lane = "paper_search"
		}
		diversity[lane]++
	}
	return diversity
}

func sumBreakdown(parts map[string]float64) float64 {
	total := 0.0
	for _, value := range parts {
		total += value
	}
	return total
}

func confidenceBonus(value string) float64 {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "high":
		return 10
	case "medium":
		return 6
	case "low":
		return 2
	default:
		return 0
	}
}

func executabilityBonus(modernEquivalent string, firstTest string, gapToClose string) float64 {
	bonus := 0.0
	if strings.TrimSpace(modernEquivalent) != "" {
		bonus += 4
	}
	if strings.TrimSpace(firstTest) != "" {
		bonus += 8
	}
	if strings.TrimSpace(gapToClose) != "" {
		bonus += 4
	}
	return bonus
}

func laneFocusBonus(lane string, focusTokens []string) float64 {
	if lane == "" || len(focusTokens) == 0 {
		return 0
	}
	return focusTextBonus(lane, focusTokens)
}

func focusTextBonus(text string, focusTokens []string) float64 {
	if len(focusTokens) == 0 {
		return 0
	}
	lowered := strings.ToLower(text)
	bonus := 0.0
	for _, token := range focusTokens {
		if strings.Contains(lowered, token) {
			bonus += 4
		}
	}
	return bonus
}

func rankBonus(rank float64) float64 {
	if rank <= 0 {
		return 0
	}
	return 6.0 / rank
}

func toFloat(value any) float64 {
	switch typed := value.(type) {
	case float64:
		return typed
	case int64:
		return float64(typed)
	case int:
		return float64(typed)
	case string:
		parsed, err := strconv.ParseFloat(typed, 64)
		if err == nil {
			return parsed
		}
		var scanned float64
		fmt.Sscanf(typed, "%f", &scanned)
		return scanned
	default:
		return 0
	}
}

func minInt(a int, b int) int {
	if a < b {
		return a
	}
	return b
}

func normalizeSurfaceLeadID(lane string, title string, modernEquivalent string) string {
	squash := func(value string) string {
		value = strings.ToLower(strings.TrimSpace(value))
		value = strings.ReplaceAll(value, " ", "-")
		value = strings.ReplaceAll(value, ":", "")
		return value
	}
	return fmt.Sprintf("surface:%s:%s:%s", squash(lane), squash(title), squash(modernEquivalent))
}

func discoverFocusTokens(prompt string) []string {
	base := core.QueryTokens(prompt)
	blocked := map[string]struct{}{
		"early": {}, "exchange": {}, "illiquid": {}, "liquidity": {}, "low": {}, "market": {}, "markets": {},
		"sparse": {}, "thin": {}, "trading": {}, "unprofessionalized": {}, "venue": {}, "volume": {},
	}
	focus := make([]string, 0, len(base))
	for _, token := range base {
		if _, skip := blocked[token]; skip {
			continue
		}
		focus = append(focus, token)
	}
	return focus
}

func matchesAnyToken(text string, tokens []string) bool {
	lowered := strings.ToLower(text)
	for _, token := range tokens {
		if strings.Contains(lowered, token) {
			return true
		}
	}
	return false
}
