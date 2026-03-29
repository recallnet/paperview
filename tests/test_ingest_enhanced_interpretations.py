import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "ingest_enhanced_interpretations.py"
JSON_SCHEMA_PATH = ROOT / "schemas" / "selective_interpretation.schema.json"


def seed_enhanced_ingest_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.commit()


class IngestEnhancedInterpretationsTest(unittest.TestCase):
    def test_ingests_valid_rows_and_rejects_invalid_or_unknown(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"
            batch_path = tmp_path / "enhanced_interpretation_batch.jsonl"
            responses_path = tmp_path / "responses.jsonl"

            connection = sqlite3.connect(db_path)
            seed_enhanced_ingest_fixture(connection)
            connection.close()

            batch_rows = [
                {
                    "batch_item_id": "market_design:bridge:market_design_seams__refill_lag_local_shock",
                    "operator_family": "market_design",
                    "lane_family": "market_design",
                    "source_kind": "review_packet_bridge",
                    "source_run_id": "batch-run",
                    "source_ref": "market_design_seams__refill_lag_local_shock",
                    "family_rank": 1,
                    "score": 2.2,
                    "packet_title": "Market Design A",
                },
                {
                    "batch_item_id": "stranded_qfin:paper-a",
                    "operator_family": "stranded_qfin",
                    "lane_family": "stranded_qfin",
                    "source_kind": "stranded_resurfacing_candidate",
                    "source_run_id": "batch-run",
                    "source_ref": "paper-a",
                    "family_rank": 2,
                    "score": 1.2,
                    "packet_title": "Paper A",
                },
            ]
            batch_path.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in batch_rows),
                encoding="utf-8",
            )

            responses = [
                {
                    "batch_item_id": "market_design:bridge:market_design_seams__refill_lag_local_shock",
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
                    "batch_item_id": "stranded_qfin:paper-a",
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
                    "batch_item_id": "market_design:bridge:market_design_seams__refill_lag_local_shock",
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
                    "batch_item_id": "unknown:item",
                    "interpretation": {
                        "classification": "TRANSLATION_CANDIDATE",
                        "result_summary": "unknown batch item",
                        "first_step": "bad",
                        "instrument_assumed": "bad",
                        "modern_equivalent": "bad",
                        "why_stranded_or_unrealized": "bad",
                        "gap_to_close": "bad",
                        "confidence": "low",
                    },
                },
            ]
            responses_path.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in responses),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "ingest-run",
                    "--batch-run-id",
                    "batch-run",
                    "--batch-path",
                    str(batch_path),
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
                SELECT batch_item_id, operator_family, lane_family, classification
                FROM enhanced_interpretations
                WHERE run_id = 'ingest-run'
                ORDER BY batch_item_id
                """
            ).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                [
                    (
                        row["batch_item_id"],
                        row["operator_family"],
                        row["lane_family"],
                        row["classification"],
                    )
                    for row in rows
                ],
                [
                    (
                        "market_design:bridge:market_design_seams__refill_lag_local_shock",
                        "market_design",
                        "market_design",
                        "TRANSLATION_CANDIDATE",
                    ),
                    ("stranded_qfin:paper-a", "stranded_qfin", "stranded_qfin", "NO_TRANSLATION"),
                ],
            )

            metrics = json.loads((output_dir / "enhanced_interpretation_ingestion_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["accepted_count"], 2)
            self.assertEqual(metrics["rejected_count"], 2)
            self.assertEqual(metrics["counts_by_classification"]["NO_TRANSLATION"], 1)
            self.assertEqual(metrics["counts_by_operator_family"]["market_design"], 1)
            self.assertEqual(metrics["counts_by_operator_family"]["stranded_qfin"], 1)

            rejection_lines = (output_dir / "enhanced_interpretation_rejections.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(rejection_lines), 2)
            reasons = {json.loads(line)["reason"] for line in rejection_lines}
            self.assertTrue(any(reason.startswith("invalid_enum:classification:BAD_CLASS") for reason in reasons))
            self.assertIn("unknown_batch_item_id", reasons)

            connection.close()


if __name__ == "__main__":
    unittest.main()
