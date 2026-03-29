import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_early_market_failure_modes_ledger.py"


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO diamond_interpretations (
          run_id, batch_run_id, batch_item_id, lane_family, operator_family, source_kind, source_run_id, source_ref,
          family_rank, shortlist_rank, selection_bucket, source_score, diamond_score, packet_title, classification,
          result_summary, first_test, instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close,
          confidence, raw_json
        ) VALUES
          ('diamond-run', 'diamond-batch-run', 'market_design:bridge:paper-a', 'market_design', 'bridge', 'review_packet', 'packet-run', 'paper-a', 1, 1, 'lane_quota', 2.0, 0.82, 'Market Design Packet', 'TRANSLATION_CANDIDATE', 'rule seam survives because venue incentives stay misaligned', 'test market design', 'instrument-a', 'modern-a', 'venue fragmentation remains cheap to exploit', 'tighten routing and rule parity', 'high', '{}'),
          ('diamond-run', 'diamond-batch-run', 'settlement_resolution:bridge:paper-b', 'settlement_resolution', 'bridge', 'review_packet', 'packet-run', 'paper-b', 1, 2, 'lane_quota', 1.8, 0.78, 'Settlement Packet', 'COMPOSITIONAL_CANDIDATE', 'async settlement creates repair window', 'test settlement', 'instrument-b', 'modern-b', 'post-trade state remains opaque', 'better netting and collateral synchronization', 'medium', '{}'),
          ('diamond-run', 'diamond-batch-run', 'transition_state:bridge:paper-c', 'transition_state', 'bridge', 'review_packet', 'packet-run', 'paper-c', 1, 3, 'lane_quota', 1.7, 0.74, 'Transition Packet', 'TRANSLATION_CANDIDATE', 'should not appear', 'test transition', 'instrument-c', 'modern-c', 'why-c', 'gap-c', 'medium', '{}');
        """
    )
    connection.commit()


class MaterializeEarlyMarketFailureModesLedgerTest(unittest.TestCase):
    def test_materializes_only_early_market_lane_rows(self):
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
                    "early-market-run",
                    "--interpretation-run-id",
                    "diamond-run",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "early_market_failure_modes_ledger_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["entry_count"], 2)
            self.assertEqual(metrics["counts_by_lane"]["market_design"], 1)
            self.assertEqual(metrics["counts_by_lane"]["settlement_resolution"], 1)
            self.assertEqual(metrics["counts_by_lane"]["participant_pathologies"], 0)
            self.assertEqual(metrics["counts_by_lane"]["state_graph"], 0)

            rows = [
                json.loads(line)
                for line in (output_dir / "early_market_failure_modes_ledger.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual([row["lane_family"] for row in rows], ["market_design", "settlement_resolution"])
            self.assertEqual(rows[0]["wrong_actor"], "venue operator or rule designer")
            self.assertEqual(rows[1]["likely_market_stage"], "weak_post_trade")
            self.assertNotIn("transition_state", [row["lane_family"] for row in rows])

            markdown = (output_dir / "early_market_failure_modes_ledger.md").read_text(encoding="utf-8")
            self.assertIn("# Early-Market Failure Modes Ledger", markdown)
            self.assertIn("Market Design Packet", markdown)
            self.assertNotIn("Transition Packet", markdown)


if __name__ == "__main__":
    unittest.main()
