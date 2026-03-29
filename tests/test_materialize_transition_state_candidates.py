import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MaterializeTransitionStateCandidatesTests(unittest.TestCase):
    def test_transition_state_candidate_stage_writes_ranked_candidates(self):
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
                  ('p1', 'arxiv', 'queue refill lead', 'queue value and refill lag', 'q-fin', '2024-01-01'),
                  ('p2', 'arxiv', 'queue refill backup', 'queue value only', 'q-fin', '2024-01-02'),
                  ('p3', 'arxiv', 'auction refill lead', 'auction handoff and refill', 'q-fin', '2024-01-03');

                INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256) VALUES
                  (1, 'p1', 'title_abs', 'queue refill lead', 3, 'a'),
                  (2, 'p2', 'title_abs', 'queue refill backup', 3, 'b'),
                  (3, 'p3', 'title_abs', 'auction refill lead', 3, 'c');

                INSERT INTO agitator_patterns (pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active) VALUES
                  ('near_transition_queue_refill', 'queue refill', 'composition', '', '[]', '[]', 1),
                  ('near_transition_auction_refill', 'auction refill', 'composition', '', '[]', '[]', 1);

                INSERT INTO transition_state_scores (
                  run_id, paper_id, membership_run_id, probe_run_id, score_version,
                  transition_state_score, queue_value_score, refill_resiliency_score,
                  auction_handoff_score, maker_retreat_score, parity_repair_score,
                  sparse_component_score, proximity_component_score, family_count, feature_json
                ) VALUES
                  ('score-run', 'p1', 'membership-run', 'probe-run', 'v1', 0.55, 0.7, 0.6, 0.0, 0.0, 0.0, 0.4, 0.5, 3, '{}'),
                  ('score-run', 'p2', 'membership-run', 'probe-run', 'v1', 0.35, 0.5, 0.1, 0.0, 0.0, 0.0, 0.2, 0.3, 2, '{}'),
                  ('score-run', 'p3', 'membership-run', 'probe-run', 'v1', 0.42, 0.0, 0.5, 0.6, 0.0, 0.0, 0.3, 0.4, 3, '{}');

                INSERT INTO probe_hits (run_id, pattern_id, view_id, score, rank) VALUES
                  ('probe-run', 'near_transition_queue_refill', 1, 2.0, 1),
                  ('probe-run', 'near_transition_queue_refill', 2, 1.0, 2),
                  ('probe-run', 'near_transition_auction_refill', 3, 1.5, 1);
                """
            )
            conn.commit()
            conn.close()

            output_dir = tmp / "transition-candidate-run"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_transition_state_candidates.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "transition-candidate-run",
                    "--score-run-id",
                    "score-run",
                    "--probe-run-id",
                    "probe-run",
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
                    SELECT pattern_id, paper_id, transition_state_rank, transition_state_candidate_score, rationale_json
                    FROM transition_state_candidates
                    WHERE run_id='transition-candidate-run'
                    ORDER BY pattern_id, transition_state_rank, paper_id
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["pattern_id"], "near_transition_auction_refill")
            self.assertEqual(rows[0]["paper_id"], "p3")
            queue_rows = [row for row in rows if row["pattern_id"] == "near_transition_queue_refill"]
            self.assertEqual(queue_rows[0]["paper_id"], "p1")
            self.assertEqual(queue_rows[0]["transition_state_rank"], 1)
            self.assertGreater(queue_rows[0]["transition_state_candidate_score"], queue_rows[1]["transition_state_candidate_score"])

            rationale = json.loads(queue_rows[0]["rationale_json"])
            self.assertEqual(rationale["probe_rank"], 1)
            self.assertGreater(rationale["transition_state_score"], 0.5)

            metrics = json.loads((output_dir / "transition_state_candidate_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["transition_pattern_count"], 2)
            self.assertEqual(metrics["transition_candidate_count"], 3)
            self.assertEqual(metrics["patterns_with_candidates"], 2)


if __name__ == "__main__":
    unittest.main()
