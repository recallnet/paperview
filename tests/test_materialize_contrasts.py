import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MaterializeContrastsTests(unittest.TestCase):
    def test_contrast_stage_writes_ranked_paper_level_candidates(self):
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
                INSERT INTO papers (paper_id, source_corpus, title, abstract, primary_category, published_at) VALUES
                  ('p1', 'arxiv', 'auction far paper', 'far from standard auction wording', 'cs.GT', '2020-01-01'),
                  ('p2', 'arxiv', 'auction local paper', 'near auction wording', 'q-fin.TR', '2019-01-01'),
                  ('p3', 'arxiv', 'maker stress paper', 'maker stress under dead-end pressure', 'q-fin.TR', '2021-05-01');

                INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256) VALUES
                  (1, 'p1', 'title_abs', 'auction far paper', 3, 'a'),
                  (2, 'p2', 'title_abs', 'auction local paper', 3, 'b'),
                  (3, 'p3', 'title_abs', 'maker stress paper', 3, 'c');

                INSERT INTO agitator_patterns (
                  pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active
                ) VALUES
                  ('near_auction_lexically_far', 'near auction design, lexically far', 'contrast', '...', '["auction"]', '["negative"]', 1),
                  ('near_maker_stress_far_dead_end', 'near maker stress, far dead-end', 'contrast', '...', '["maker"]', '["negative"]', 1),
                  ('near_parity_auctions', 'near parity and auctions', 'composition', '...', '["parity","auction"]', '["negative"]', 1);

                INSERT INTO probe_hits (run_id, pattern_id, view_id, score, rank) VALUES
                  ('probe-run', 'near_auction_lexically_far', 1, 0.91, 1),
                  ('probe-run', 'near_auction_lexically_far', 2, 0.74, 2),
                  ('probe-run', 'near_maker_stress_far_dead_end', 3, 0.88, 1),
                  ('probe-run', 'near_parity_auctions', 1, 0.99, 1);

                INSERT INTO stranding_scores (
                  run_id, paper_id, membership_run_id, score_version, stranding_score,
                  instrument_gap_score, access_barrier_score, implementation_barrier_score,
                  result_specificity_score, resolution_mechanics_score, survey_penalty_score,
                  empirical_only_penalty_score, stranded_alpha_bonus, feature_json
                ) VALUES
                  ('stranding-run', 'p1', 'membership-run', 's08-test', 0.31, 0, 0, 0, 0, 0, 0, 0, 0, '{}'),
                  ('stranding-run', 'p3', 'membership-run', 's08-test', 0.22, 0, 0, 0, 0, 0, 0, 0, 0, '{}');
                """
            )
            conn.commit()
            conn.close()

            output_dir = tmp / "contrast-run"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_contrasts.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "contrast-run",
                    "--probe-run-id",
                    "probe-run",
                    "--stranding-run-id",
                    "stranding-run",
                    "--output-dir",
                    str(output_dir),
                    "--top-k",
                    "2",
                ],
                check=True,
                cwd=ROOT,
            )

            conn = sqlite3.connect(str(canonical_db))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT pattern_id, paper_id, contrast_rank, contrast_score, rationale_json
                    FROM contrast_candidates
                    WHERE run_id='contrast-run'
                    ORDER BY pattern_id, contrast_rank
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["pattern_id"], "near_auction_lexically_far")
            self.assertEqual(rows[0]["paper_id"], "p1")
            self.assertEqual(rows[0]["contrast_rank"], 1)
            self.assertGreater(rows[0]["contrast_score"], rows[1]["contrast_score"])
            self.assertEqual(rows[2]["pattern_id"], "near_maker_stress_far_dead_end")
            self.assertEqual(rows[2]["paper_id"], "p3")

            rationale = json.loads(rows[0]["rationale_json"])
            self.assertEqual(rationale["pattern_kind"], "contrast")
            self.assertEqual(rationale["stranding_score"], 0.31)
            self.assertEqual(rationale["primary_category"], "cs.GT")

            metrics = json.loads((output_dir / "contrast_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["contrast_pattern_count"], 2)
            self.assertEqual(metrics["contrast_candidate_count"], 3)
            self.assertEqual(metrics["patterns_with_candidates"], 2)


if __name__ == "__main__":
    unittest.main()
