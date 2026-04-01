package core

import (
	"database/sql"
	"encoding/json"
	"fmt"
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
