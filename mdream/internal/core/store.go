package core

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
)

type StoredResult struct {
	ResultID   string         `json:"result_id"`
	SessionID  string         `json:"session_id,omitempty"`
	Command    string         `json:"command"`
	Summary    string         `json:"summary"`
	Kind       string         `json:"kind"`
	Truncated  bool           `json:"truncated"`
	Page       int            `json:"page"`
	PageSize   int            `json:"page_size"`
	TotalItems int            `json:"total_items"`
	NextPage   int            `json:"next_page,omitempty"`
	Data       map[string]any `json:"data,omitempty"`
}

func EnsureStoreSchema(db *sql.DB) error {
	_, err := db.Exec(`
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value_text TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  label TEXT,
  prompt TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  source_db_path TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
  note_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  text TEXT NOT NULL,
  paper_id TEXT,
  result_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hypotheses (
  hypothesis_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  title TEXT NOT NULL,
  hypothesis_text TEXT NOT NULL,
  target_market TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS query_results (
  result_id TEXT PRIMARY KEY,
  session_id TEXT,
  command TEXT NOT NULL,
  args_json TEXT NOT NULL DEFAULT '{}',
  kind TEXT NOT NULL,
  summary_text TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  total_items INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_query_results_session ON query_results(session_id, created_at DESC);
`)
	return err
}

func UpsertSetting(db *sql.DB, key string, value string) error {
	_, err := db.Exec(
		`INSERT INTO settings(key, value_text, updated_at)
		 VALUES (?, ?, ?)
		 ON CONFLICT(key) DO UPDATE SET value_text = excluded.value_text, updated_at = excluded.updated_at`,
		key, value, time.Now().UTC().Format(time.RFC3339),
	)
	return err
}

func LoadSetting(db *sql.DB, key string) (string, error) {
	row := db.QueryRow(`SELECT value_text FROM settings WHERE key = ?`, key)
	var value string
	if err := row.Scan(&value); err != nil {
		return "", err
	}
	return value, nil
}

func CreateSession(db *sql.DB, label string, prompt string, sourceDBPath string) (string, error) {
	sessionID := "ses_" + uuid.NewString()[:8]
	_, err := db.Exec(
		`INSERT INTO sessions(session_id, label, prompt, source_db_path) VALUES (?, ?, ?, ?)`,
		sessionID, label, prompt, sourceDBPath,
	)
	return sessionID, err
}

func SaveNote(db *sql.DB, sessionID string, kind string, text string, paperID string, resultID string) (string, error) {
	noteID := "note_" + uuid.NewString()[:8]
	_, err := db.Exec(
		`INSERT INTO notes(note_id, session_id, kind, text, paper_id, result_id) VALUES (?, ?, ?, ?, ?, ?)`,
		noteID, sessionID, kind, text, nullableString(paperID), nullableString(resultID),
	)
	return noteID, err
}

func SaveHypothesis(db *sql.DB, sessionID string, title string, hypothesisText string, targetMarket string) (string, error) {
	hypothesisID := "hyp_" + uuid.NewString()[:8]
	_, err := db.Exec(
		`INSERT INTO hypotheses(hypothesis_id, session_id, title, hypothesis_text, target_market) VALUES (?, ?, ?, ?, ?)`,
		hypothesisID, sessionID, title, hypothesisText, nullableString(targetMarket),
	)
	return hypothesisID, err
}

func SaveQueryResult(db *sql.DB, sessionID string, command string, args map[string]any, kind string, summary string, payload map[string]any, totalItems int) (string, error) {
	resultID := "res_" + uuid.NewString()[:8]
	argsBytes, err := json.Marshal(args)
	if err != nil {
		return "", err
	}
	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	_, err = db.Exec(
		`INSERT INTO query_results(result_id, session_id, command, args_json, kind, summary_text, payload_json, total_items)
		 VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		resultID, nullableString(sessionID), command, string(argsBytes), kind, summary, string(payloadBytes), totalItems,
	)
	return resultID, err
}

func LoadQueryResult(db *sql.DB, resultID string) (*StoredResult, error) {
	row := db.QueryRow(`SELECT result_id, session_id, command, kind, summary_text, payload_json, total_items FROM query_results WHERE result_id = ?`, resultID)
	var result StoredResult
	var sessionID sql.NullString
	var payloadJSON string
	if err := row.Scan(&result.ResultID, &sessionID, &result.Command, &result.Kind, &result.Summary, &payloadJSON, &result.TotalItems); err != nil {
		return nil, err
	}
	if sessionID.Valid {
		result.SessionID = sessionID.String
	}
	result.Data = map[string]any{}
	if err := json.Unmarshal([]byte(payloadJSON), &result.Data); err != nil {
		return nil, fmt.Errorf("unmarshal stored result: %w", err)
	}
	return &result, nil
}

func nullableString(value string) any {
	if value == "" {
		return nil
	}
	return value
}
