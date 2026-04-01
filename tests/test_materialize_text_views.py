import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from materialize_text_views import build_text_views, build_section_derived_views, decode_categories


class MaterializeTextViewsTests(unittest.TestCase):
    def test_decode_categories_handles_json_array(self):
        self.assertEqual(decode_categories('["q-fin.TR", "math.OC"]'), ["q-fin.TR", "math.OC"])

    def test_build_section_derived_views_prioritize_tail_and_regime_sections(self):
        views = build_section_derived_views(
            [
                {"label": "Introduction", "order": 1, "text": "Venue rules and resolution timing define the market setting."},
                {"label": "Empirical results", "order": 2, "text": "We find delayed parity repair after fragmented order shocks."},
                {"label": "Conclusion", "order": 3, "text": "The main implication is a slower repair regime in thin event venues."},
                {"label": "References", "order": 4, "text": "ignored"},
            ]
        )
        self.assertIn("slower repair regime", views["surprise_sections"])
        self.assertIn("delayed parity repair", views["mechanism_sections"])
        self.assertIn("resolution timing define the market setting", views["regime_sections"])

    def test_build_text_views_emits_section_first_discovery_views(self):
        rows = build_text_views(
            [
                {
                    "paper_id": "p1",
                    "title": "Queue value after a local shock",
                    "abstract": "Passive quoting becomes attractive after refills lag.",
                    "primary_category": "q-fin.TR",
                    "categories": ["q-fin.TR", "physics.soc-ph"],
                    "literature_family": "q_fin",
                    "evaluation_split": "tuning",
                    "section_view": "[institutional] venue refill lags after a shock",
                    "section_snippets": [
                        {"label": "Institutional setting", "order": 1, "text": "Venue refill lags after a shock."},
                        {"label": "Empirical results", "order": 2, "text": "We find quote withdrawal under fragmented replenishment."},
                        {"label": "Conclusion", "order": 3, "text": "The implication is delayed repair in thin venues."},
                    ],
                }
            ]
        )
        self.assertEqual(len(rows), 10)
        by_type = {row["view_type"]: row for row in rows}
        self.assertEqual(
            set(by_type),
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
        self.assertIn("venue refill lags after a shock", by_type["section_or_abs"]["text"])
        self.assertIn("physics.soc-ph", by_type["category_string"]["text"])
        self.assertIn("delayed repair in thin venues", by_type["surprise_sections"]["text"])
        self.assertIn("quote withdrawal under fragmented replenishment", by_type["mechanism_sections"]["text"])
        self.assertIn("Venue refill lags after a shock", by_type["regime_sections"]["text"])


if __name__ == "__main__":
    unittest.main()
