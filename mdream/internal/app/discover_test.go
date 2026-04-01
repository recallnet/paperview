package app

import "testing"

func TestMergeDiscoverLeadsDefaultsToCorpusFirst(t *testing.T) {
	surfaceHits := []map[string]any{
		{
			"publication_item_id": "early_market_failure_modes_ledger:market_design:x",
			"lane_family":         "market_design",
			"source_surface":      "early_market_failure_modes_ledger",
			"confidence":          "medium",
			"title":               "Delayed parity repair",
			"result_summary":      "Rule differences delay repair.",
			"modern_equivalent":   "venue-shaped delayed parity repair",
			"first_test":          "Compare venue rule differences.",
			"gap_to_close":        "Need venue metadata.",
			"board_rank":          int64(1),
			"match_score":         float64(12),
		},
	}
	paperHits := []map[string]any{
		{
			"paper_id":         "2205.08913",
			"title":            "Prediction market convergence",
			"lexical_score":    float64(18),
			"diamond_score":    float64(0.6),
			"top_lane":         "market_design",
			"abstract_snippet": "Prediction markets converge under some conditions.",
		},
	}
	sectionHits := []map[string]any{
		{
			"paper_id":      "2205.08913",
			"title":         "Prediction market convergence",
			"section_label": "discussion",
			"lexical_score": float64(6),
			"snippet":       "Thin venues repair more slowly.",
		},
	}
	leads := mergeDiscoverLeads(surfaceHits, paperHits, sectionHits, []string{"prediction"}, map[string]struct{}{}, 5, false, false)
	if len(leads) != 2 {
		t.Fatalf("expected 2 leads, got %d", len(leads))
	}
	if leads[0].LeadType != "paper" {
		t.Fatalf("expected paper lead first in corpus-first mode, got %+v", leads[0])
	}
	if leads[1].LeadType != "surface" {
		t.Fatalf("expected surface lead second, got %+v", leads[1])
	}
	if leads[1].AgentPriority >= leads[0].AgentPriority {
		t.Fatalf("expected repeated paper lead to be penalized, got %+v", leads)
	}
	if leads[0].ScoreBreakdown["runtime_bonus"] <= 0 {
		t.Fatalf("expected runtime discovery bonus in default corpus-first mode, got %+v", leads[0].ScoreBreakdown)
	}
	if leads[0].ScoreBreakdown["repeat_penalty"] != 0 {
		t.Fatalf("expected no repeat penalty on unseen paper, got %+v", leads[0].ScoreBreakdown)
	}
}

func TestMergeDiscoverLeadsBackfillsRepeatsOnlyAfterUnseen(t *testing.T) {
	surfaceHits := []map[string]any{
		{
			"publication_item_id": "early_market_failure_modes_ledger:market_design:x",
			"lane_family":         "market_design",
			"source_surface":      "early_market_failure_modes_ledger",
			"confidence":          "medium",
			"title":               "Delayed parity repair",
			"result_summary":      "Rule differences delay repair.",
			"modern_equivalent":   "venue-shaped delayed parity repair",
			"first_test":          "Compare venue rule differences.",
			"gap_to_close":        "Need venue metadata.",
			"board_rank":          int64(1),
			"match_score":         float64(24),
		},
	}
	paperHits := []map[string]any{
		{
			"paper_id":         "2012.12555",
			"title":            "Market Impact in Trader-Agents",
			"lexical_score":    float64(38),
			"diamond_score":    float64(0.66),
			"top_lane":         "participant_pathologies",
			"abstract_snippet": "Order-flow imbalance sensitivity.",
		},
	}
	seen := map[string]struct{}{
		"surface:market_design:delayed-parity-repair:venue-shaped-delayed-parity-repair": {},
	}

	leads := mergeDiscoverLeads(surfaceHits, paperHits, nil, []string{"toxic", "flow"}, seen, 5, false, false)
	if len(leads) != 2 {
		t.Fatalf("expected 2 leads, got %d", len(leads))
	}
	if leads[0].LeadType != "paper" || leads[0].PaperID != "2012.12555" {
		t.Fatalf("expected unseen paper lead first, got %+v", leads[0])
	}
	if leads[1].LeadType != "surface" {
		t.Fatalf("expected repeated surface to backfill second, got %+v", leads[1])
	}
}

