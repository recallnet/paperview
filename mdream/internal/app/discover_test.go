package app

import "testing"

func TestMergeDiscoverLeadsPrefersUnseenCrossSurfaceLead(t *testing.T) {
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
			"lexical_score":    float64(9),
			"diamond_score":    float64(0.4),
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
	seen := map[string]struct{}{
		"paper:2205.08913": {},
	}
	leads := mergeDiscoverLeads(surfaceHits, paperHits, sectionHits, []string{"prediction"}, seen, 5, false)
	if len(leads) != 2 {
		t.Fatalf("expected 2 leads, got %d", len(leads))
	}
	if leads[0].LeadType != "surface" {
		t.Fatalf("expected surface lead first, got %+v", leads[0])
	}
	if leads[1].LeadType != "paper" {
		t.Fatalf("expected paper lead second, got %+v", leads[1])
	}
	if leads[1].AgentPriority >= leads[0].AgentPriority {
		t.Fatalf("expected repeated paper lead to be penalized, got %+v", leads)
	}
	if leads[0].AgentPriority <= leads[0].MatchScore {
		t.Fatalf("expected surface lead to have an explicit priority boost, got %+v", leads[0])
	}
	if leads[1].ScoreBreakdown["repeat_penalty"] >= 0 {
		t.Fatalf("expected repeat penalty to be recorded, got %+v", leads[1].ScoreBreakdown)
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

	leads := mergeDiscoverLeads(surfaceHits, paperHits, nil, []string{"toxic", "flow"}, seen, 5, false)
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

	leads := mergeDiscoverLeads(surfaceHits, paperHits, nil, []string{"market", "design", "parity"}, seen, 5, false)
	if len(leads) != 2 {
		t.Fatalf("expected 2 leads, got %d", len(leads))
	}
	if leads[0].LeadType != "surface" {
		t.Fatalf("expected strong repeated surface to remain visible first, got %+v", leads[0])
	}
	if leads[0].ScoreBreakdown["repeat_penalty"] >= 0 {
		t.Fatalf("expected repeat penalty on carried-forward surface, got %+v", leads[0].ScoreBreakdown)
	}
}
