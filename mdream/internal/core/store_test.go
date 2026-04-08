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
	if err := UpsertSetting(db, "source_db_path", "/tmp/source.sqlite3"); err != nil {
		t.Fatal(err)
	}
	sourcePath, err := LoadSetting(db, "source_db_path")
	if err != nil {
		t.Fatal(err)
	}
	if sourcePath != "/tmp/source.sqlite3" {
		t.Fatalf("unexpected source path %q", sourcePath)
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

	hypothesisID, err := SaveHypothesis(db, sessionID, "test hypothesis", "some thesis", "prediction")
	if err != nil {
		t.Fatal(err)
	}
	if hypothesisID == "" {
		t.Fatal("expected hypothesis id")
	}
	scoreID, err := SaveHypothesisScore(db, HypothesisScoreInput{
		HypothesisID:           hypothesisID,
		LeadID:                 "paper:1234.5678",
		PaperID:                "1234.5678",
		ResultID:               resultID,
		PriorNovelty:           3,
		PosteriorNovelty:       8,
		PriorPlausibility:      4,
		PosteriorPlausibility:  7,
		ThinMarketFit:          8,
		Executability:          6,
		EvidenceQuality:        7,
		BasinRepetitionPenalty: 1,
		GenericDragPenalty:     2,
		SurpriseScore:          4,
		ObjectiveScore:         6.2,
		Notes:                  "strong after reading",
	})
	if err != nil {
		t.Fatal(err)
	}
	if scoreID == "" {
		t.Fatal("expected score id")
	}
}
