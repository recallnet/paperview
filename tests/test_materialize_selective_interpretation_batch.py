import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_selective_interpretation_batch.py"


def seed_interpretation_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.execute(
        """
        INSERT INTO review_packets (
          run_id, packet_kind, item_ref, title, packet_path, summary_json, packet_markdown, source_run_ids_json
        )
        VALUES
          ('packet-run', 'bridge', 'bridge-a', 'Bridge Packet A', '/tmp/bridge-a.md', '{"max_score": 2.2}', '# Bridge A', '{}'),
          ('packet-run', 'composition', 'composition-a', 'Composition Packet A', '/tmp/composition-a.md', '{"max_score": 2.8}', '# Composition A', '{}')
        """
    )
    connection.execute(
        """
        INSERT INTO shortlist_items (
          run_id, shortlist_id, item_type, item_ref, packet_run_id, packet_kind, packet_item_ref,
          score, shortlist_rank, status, rationale_json
        )
        VALUES
          ('shortlist-run', 'bridge:bridge-a', 'bridge', 'bridge-a', 'packet-run', 'bridge', 'bridge-a', 2.2, 1, 'proposed', '{"selection_reason":"quota"}'),
          ('shortlist-run', 'composition:composition-a', 'composition', 'composition-a', 'packet-run', 'composition', 'composition-a', 2.8, 2, 'proposed', '{"selection_reason":"quota"}')
        """
    )
    connection.commit()


class MaterializeSelectiveInterpretationBatchTest(unittest.TestCase):
    def test_prepares_shortlist_gated_batch_with_prompt_and_schema(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"

            connection = sqlite3.connect(db_path)
            seed_interpretation_fixture(connection)
            connection.close()

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "interpret-run",
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--output-dir",
                    str(output_dir),
                    "--limit",
                    "1",
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "interpretation_batch_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["prepared_count"], 1)
            self.assertEqual(metrics["counts_by_item_type"], {"bridge": 1})

            lines = (output_dir / "interpretation_batch.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertEqual(row["shortlist_run_id"], "shortlist-run")
            self.assertEqual(row["shortlist_id"], "bridge:bridge-a")
            self.assertEqual(row["packet_kind"], "bridge")
            self.assertIn("TRANSLATION_CANDIDATE", row["prompt_text"])
            self.assertIn("classification", row["schema_required_fields"])
            self.assertEqual(row["packet_summary"]["max_score"], 2.2)


if __name__ == "__main__":
    unittest.main()
