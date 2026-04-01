package app

import "testing"

func TestMergeDiscoverLeadsPrefersUnseenCrossSurfaceLead(t *testing.T) {
	surfaceHits := []map[string]any{
		{
			"publication_item_id": "early_market_failure_modes_ledger:market_design:x",
			"lane_family":         "market_design",
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
	leads := mergeDiscoverLeads(surfaceHits, paperHits, sectionHits, []string{"prediction"}, seen, 5)
	if len(leads) != 2 {
		t.Fatalf("expected 2 leads, got %d", len(leads))
	}
	if leads[0].LeadType != "surface" {
		t.Fatalf("expected surface lead first, got %+v", leads[0])
	}
	if leads[1].LeadType != "paper" {
		t.Fatalf("expected paper lead second, got %+v", leads[1])
	}
	if leads[1].Score >= leads[0].Score {
		t.Fatalf("expected repeated paper lead to be penalized, got %+v", leads)
	}
}
