import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_diamond_interpretation_batch.py"


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO anchors (anchor_id, label, anchor_type, tags_json) VALUES
          ('market_design_seams', 'Market Design', 'positive', '[]'),
          ('settlement_resolution_seams', 'Settlement Resolution', 'positive', '[]'),
          ('refill_lag_local_shock', 'Refill Lag Local Shock', 'positive', '[]'),
          ('refill_lag_resiliency', 'Refill Lag Resiliency', 'positive', '[]'),
          ('parity_propagation_delayed_repair', 'Parity Delayed Repair', 'positive', '[]'),
          ('state_graph_inconsistencies', 'State Graph Inconsistencies', 'positive', '[]');

        INSERT INTO papers (paper_id, source_corpus, title, abstract, primary_category, published_at) VALUES
          ('market-design-paper', 'arxiv', 'Market Design Paper', 'market design abstract', 'cs.GT', '2023-01-01'),
          ('settlement-paper', 'arxiv', 'Settlement Paper', 'settlement abstract', 'q-fin.GN', '2022-01-01'),
          ('participant-paper', 'arxiv', 'Participant Paper', 'participant abstract', 'q-fin.TR', '2021-01-01'),
          ('state-graph-paper', 'arxiv', 'State Graph Paper', 'state graph abstract', 'q-fin.CP', '2020-01-01'),
          ('stranded-paper', 'arxiv', 'Stranded Paper', 'stranded abstract', 'q-fin.PR', '2019-01-01'),
          ('transition-paper-a', 'arxiv', 'Transition Paper A', 'transition abstract a', 'q-fin.TR', '2020-02-01'),
          ('transition-paper-b', 'arxiv', 'Transition Paper B', 'transition abstract b', 'q-fin.TR', '2020-03-01');

        INSERT INTO agitator_patterns (pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active) VALUES
          ('near_transition_queue_refill', 'Queue x Refill', 'composition', '', '[]', '[]', 1),
          ('near_transition_auction_queue', 'Auction x Queue', 'composition', '', '[]', '[]', 1);

        INSERT INTO diamond_scores (
          run_id, paper_id, lane_score_run_id, membership_run_id, score_version, diamond_score, top_lane,
          top_lane_score, primary_capsule_id, challenge_affinity_score, positive_anchor_affinity_score,
          negative_anchor_affinity_score, translation_gap_score, stranding_score, bridge_score,
          composition_score, holdout_echo_score, transition_state_score, genericity_penalty_score,
          realized_market_leakage_penalty_score, lane_rarity_bonus, positive_lane_count, problem_view,
          mechanism_view, regime_view, stranding_view, feature_json
        ) VALUES
          ('diamond-run', 'market-design-paper', 'lane-run', 'membership-run', 'v1', 0.71, 'market_design', 0.71, 'market_design_repair', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{}'),
          ('diamond-run', 'settlement-paper', 'lane-run', 'membership-run', 'v1', 0.69, 'settlement_resolution', 0.69, 'settlement_async_repair', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{}'),
          ('diamond-run', 'participant-paper', 'lane-run', 'membership-run', 'v1', 0.67, 'participant_pathologies', 0.67, 'participant_design_failure', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{}'),
          ('diamond-run', 'state-graph-paper', 'lane-run', 'membership-run', 'v1', 0.74, 'state_graph', 0.74, 'state_graph_repair', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{}'),
          ('diamond-run', 'stranded-paper', 'lane-run', 'membership-run', 'v1', 0.66, 'stranded_qfin', 0.66, 'execution_control', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{}'),
          ('diamond-run', 'transition-paper-a', 'lane-run', 'membership-run', 'v1', 0.83, 'transition_state', 0.83, 'queue_refill_repair', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{}'),
          ('diamond-run', 'transition-paper-b', 'lane-run', 'membership-run', 'v1', 0.81, 'transition_state', 0.81, 'auction_handoff', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, '', '', '', '', '{}');

        INSERT INTO bridge_candidates (
          run_id, source_anchor_id, target_anchor_id, paper_id, bridge_score, bridge_rank, rationale_json
        ) VALUES
          ('bridge-run', 'market_design_seams', 'refill_lag_local_shock', 'market-design-paper', 2.4, 1, '{}'),
          ('bridge-run', 'settlement_resolution_seams', 'parity_propagation_delayed_repair', 'settlement-paper', 2.3, 1, '{}');

        INSERT INTO composition_candidates (
          run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json
        ) VALUES
          ('composition-run', 'market_design_seams', 'refill_lag_resiliency', 'market-design-paper', 2.5, 1, '{}'),
          ('composition-run', 'settlement_resolution_seams', 'state_graph_inconsistencies', 'settlement-paper', 2.6, 1, '{}');

        INSERT INTO participant_pathology_candidates (
          run_id, paper_id, diamond_score_run_id, probe_run_id, bridge_run_id, composition_run_id,
          participant_pathology_candidate_score, participant_pathology_rank, rationale_json
        ) VALUES
          ('participant-run', 'participant-paper', 'diamond-run', 'probe-run', 'bridge-run', 'composition-run', 0.82, 1, '{"support":"participant"}');

        INSERT INTO state_graph_candidates (
          run_id, paper_id, diamond_score_run_id, probe_run_id, bridge_run_id, composition_run_id,
          state_graph_candidate_score, state_graph_rank, rationale_json
        ) VALUES
          ('state-graph-run', 'state-graph-paper', 'diamond-run', 'probe-run', 'bridge-run', 'composition-run', 0.91, 1, '{"support":"state_graph"}');

        INSERT INTO stranded_resurfacing_candidates (
          run_id, paper_id, resurfacing_score, resurfacing_rank, membership_run_id, stranding_run_id, transition_score_run_id, rationale_json
        ) VALUES
          ('stranded-run', 'stranded-paper', 0.62, 1, 'membership-run', 'stranding-run', 'transition-score-run', '{"venue_closeness_score":0.5}');

        INSERT INTO transition_state_candidates (
          run_id, pattern_id, paper_id, transition_state_candidate_score, transition_state_rank, rationale_json
        ) VALUES
          ('transition-run', 'near_transition_queue_refill', 'transition-paper-a', 0.77, 1, '{"probe_rank":1}'),
          ('transition-run', 'near_transition_auction_queue', 'transition-paper-b', 0.73, 2, '{"probe_rank":1}');
        """
    )
    connection.commit()


class MaterializeDiamondInterpretationBatchTests(unittest.TestCase):
    def test_prepares_top_band_with_lane_quota_and_overflow(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"

            connection = sqlite3.connect(db_path)
            seed_fixture(connection)
            connection.close()

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "diamond-batch-run",
                    "--diamond-score-run-id",
                    "diamond-run",
                    "--bridge-run-id",
                    "bridge-run",
                    "--composition-run-id",
                    "composition-run",
                    "--stranded-run-id",
                    "stranded-run",
                    "--transition-run-id",
                    "transition-run",
                    "--state-graph-run-id",
                    "state-graph-run",
                    "--participant-run-id",
                    "participant-run",
                    "--lane-quota",
                    "1",
                    "--overall-limit",
                    "7",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "diamond_interpretation_batch_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["prepared_count"], 7)
            self.assertEqual(metrics["counts_by_selection_bucket"], {"lane_quota": 6, "overall_topup": 1})
            self.assertEqual(
                metrics["counts_by_lane"],
                {
                    "market_design": 1,
                    "settlement_resolution": 1,
                    "participant_pathologies": 1,
                    "state_graph": 1,
                    "stranded_qfin": 1,
                    "transition_state": 2,
                },
            )

            rows = [
                json.loads(line)
                for line in (output_dir / "diamond_interpretation_batch.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual(len(rows), 7)
            self.assertIn("TRANSITION_SEAM", rows[0]["prompt_text"])
            self.assertIn("first_test", rows[0]["schema_required_fields"])
            self.assertEqual({row["lane_family"] for row in rows}, {"market_design", "settlement_resolution", "participant_pathologies", "state_graph", "stranded_qfin", "transition_state"})
            self.assertTrue(any(row["selection_bucket"] == "overall_topup" and row["lane_family"] == "transition_state" for row in rows))


if __name__ == "__main__":
    unittest.main()
