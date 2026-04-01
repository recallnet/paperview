package core

import (
	"database/sql"
	"path/filepath"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func TestStoreLifecycle(t *testing.T) {
	db, err := sql.Open("sqlite3", filepath.Join(t.TempDir(), "mdream.sqlite3"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	if err := EnsureStoreSchema(db); err != nil {
		t.Fatal(err)
	}
	sessionID, err := CreateSession(db, "test", "prompt", "/tmp/source.sqlite3")
	if err != nil {
		t.Fatal(err)
	}
	if sessionID == "" {
		t.Fatal("expected session id")
	}
	resultID, err := SaveQueryResult(
		db,
		sessionID,
		"mdream tools",
		map[string]any{"q": "x"},
		"tools",
		"tools summary",
		map[string]any{"items": []map[string]any{{"tool": "search"}}},
		1,
	)
	if err != nil {
		t.Fatal(err)
	}
	stored, err := LoadQueryResult(db, resultID)
	if err != nil {
		t.Fatal(err)
	}
	if stored.ResultID != resultID {
		t.Fatalf("unexpected result id %q", stored.ResultID)
	}
}
