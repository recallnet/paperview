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

        INSERT INTO papers (paper_id, source_corpus, title, abstract, primary_category, published_at) VALUES
          ('bridge-paper', 'arxiv', 'Bridge Paper', 'bridge abstract', 'q-fin.TR', '2023-01-01'),
          ('stranded-paper', 'arxiv', 'Stranded Paper', 'stranded abstract', 'q-fin.PR', '2021-02-01'),
          ('transition-paper-a', 'arxiv', 'Transition Paper A', 'transition abstract a', 'q-fin.TR', '2020-03-01'),
          ('transition-paper-b', 'arxiv', 'Transition Paper B', 'transition abstract b', 'q-fin.TR', '2019-04-01');

        INSERT INTO review_packets (
          run_id, packet_kind, item_ref, title, packet_path, summary_json, packet_markdown, source_run_ids_json
        ) VALUES
          ('packet-run', 'bridge', 'bridge-a', 'Bridge Packet A', '/tmp/bridge-a.md', '{"max_score": 2.4}', '# Bridge A', '{}');

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
    def test_prepares_expanded_batch_across_three_operator_families(self):
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
                    "--resurfacing-run-id",
                    "resurface-run",
                    "--transition-run-id",
                    "transition-run",
                    "--output-dir",
                    str(output_dir),
                    "--bridge-limit",
                    "2",
                    "--stranded-limit",
                    "2",
                    "--transition-per-pattern",
                    "1",
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "enhanced_interpretation_batch_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["prepared_count"], 4)
            self.assertEqual(metrics["counts_by_operator_family"], {"bridge": 1, "stranded_qfin": 1, "transition_state": 2})

            rows = [
                json.loads(line)
                for line in (output_dir / "enhanced_interpretation_batch.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual(rows[0]["operator_family"], "bridge")
            self.assertEqual(rows[1]["operator_family"], "stranded_qfin")
            self.assertEqual(rows[2]["operator_family"], "transition_state")
            self.assertEqual(rows[3]["operator_family"], "transition_state")
            self.assertIn("TRANSLATION_CANDIDATE", rows[0]["prompt_text"])
            self.assertIn("classification", rows[0]["schema_required_fields"])
            self.assertEqual(rows[1]["packet_summary"]["paper_id"], "stranded-paper")
            self.assertEqual(
                {rows[2]["packet_summary"]["pattern_id"], rows[3]["packet_summary"]["pattern_id"]},
                {"near_transition_queue_refill", "near_transition_auction_refill"},
            )


if __name__ == "__main__":
    unittest.main()
