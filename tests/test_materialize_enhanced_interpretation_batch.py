import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_enhanced_interpretation_batch.py"


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO agitator_patterns (
          pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active
        ) VALUES
          ('near_transition_queue_refill', 'Queue x Refill', 'transition', 'queue refill', '[]', '[]', 1),
          ('near_transition_auction_refill', 'Auction x Refill', 'transition', 'auction refill', '[]', '[]', 1);

        INSERT INTO anchors (anchor_id, label, anchor_type, tags_json) VALUES
          ('market_design_seams', 'Market Design', 'positive', '[]'),
          ('settlement_resolution_seams', 'Settlement', 'positive', '[]'),
          ('participant_pathologies', 'Participant', 'positive', '[]'),
          ('state_graph_inconsistencies', 'State Graph', 'positive', '[]'),
          ('lifecycle_professionalization', 'Lifecycle', 'positive', '[]'),
          ('refill_lag_local_shock', 'Refill Local Shock', 'positive', '[]'),
          ('parity_propagation_delayed_repair', 'Parity Repair', 'positive', '[]'),
          ('queue_value_passive_quoting', 'Queue Value', 'positive', '[]');

        INSERT INTO papers (paper_id, source_corpus, title, abstract, primary_category, published_at) VALUES
          ('market-design-paper', 'arxiv', 'Market Design Paper', 'market design abstract', 'cs.GT', '2023-01-01'),
          ('settlement-paper', 'arxiv', 'Settlement Paper', 'settlement abstract', 'q-fin.GN', '2022-01-01'),
          ('participant-paper', 'arxiv', 'Participant Pathology Paper', 'participant abstract', 'q-fin.TR', '2021-01-01'),
          ('state-graph-paper', 'arxiv', 'State Graph Paper', 'state graph abstract', 'q-fin.CP', '2020-01-01'),
          ('lifecycle-paper', 'arxiv', 'Lifecycle Paper', 'lifecycle abstract', 'q-fin.TR', '2019-01-01'),
          ('stranded-paper', 'arxiv', 'Stranded Paper', 'stranded abstract', 'q-fin.PR', '2021-02-01'),
          ('transition-paper-a', 'arxiv', 'Transition Paper A', 'transition abstract a', 'q-fin.TR', '2020-03-01'),
          ('transition-paper-b', 'arxiv', 'Transition Paper B', 'transition abstract b', 'q-fin.TR', '2019-04-01');

        INSERT INTO review_packets (
          run_id, packet_kind, item_ref, title, packet_path, summary_json, packet_markdown, source_run_ids_json
        ) VALUES
          ('packet-run', 'bridge', 'market_design_seams__refill_lag_local_shock', 'Market Design Packet', '/tmp/market-design.md', '{"max_score": 2.4}', '# Market Design', '{}'),
          ('packet-run', 'composition', 'settlement_resolution_seams__parity_propagation_delayed_repair', 'Settlement Packet', '/tmp/settlement.md', '{"max_score": 2.3}', '# Settlement', '{}'),
          ('packet-run', 'bridge', 'participant_pathologies__queue_value_passive_quoting', 'Participant Packet', '/tmp/participant.md', '{"max_score": 2.2}', '# Participant', '{}'),
          ('packet-run', 'composition', 'state_graph_inconsistencies__parity_propagation_delayed_repair', 'State Graph Packet', '/tmp/state-graph.md', '{"max_score": 2.1}', '# State Graph', '{}'),
          ('packet-run', 'bridge', 'lifecycle_professionalization__queue_value_passive_quoting', 'Lifecycle Packet', '/tmp/lifecycle.md', '{"max_score": 2.0}', '# Lifecycle', '{}');

        INSERT INTO bridge_candidates (
          run_id, source_anchor_id, target_anchor_id, paper_id, bridge_score, bridge_rank, rationale_json
        ) VALUES
          ('bridge-run', 'market_design_seams', 'refill_lag_local_shock', 'market-design-paper', 2.4, 1, '{}'),
          ('bridge-run', 'participant_pathologies', 'queue_value_passive_quoting', 'participant-paper', 2.2, 1, '{}'),
          ('bridge-run', 'lifecycle_professionalization', 'queue_value_passive_quoting', 'lifecycle-paper', 2.0, 1, '{}');

        INSERT INTO composition_candidates (
          run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json
        ) VALUES
          ('composition-run', 'settlement_resolution_seams', 'parity_propagation_delayed_repair', 'settlement-paper', 2.3, 1, '{}'),
          ('composition-run', 'state_graph_inconsistencies', 'parity_propagation_delayed_repair', 'state-graph-paper', 2.1, 1, '{}');

        INSERT INTO stranded_resurfacing_candidates (
          run_id, paper_id, resurfacing_score, resurfacing_rank, membership_run_id, stranding_run_id, transition_score_run_id, rationale_json
        ) VALUES
          ('resurface-run', 'stranded-paper', 0.61, 1, 'membership-run', 'stranding-run', 'transition-run', '{"venue_closeness_score": 0.4, "result_specificity_score": 0.3}');

        INSERT INTO transition_state_candidates (
          run_id, pattern_id, paper_id, transition_state_candidate_score, transition_state_rank, rationale_json
        ) VALUES
          ('transition-run', 'near_transition_queue_refill', 'transition-paper-a', 0.72, 1, '{"probe_rank":1,"family_count":2}'),
          ('transition-run', 'near_transition_auction_refill', 'transition-paper-b', 0.68, 1, '{"probe_rank":1,"family_count":2}');
        """
    )
    connection.commit()


class MaterializeEnhancedInterpretationBatchTest(unittest.TestCase):
    def test_prepares_expanded_batch_across_lane_stranded_and_transition_families(self):
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
                    "enhanced-run",
                    "--packet-run-id",
                    "packet-run",
                    "--bridge-run-id",
                    "bridge-run",
                    "--composition-run-id",
                    "composition-run",
                    "--resurfacing-run-id",
                    "resurface-run",
                    "--transition-run-id",
                    "transition-run",
                    "--output-dir",
                    str(output_dir),
                    "--lane-limit",
                    "1",
                    "--stranded-limit",
                    "2",
                    "--transition-per-pattern",
                    "1",
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "enhanced_interpretation_batch_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["prepared_count"], 8)
            self.assertEqual(
                metrics["counts_by_operator_family"],
                {
                    "market_design": 1,
                    "settlement_resolution": 1,
                    "participant_pathologies": 1,
                    "state_graph": 1,
                    "lifecycle": 1,
                    "stranded_qfin": 1,
                    "transition_state": 2,
                },
            )

            rows = [
                json.loads(line)
                for line in (output_dir / "enhanced_interpretation_batch.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual(
                [row["operator_family"] for row in rows],
                [
                    "market_design",
                    "settlement_resolution",
                    "participant_pathologies",
                    "state_graph",
                    "lifecycle",
                    "stranded_qfin",
                    "transition_state",
                    "transition_state",
                ],
            )
            self.assertIn("TRANSLATION_CANDIDATE", rows[0]["prompt_text"])
            self.assertIn("classification", rows[0]["schema_required_fields"])
            self.assertEqual(rows[0]["packet_summary"]["lane_anchor_id"], "market_design_seams")
            self.assertEqual(rows[0]["packet_summary"]["packet_kind"], "bridge")
            self.assertEqual(rows[5]["packet_summary"]["paper_id"], "stranded-paper")
            self.assertEqual(
                {rows[6]["packet_summary"]["pattern_id"], rows[7]["packet_summary"]["pattern_id"]},
                {"near_transition_queue_refill", "near_transition_auction_refill"},
            )


if __name__ == "__main__":
    unittest.main()
