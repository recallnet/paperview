package core

import "testing"

func TestExpandResearchTokensKeepsDomainTerms(t *testing.T) {
	tokens := ExpandResearchTokens("find a surprising strategy for low-volume prediction markets")
	required := []string{"low", "volume", "prediction", "markets", "thin", "illiquid", "kalshi", "polymarket", "limitless"}
	for _, token := range required {
		found := false
		for _, existing := range tokens {
			if existing == token {
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("expected token %q in %v", token, tokens)
		}
	}
}
