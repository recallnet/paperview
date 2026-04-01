package core

import "testing"

func TestRenderStoredResultTruncatesAndPages(t *testing.T) {
	payload := map[string]any{
		"items": []map[string]any{
			{"paper_id": "a", "title": "alpha"},
			{"paper_id": "b", "title": "beta"},
			{"paper_id": "c", "title": "gamma"},
		},
	}
	stored := BuildStoredResult("res_123", "mdream search papers", "", "summary that is intentionally longer than short but still fine", "paper_search", payload, 3, OutputOptions{Page: 1, PageSize: 2})
	if stored.NextPage != 2 {
		t.Fatalf("expected next page 2, got %d", stored.NextPage)
	}
	text, err := RenderStoredResult(stored, OutputOptions{Page: 1, PageSize: 2})
	if err != nil {
		t.Fatal(err)
	}
	if text == "" {
		t.Fatal("expected rendered text")
	}
}
