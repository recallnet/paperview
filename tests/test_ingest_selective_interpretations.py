import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "ingest_selective_interpretations.py"
JSON_SCHEMA_PATH = ROOT / "schemas" / "selective_interpretation.schema.json"


def seed_interpretation_ingest_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.execute(
        """
        INSERT INTO shortlist_items (
          run_id, shortlist_id, item_type, item_ref, packet_run_id, packet_kind, packet_item_ref,
          score, shortlist_rank, status, rationale_json
        )
        VALUES
          ('shortlist-run', 'bridge:bridge-a', 'bridge', 'bridge-a', 'packet-run', 'bridge', 'bridge-a', 2.2, 1, 'proposed', '{}'),
          ('shortlist-run', 'paper:paper-a', 'paper', 'paper-a', 'packet-run', 'stranded_qfin', 'paper-a', 1.2, 2, 'proposed', '{}')
        """
    )
    connection.commit()


class IngestSelectiveInterpretationsTest(unittest.TestCase):
    def test_ingests_valid_rows_and_rejects_invalid_or_unknown(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"
            responses_path = tmp_path / "responses.jsonl"

            connection = sqlite3.connect(db_path)
            seed_interpretation_ingest_fixture(connection)
            connection.close()

            responses = [
                {
                    "shortlist_id": "bridge:bridge-a",
                    "interpretation": {
                        "classification": "TRANSLATION_CANDIDATE",
                        "result_summary": "Bridge idea summary",
                        "first_step": "Replicate on recent data",
                        "instrument_assumed": "cross-venue spread",
                        "modern_equivalent": "DEX arbitrage",
                        "why_stranded_or_unrealized": "venue tooling lagged",
                        "gap_to_close": "execution integration",
                        "confidence": "medium",
                    },
                },
                {
                    "shortlist_id": "paper:paper-a",
                    "interpretation": {
                        "classification": "NO_TRANSLATION",
                        "result_summary": "Interesting but not translatable",
                        "first_step": "Do nothing yet",
                        "instrument_assumed": "none",
                        "modern_equivalent": "none",
                        "why_stranded_or_unrealized": "general property only",
                        "gap_to_close": "no concrete path",
                        "confidence": "high",
                    },
                },
                {
                    "shortlist_id": "bridge:bridge-a",
                    "interpretation": {
                        "classification": "BAD_CLASS",
                        "result_summary": "bad",
                        "first_step": "bad",
                        "instrument_assumed": "bad",
                        "modern_equivalent": "bad",
                        "why_stranded_or_unrealized": "bad",
                        "gap_to_close": "bad",
                        "confidence": "low",
                    },
                },
                {
                    "shortlist_id": "unknown:item",
                    "interpretation": {
                        "classification": "TRANSLATION_CANDIDATE",
                        "result_summary": "unknown shortlist",
                        "first_step": "bad",
                        "instrument_assumed": "bad",
                        "modern_equivalent": "bad",
                        "why_stranded_or_unrealized": "bad",
                        "gap_to_close": "bad",
                        "confidence": "low",
                    },
                },
            ]
            with responses_path.open("w", encoding="utf-8") as handle:
                for item in responses:
                    handle.write(json.dumps(item, sort_keys=True) + "\n")

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "ingest-run",
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--responses-path",
                    str(responses_path),
                    "--schema-path",
                    str(JSON_SCHEMA_PATH),
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            connection = sqlite3.connect(db_path)
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT shortlist_id, classification
                FROM selective_interpretations
                WHERE run_id = 'ingest-run'
                ORDER BY shortlist_id
                """
            ).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                [(row["shortlist_id"], row["classification"]) for row in rows],
                [("bridge:bridge-a", "TRANSLATION_CANDIDATE"), ("paper:paper-a", "NO_TRANSLATION")],
            )

            metrics = json.loads((output_dir / "interpretation_ingestion_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["accepted_count"], 2)
            self.assertEqual(metrics["rejected_count"], 2)
            self.assertEqual(metrics["counts_by_classification"]["NO_TRANSLATION"], 1)

            rejection_lines = (output_dir / "interpretation_rejections.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(rejection_lines), 2)
            reasons = {json.loads(line)["reason"] for line in rejection_lines}
            self.assertTrue(any(reason.startswith("invalid_enum:classification:BAD_CLASS") for reason in reasons))
            self.assertIn("unknown_shortlist_id", reasons)

            connection.close()


if __name__ == "__main__":
    unittest.main()
