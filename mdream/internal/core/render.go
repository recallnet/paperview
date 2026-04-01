package core

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
)

const shortLimit = 500

func BuildStoredResult(resultID string, command string, sessionID string, summary string, kind string, payload map[string]any, totalItems int, options OutputOptions) StoredResult {
	stored := StoredResult{
		ResultID:   resultID,
		SessionID:  sessionID,
		Command:    command,
		Summary:    summary,
		Kind:       kind,
		Page:       options.Page,
		PageSize:   options.PageSize,
		TotalItems: totalItems,
		Data:       map[string]any{},
	}
	if items, ok := payload["items"].([]map[string]any); ok {
		start, end, nextPage := pageBounds(len(items), options.Page, options.PageSize)
		stored.Data["items"] = items[start:end]
		stored.NextPage = nextPage
		stored.Truncated = !options.Full && (nextPage > 0 || len(summary) > shortLimit)
	} else if genericItems, ok := payload["items"].([]any); ok {
		start, end, nextPage := pageBounds(len(genericItems), options.Page, options.PageSize)
		stored.Data["items"] = genericItems[start:end]
		stored.NextPage = nextPage
		stored.Truncated = !options.Full && (nextPage > 0 || len(summary) > shortLimit)
	}
	for key, value := range payload {
		if key == "items" {
			continue
		}
		stored.Data[key] = value
	}
	if !options.Full && len(stored.Data) == 0 {
		stored.Truncated = len(summary) > shortLimit
	}
	return stored
}

func RenderStoredResult(stored StoredResult, options OutputOptions) (string, error) {
	if options.JSON {
		payload := stored
		if !options.Full {
			payload.Summary = TruncateString(payload.Summary, shortLimit)
		}
		raw, err := json.MarshalIndent(payload, "", "  ")
		if err != nil {
			return "", err
		}
		return string(raw), nil
	}
	summary := stored.Summary
	if !options.Full {
		summary = TruncateString(summary, shortLimit)
	}
	var lines []string
	lines = append(lines, summary)
	lines = append(lines, fmt.Sprintf("result_id=%s", stored.ResultID))
	if stored.SessionID != "" {
		lines = append(lines, fmt.Sprintf("session_id=%s", stored.SessionID))
	}
	if stored.TotalItems > 0 {
		lines = append(lines, fmt.Sprintf("items=%d page=%d page_size=%d", stored.TotalItems, stored.Page, stored.PageSize))
	}
	if stored.NextPage > 0 {
		lines = append(lines, fmt.Sprintf("next: mdream result get --result-id %s --page %d", stored.ResultID, stored.NextPage))
	}
	if stored.Truncated {
		lines = append(lines, fmt.Sprintf("full: mdream result get --result-id %s --full", stored.ResultID))
	}
	return strings.Join(lines, "\n"), nil
}

func pageBounds(total int, page int, pageSize int) (int, int, int) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 5
	}
	start := (page - 1) * pageSize
	if start > total {
		start = total
	}
	end := start + pageSize
	if end > total {
		end = total
	}
	next := 0
	if end < total {
		next = page + 1
	}
	return start, end, next
}

func SummarizeList(kind string, items []map[string]any) string {
	if len(items) == 0 {
		return fmt.Sprintf("%s: no results", kind)
	}
	var parts []string
	limit := len(items)
	if limit > 3 {
		limit = 3
	}
	for _, item := range items[:limit] {
		keys := preferredKeys(item)
		var fields []string
		for _, key := range keys {
			if value, ok := item[key]; ok && fmt.Sprint(value) != "" {
				fields = append(fields, fmt.Sprintf("%s=%v", key, value))
			}
		}
		parts = append(parts, strings.Join(fields, " "))
	}
	return fmt.Sprintf("%s: %d result(s). %s", kind, len(items), strings.Join(parts, " | "))
}

func preferredKeys(item map[string]any) []string {
	preferred := []string{"paper_id", "title", "section_label", "lane_family", "shortlist_id", "publication_item_id", "board_rank", "index_rank", "ledger_rank", "diamond_score", "top_lane", "pattern_id", "packet_kind"}
	keys := make([]string, 0, len(item))
	for _, key := range preferred {
		if _, ok := item[key]; ok {
			keys = append(keys, key)
		}
	}
	if len(keys) > 0 {
		return keys
	}
	for key := range item {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	if len(keys) > 5 {
		keys = keys[:5]
	}
	return keys
}
