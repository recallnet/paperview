package app

import (
	"database/sql"
	"path/filepath"
	"testing"

	_ "github.com/mattn/go-sqlite3"
	"github.com/recallnet/paperview/mdream/internal/core"
)

func TestComputeScores(t *testing.T) {
	input := core.HypothesisScoreInput{
		PriorNovelty:           2,
		PosteriorNovelty:       8,
		PriorPlausibility:      3,
		PosteriorPlausibility:  7,
		ThinMarketFit:          9,
		Executability:          6,
		EvidenceQuality:        8,
		BasinRepetitionPenalty: 1,
		GenericDragPenalty:     2,
	}
	surprise := computeSurpriseScore(input)
	if surprise <= 0 {
		t.Fatalf("expected positive surprise score, got %v", surprise)
	}
	input.SurpriseScore = surprise
	objective := computeObjectiveScore(input)
	if objective <= 0 {
		t.Fatalf("expected positive objective score, got %v", objective)
	}
}

func TestCurrentSessionObjectiveReturnsBestScoredHypothesis(t *testing.T) {
	db, err := sql.Open("sqlite3", filepath.Join(t.TempDir(), "mdream.sqlite3"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if err := core.EnsureStoreSchema(db); err != nil {
		t.Fatal(err)
	}
	sessionID, err := core.CreateSession(db, "test", "prompt", "/tmp/source.sqlite3")
	if err != nil {
		t.Fatal(err)
	}
	h1, err := core.SaveHypothesis(db, sessionID, "h1", "first", "prediction")
	if err != nil {
		t.Fatal(err)
	}
	h2, err := core.SaveHypothesis(db, sessionID, "h2", "second", "prediction")
	if err != nil {
		t.Fatal(err)
	}
	_, err = core.SaveHypothesisScore(db, core.HypothesisScoreInput{
		HypothesisID:          h1,
		PosteriorNovelty:      6,
		PosteriorPlausibility: 5,
		ThinMarketFit:         6,
		Executability:         6,
		EvidenceQuality:       6,
		SurpriseScore:         5,
		ObjectiveScore:        4.5,
	})
	if err != nil {
		t.Fatal(err)
	}
	_, err = core.SaveHypothesisScore(db, core.HypothesisScoreInput{
		HypothesisID:          h2,
		PosteriorNovelty:      8,
		PosteriorPlausibility: 7,
		ThinMarketFit:         8,
		Executability:         7,
		EvidenceQuality:       7,
		SurpriseScore:         6,
		ObjectiveScore:        6.8,
	})
	if err != nil {
		t.Fatal(err)
	}

	best, err := currentSessionObjective(db, sessionID)
	if err != nil {
		t.Fatal(err)
	}
	if best["status"] != "scored" {
		t.Fatalf("expected scored status, got %+v", best)
	}
	if best["hypothesis_id"] != h2 {
		t.Fatalf("expected top hypothesis %s, got %+v", h2, best)
	}
}
