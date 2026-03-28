import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MaterializeStrandingScoresTests(unittest.TestCase):
    def test_materializes_sparse_stranding_scores_for_discovery_members(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical_db = tmp / "paperview.sqlite3"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "init_local_store.py"), "--db-path", str(canonical_db)],
                check=True,
                cwd=ROOT,
            )
            conn = sqlite3.connect(str(canonical_db))
            conn.executescript(
                """
                INSERT INTO papers (
                  paper_id, source_corpus, title, abstract, categories_json, primary_category, published_at
                ) VALUES
                  ('p1', 'arxiv', 'Closed-form contingent claim pricing', 'closed-form pricing in an illiquid market with contingent claim settlement delay', '["q-fin.PR"]', 'q-fin.PR', '2018-01-05'),
                  ('p2', 'arxiv', 'Survey of stylized facts', 'a review and survey of stylized facts in empirical finance', '["q-fin.ST"]', 'q-fin.ST', '2019-03-01'),
                  ('p4', 'arxiv', 'Denied frictions', 'the market is not illiquid and executes without settlement delay or contingent claim frictions', '["q-fin.TR"]', 'q-fin.TR', '2020-08-12'),
                  ('p5', 'arxiv', 'Weak characterization', 'we characterize maturity effects in a thin market', '["q-fin.PR"]', 'q-fin.PR', '2017-06-14'),
                  ('p6', 'arxiv', 'Generic characterization', 'we characterize asset dynamics with no contingent structure or explicit friction', '["q-fin.PR"]', 'q-fin.PR', '2017-07-01'),
                  ('p7', 'arxiv', 'Market contingent claim pricing', 'closed-form contingent claim pricing for a traded option market with settlement delay', '["q-fin.PR"]', 'q-fin.PR', '2018-02-03'),
                  ('p8', 'arxiv', 'Generic incomplete-market note', 'we characterize pricing in an incomplete market', '["q-fin.PR"]', 'q-fin.PR', '2017-08-10'),
                  ('p9', 'arxiv', 'Exact incomplete-market note', 'we provide an exact characterization of pricing in an incomplete market', '["q-fin.PR"]', 'q-fin.PR', '2017-08-11'),
                  ('p10', 'arxiv', 'Unobservable calibration friction', 'closed-form pricing with calibration challenges because volatility is unobservable and data unavailable', '["q-fin.PR"]', 'q-fin.PR', '2018-01-10'),
                  ('p3', 'arxiv', 'Holdout market structure', 'prediction market settlement design', '["cs.GT"]', 'cs.GT', '2024-05-01');

                INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source, rationale_json) VALUES
                  ('membership-run', 'p1', 'discovery', 'test', '{}'),
                  ('membership-run', 'p1', 'stranded_alpha', 'test', '{}'),
                  ('membership-run', 'p2', 'discovery', 'test', '{}'),
                  ('membership-run', 'p2', 'stranded_alpha', 'test', '{}'),
                  ('membership-run', 'p4', 'discovery', 'test', '{}'),
                  ('membership-run', 'p5', 'discovery', 'test', '{}'),
                  ('membership-run', 'p5', 'stranded_alpha', 'test', '{}'),
                  ('membership-run', 'p6', 'discovery', 'test', '{}'),
                  ('membership-run', 'p7', 'discovery', 'test', '{}'),
                  ('membership-run', 'p7', 'stranded_alpha', 'test', '{}'),
                  ('membership-run', 'p7', 'realized_market', 'test', '{}'),
                  ('membership-run', 'p8', 'discovery', 'test', '{}'),
                  ('membership-run', 'p9', 'discovery', 'test', '{}'),
                  ('membership-run', 'p10', 'discovery', 'test', '{}'),
                  ('membership-run', 'p3', 'holdout', 'test', '{}');
                """
            )
            conn.commit()
            conn.close()

            output_dir = tmp / "stranding-run"
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--with",
                    "pyyaml",
                    "python3",
                    str(ROOT / "scripts" / "materialize_stranding_scores.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "stranding-run",
                    "--membership-run-id",
                    "membership-run",
                    "--signal-config-path",
                    str(ROOT / "configs" / "stranding_signals.yaml"),
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            conn = sqlite3.connect(str(canonical_db))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT paper_id, stranding_score, survey_penalty_score, stranded_alpha_bonus, result_specificity_score, implementation_barrier_score
                    FROM stranding_scores
                    WHERE run_id = 'stranding-run'
                    ORDER BY paper_id
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual([row["paper_id"] for row in rows], ["p1", "p10", "p2", "p4", "p5", "p6", "p7", "p8", "p9"])
            by_id = {row["paper_id"]: row for row in rows}
            self.assertGreater(by_id["p1"]["stranding_score"], by_id["p2"]["stranding_score"])
            self.assertGreater(by_id["p1"]["stranding_score"], 0.0)
            self.assertGreater(by_id["p2"]["survey_penalty_score"], 0.0)
            self.assertEqual(by_id["p1"]["stranded_alpha_bonus"], 1.0)
            self.assertEqual(by_id["p4"]["stranding_score"], 0.0)
            self.assertGreater(by_id["p1"]["result_specificity_score"], by_id["p5"]["result_specificity_score"])
            self.assertGreater(by_id["p5"]["stranding_score"], 0.0)
            self.assertLess(by_id["p5"]["stranding_score"], by_id["p1"]["stranding_score"])
            self.assertEqual(by_id["p6"]["stranding_score"], 0.0)
            self.assertGreater(by_id["p7"]["stranding_score"], 0.0)
            self.assertLess(by_id["p7"]["stranding_score"], by_id["p1"]["stranding_score"])
            self.assertGreater(by_id["p8"]["stranding_score"], 0.0)
            self.assertGreater(by_id["p9"]["stranding_score"], by_id["p8"]["stranding_score"])
            self.assertGreater(by_id["p10"]["implementation_barrier_score"], 0.0)
            self.assertGreater(by_id["p10"]["stranding_score"], 0.0)

            conn = sqlite3.connect(str(canonical_db))
            conn.row_factory = sqlite3.Row
            try:
                feature_rows = conn.execute(
                    """
                    SELECT paper_id, feature_json
                    FROM stranding_scores
                    WHERE run_id = 'stranding-run'
                    ORDER BY paper_id
                    """
                ).fetchall()
            finally:
                conn.close()

            feature_by_id = {row["paper_id"]: json.loads(row["feature_json"]) for row in feature_rows}
            self.assertLess(
                feature_by_id["p5"]["adjusted_weight_totals"]["result_specificity"],
                feature_by_id["p5"]["raw_weight_totals"]["result_specificity"],
            )
            self.assertLess(
                feature_by_id["p8"]["adjusted_weight_totals"]["result_specificity"],
                feature_by_id["p8"]["raw_weight_totals"]["result_specificity"],
            )
            self.assertGreater(
                feature_by_id["p10"]["adjusted_weight_totals"]["implementation_barrier"],
                0.0,
            )

            metrics = json.loads((output_dir / "stranding_score_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["scored_papers"], 9)
            self.assertEqual(metrics["positive_score_papers"], 6)
            self.assertEqual(metrics["realized_market_positive_papers"], 1)


if __name__ == "__main__":
    unittest.main()
