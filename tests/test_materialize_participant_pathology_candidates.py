import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MaterializeParticipantPathologyCandidatesTests(unittest.TestCase):
    def test_participant_pathology_operator_materializes_ranked_candidates(self):
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
                  ('p1', 'arxiv', 'participant lead', 'toxic flow and venue rules'),
                  ('p2', 'arxiv', 'participant backup', 'manipulation around queue priority'),
                  ('p3', 'arxiv', 'off lane', 'unrelated');

                INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256) VALUES
                  (1, 'p1', 'title_abs', 'participant lead', 3, 'a'),
                  (2, 'p2', 'title_abs', 'participant backup', 3, 'b'),
                  (3, 'p3', 'title_abs', 'off lane', 2, 'c');

                INSERT INTO agitator_patterns (pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active) VALUES
                  ('near_participant_pathology_far_realized', 'participant pathology far realized', 'contrast', '', '[]', '[]', 1),
                  ('near_market_design_far_realized', 'market design far realized', 'contrast', '', '[]', '[]', 1);

                INSERT INTO probe_hits (run_id, pattern_id, view_id, score, rank) VALUES
                  ('probe-run', 'near_participant_pathology_far_realized', 1, 1.9, 1),
                  ('probe-run', 'near_market_design_far_realized', 2, 1.5, 1);

                INSERT INTO bridge_candidates (
                  run_id, source_anchor_id, target_anchor_id, paper_id, bridge_score, bridge_rank, rationale_json
                ) VALUES
                  ('bridge-run', 'participant_pathologies', 'market_design_seams', 'p1', 2.4, 1, '{}');

                INSERT INTO composition_candidates (
                  run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json
                ) VALUES
                  ('composition-run', 'participant_pathologies', 'queue_value_passive_quoting', 'p2', 2.8, 1, '{}');

                INSERT INTO diamond_scores (
                  run_id, paper_id, lane_score_run_id, membership_run_id, score_version, diamond_score, top_lane,
                  top_lane_score, primary_capsule_id, challenge_affinity_score, positive_anchor_affinity_score,
                  negative_anchor_affinity_score, translation_gap_score, stranding_score, bridge_score,
                  composition_score, holdout_echo_score, transition_state_score, genericity_penalty_score,
                  realized_market_leakage_penalty_score, lane_rarity_bonus, positive_lane_count, problem_view,
                  mechanism_view, regime_view, stranding_view, feature_json
                ) VALUES
                  ('diamond-run', 'p1', 'lane-run', 'membership-run', 'v1', 0.79, 'participant_pathologies', 0.79, 'participant_design_failure', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{"lane_scores":{"participant_pathologies":0.79}}'),
                  ('diamond-run', 'p2', 'lane-run', 'membership-run', 'v1', 0.70, 'market_design', 0.44, 'market_design_failure', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{"lane_scores":{"participant_pathologies":0.31}}'),
                  ('diamond-run', 'p3', 'lane-run', 'membership-run', 'v1', 0.10, 'state_graph', 0.10, 'state_graph_repair', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, '', '', '', '', '{"lane_scores":{"participant_pathologies":0.01}}');
                """
            )
            conn.commit()
            conn.close()

            output_dir = tmp / "participant-run"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_participant_pathology_candidates.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "participant-run",
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
                    SELECT paper_id, participant_pathology_rank, participant_pathology_candidate_score, rationale_json
                    FROM participant_pathology_candidates
                    WHERE run_id='participant-run'
                    ORDER BY participant_pathology_rank, paper_id
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual([row["paper_id"] for row in rows], ["p1", "p2"])
            self.assertGreater(rows[0]["participant_pathology_candidate_score"], rows[1]["participant_pathology_candidate_score"])
            rationale = json.loads(rows[0]["rationale_json"])
            self.assertEqual(rationale["probe_support"]["pattern_id"], "near_participant_pathology_far_realized")
            metrics = json.loads((output_dir / "participant_pathology_candidate_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["candidate_count"], 2)
            self.assertEqual(metrics["top_ranked_paper_id"], "p1")


if __name__ == "__main__":
    unittest.main()
