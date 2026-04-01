import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_representation_discovery_map import build_text_views


class RepresentationDiscoveryMapTests(unittest.TestCase):
    def test_build_text_views_emits_expected_view_types(self):
        corpus = [
            {
                "paper_id": "p1",
                "title": "Triangular arbitrage and queue resets",
                "abstract": "Linked venues drift and then refill.",
                "primary_category": "q-fin.TR",
                "literature_family": "q_fin",
                "evaluation_split": "tuning",
                "section_view": "[introduction] linked venues drift",
                "section_snippets": [
                    {"label": "introduction", "order": 1, "text": "linked venues drift"},
                    {"label": "empirical results", "order": 2, "text": "repair follows order-flow shocks"},
                    {"label": "conclusion", "order": 3, "text": "fragmented venues delay parity repair"},
                ],
                "weak_labels": [],
                "weak_label_text": "",
            }
        ]
        views = build_text_views(corpus)
        self.assertEqual(len(views), 10)
        self.assertEqual(
            {row["view_type"] for row in views},
            {
                "title_abs",
                "abs_only",
                "title_abs_cats",
                "title_only",
                "category_string",
                "section_or_abs",
                "surprise_sections",
                "mechanism_sections",
                "regime_sections",
                "all_sections",
            },
        )
        self.assertEqual(sorted(row["view_id"] for row in views), list(range(1, 11)))


if __name__ == "__main__":
    unittest.main()