func TestMergeDiscoverLeadsCarriesForwardStrongRepeatedSurface(t *testing.T) {
	surfaceHits := []map[string]any{
		{
			"publication_item_id": "early_market_failure_modes_ledger:market_design:x",
			"lane_family":         "market_design",
			"source_surface":      "early_market_failure_modes_ledger",
			"confidence":          "medium",
			"title":               "Delayed parity repair",
			"result_summary":      "Rule differences delay repair.",
			"modern_equivalent":   "venue-shaped delayed parity repair",
			"first_test":          "Compare venue rule differences.",
			"gap_to_close":        "Need venue metadata.",
			"board_rank":          int64(1),
			"match_score":         float64(68),
		},
	}
	paperHits := []map[string]any{
		{
			"paper_id":         "2106.06974",
			"title":            "Algorithmic market making in dealer markets",
			"lexical_score":    float64(51),
			"diamond_score":    float64(0.18),
			"top_lane":         "settlement_resolution",
			"abstract_snippet": "Dealer market hedging and impact.",
		},
	}
	seen := map[string]struct{}{
		"surface:market_design:delayed-parity-repair:venue-shaped-delayed-parity-repair": {},
	}

	leads := mergeDiscoverLeads(surfaceHits, paperHits, nil, []string{"market", "design", "parity"}, seen, 5, false, false)
	if len(leads) != 2 {
		t.Fatalf("expected 2 leads, got %d", len(leads))
	}
	if leads[1].LeadType != "surface" {
		t.Fatalf("expected strong repeated surface to remain visible, got %+v", leads)
	}
	if leads[1].ScoreBreakdown["repeat_penalty"] >= 0 {
		t.Fatalf("expected repeat penalty on carried-forward surface, got %+v", leads[1].ScoreBreakdown)
	}
}

func TestMergeDiscoverLeadsPreferSurfacesFlagRestoresSurfaceBias(t *testing.T) {
	surfaceHits := []map[string]any{
		{
			"publication_item_id": "early_market_failure_modes_ledger:market_design:x",
			"lane_family":         "market_design",
			"source_surface":      "early_market_failure_modes_ledger",
			"confidence":          "medium",
			"title":               "Delayed parity repair",
			"result_summary":      "Rule differences delay repair.",
			"modern_equivalent":   "venue-shaped delayed parity repair",
			"first_test":          "Compare venue rule differences.",
			"gap_to_close":        "Need venue metadata.",
			"board_rank":          int64(1),
			"match_score":         float64(27),
		},
	}
	paperHits := []map[string]any{
		{
			"paper_id":         "2002.02583",
			"title":            "Triangular arbitrage correlations",
			"lexical_score":    float64(36),
			"diamond_score":    float64(0.62),
			"top_lane":         "state_graph",
			"abstract_snippet": "Cross-currency correlations around flash events.",
		},
	}

	leads := mergeDiscoverLeads(surfaceHits, paperHits, nil, []string{"prediction", "market"}, map[string]struct{}{}, 5, false, true)
	if len(leads) != 2 {
		t.Fatalf("expected 2 leads, got %d", len(leads))
	}
	if leads[0].LeadType != "surface" {
		t.Fatalf("expected surface lead first when prefer-surfaces is enabled, got %+v", leads[0])
	}
	if leads[0].ScoreBreakdown["surface_bonus"] <= 0 {
		t.Fatalf("expected explicit surface bonus when prefer-surfaces is enabled, got %+v", leads[0].ScoreBreakdown)
	}
}
