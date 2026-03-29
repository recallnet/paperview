import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MaterializeStateGraphCandidatesTests(unittest.TestCase):
    def test_state_graph_operator_materializes_ranked_candidates(self):
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
                INSERT INTO papers (paper_id, source_corpus, title, abstract) VALUES
                  ('p1', 'arxiv', 'state graph lead', 'cross-market inconsistency and parity repair'),
                  ('p2', 'arxiv', 'state graph backup', 'settlement-linked repair'),
                  ('p3', 'arxiv', 'off lane', 'unrelated');

                INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256) VALUES
                  (1, 'p1', 'title_abs', 'state graph lead', 3, 'a'),
                  (2, 'p2', 'title_abs', 'state graph backup', 3, 'b'),
                  (3, 'p3', 'title_abs', 'off lane', 2, 'c');

                INSERT INTO agitator_patterns (pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active) VALUES
                  ('near_state_graph_far_realized', 'state graph far realized', 'contrast', '', '[]', '[]', 1),
                  ('near_transition_parity_repair', 'transition parity repair', 'composition', '', '[]', '[]', 1);

                INSERT INTO probe_hits (run_id, pattern_id, view_id, score, rank) VALUES
                  ('probe-run', 'near_state_graph_far_realized', 1, 1.8, 1),
                  ('probe-run', 'near_transition_parity_repair', 2, 1.4, 1);

                INSERT INTO bridge_candidates (
                  run_id, source_anchor_id, target_anchor_id, paper_id, bridge_score, bridge_rank, rationale_json
                ) VALUES
                  ('bridge-run', 'state_graph_inconsistencies', 'settlement_resolution_seams', 'p1', 2.1, 1, '{}');

                INSERT INTO composition_candidates (
                  run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json
                ) VALUES
                  ('composition-run', 'parity_propagation', 'state_graph_inconsistencies', 'p2', 2.7, 1, '{}');

                INSERT INTO diamond_scores (
                  run_id, paper_id, lane_score_run_id, membership_run_id, score_version, diamond_score, top_lane,
                  top_lane_score, primary_capsule_id, challenge_affinity_score, positive_anchor_affinity_score,
                  negative_anchor_affinity_score, translation_gap_score, stranding_score, bridge_score,
                  composition_score, holdout_echo_score, transition_state_score, genericity_penalty_score,
                  realized_market_leakage_penalty_score, lane_rarity_bonus, positive_lane_count, problem_view,
                  mechanism_view, regime_view, stranding_view, feature_json
                ) VALUES
                  ('diamond-run', 'p1', 'lane-run', 'membership-run', 'v1', 0.81, 'state_graph', 0.77, 'state_graph_repair', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{"lane_scores":{"state_graph":0.77}}'),
                  ('diamond-run', 'p2', 'lane-run', 'membership-run', 'v1', 0.72, 'settlement_resolution', 0.60, 'settlement_async_repair', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{"lane_scores":{"state_graph":0.42}}'),
                  ('diamond-run', 'p3', 'lane-run', 'membership-run', 'v1', 0.20, 'participant_pathologies', 0.20, 'participant_design_failure', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', '', '', '', '{"lane_scores":{"state_graph":0.01}}');
                """
            )
            conn.commit()
            conn.close()

            output_dir = tmp / "state-graph-run"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_state_graph_candidates.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "state-graph-run",
                    "--diamond-score-run-id",
                    "diamond-run",
                    "--probe-run-id",
                    "probe-run",
                    "--bridge-run-id",
                    "bridge-run",
                    "--composition-run-id",
                    "composition-run",
                    "--output-dir",
                    str(output_dir),
                    "--top-k",
                    "5",
                ],
                check=True,
                cwd=ROOT,
            )

            conn = sqlite3.connect(str(canonical_db))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT paper_id, state_graph_rank, state_graph_candidate_score, rationale_json
                    FROM state_graph_candidates
                    WHERE run_id='state-graph-run'
                    ORDER BY state_graph_rank, paper_id
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual([row["paper_id"] for row in rows], ["p1", "p2"])
            self.assertGreater(rows[0]["state_graph_candidate_score"], rows[1]["state_graph_candidate_score"])
            rationale = json.loads(rows[0]["rationale_json"])
            self.assertEqual(rationale["probe_support"]["pattern_id"], "near_state_graph_far_realized")
            metrics = json.loads((output_dir / "state_graph_candidate_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["candidate_count"], 2)
            self.assertEqual(metrics["top_ranked_paper_id"], "p1")


if __name__ == "__main__":
    unittest.main()
