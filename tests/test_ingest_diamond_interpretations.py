import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "ingest_diamond_interpretations.py"
JSON_SCHEMA_PATH = ROOT / "schemas" / "diamond_interpretation.schema.json"


def seed_ingest_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.commit()


class IngestDiamondInterpretationsTests(unittest.TestCase):
    def test_ingests_valid_rows_and_accepts_transition_seam(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"
            batch_path = tmp_path / "diamond_interpretation_batch.jsonl"
            responses_path = tmp_path / "responses.jsonl"

            connection = sqlite3.connect(db_path)
            seed_ingest_fixture(connection)
            connection.close()

            batch_items = [
                {
                    "batch_item_id": "transition_state:near_transition_queue_refill:p1",
                    "lane_family": "transition_state",
                    "operator_family": "transition_state",
                    "source_kind": "transition_state_candidate",
                    "source_run_id": "transition-run",
                    "source_ref": "p1",
                    "family_rank": 1,
                    "shortlist_rank": 1,
                    "selection_bucket": "lane_quota",
                    "source_score": 0.77,
                    "diamond_score": 0.83,
                    "packet_title": "Transition packet",
                },
                {
                    "batch_item_id": "stranded_qfin:p2",
                    "lane_family": "stranded_qfin",
                    "operator_family": "stranded_qfin",
                    "source_kind": "stranded_resurfacing_candidate",
                    "source_run_id": "stranded-run",
                    "source_ref": "p2",
                    "family_rank": 1,
                    "shortlist_rank": 2,
                    "selection_bucket": "lane_quota",
                    "source_score": 0.62,
                    "diamond_score": 0.66,
                    "packet_title": "Stranded packet",
                },
            ]
            with batch_path.open("w", encoding="utf-8") as handle:
                for item in batch_items:
                    handle.write(json.dumps(item, sort_keys=True) + "\n")

            responses = [
                {
                    "batch_item_id": "transition_state:near_transition_queue_refill:p1",
                    "interpretation": {
                        "classification": "TRANSITION_SEAM",
                        "result_summary": "Queue value changes at the transition boundary.",
                        "first_test": "Measure queue-priority quality immediately after the state switch.",
                        "instrument_assumed": "opening auction handoff",
                        "modern_equivalent": "auction handoff queue model",
                        "why_stranded_or_unrealized": "The seam was discussed indirectly rather than as a direct edge hypothesis.",
                        "gap_to_close": "Need exact venue state-boundary timestamps.",
                        "confidence": "medium",
                    },
                },
                {
                    "batch_item_id": "stranded_qfin:p2",
                    "interpretation": {
                        "classification": "STRANDED_QFIN_RESULT",
                        "result_summary": "Impact-aware execution control still looks testable.",
                        "first_test": "Replay the control against recent intraday data.",
                        "instrument_assumed": "intraday execution",
                        "modern_equivalent": "impact-aware adaptive execution",
                        "why_stranded_or_unrealized": "It remained framed as theory-heavy q-fin.",
                        "gap_to_close": "Need modern hidden-liquidity robustness checks.",
                        "confidence": "high",
                    },
                },
                {
                    "batch_item_id": "transition_state:near_transition_queue_refill:p1",
                    "interpretation": {
                        "classification": "BAD_CLASS",
                        "result_summary": "bad",
                        "first_test": "bad",
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
                        "result_summary": "unknown",
                        "first_test": "unknown",
                        "instrument_assumed": "unknown",
                        "modern_equivalent": "unknown",
                        "why_stranded_or_unrealized": "unknown",
                        "gap_to_close": "unknown",
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
                    "diamond-ingest-run",
                    "--batch-run-id",
                    "diamond-batch-run",
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
                SELECT batch_item_id, classification
                FROM diamond_interpretations
                WHERE run_id = 'diamond-ingest-run'
                ORDER BY batch_item_id
                """
            ).fetchall()
            connection.close()

            self.assertEqual(
                [(row["batch_item_id"], row["classification"]) for row in rows],
                [
                    ("stranded_qfin:p2", "STRANDED_QFIN_RESULT"),
                    ("transition_state:near_transition_queue_refill:p1", "TRANSITION_SEAM"),
                ],
            )

            metrics = json.loads((output_dir / "diamond_interpretation_ingestion_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["accepted_count"], 2)
            self.assertEqual(metrics["rejected_count"], 2)
            self.assertEqual(metrics["counts_by_classification"]["TRANSITION_SEAM"], 1)
            rejection_lines = (output_dir / "diamond_interpretation_rejections.jsonl").read_text(encoding="utf-8").strip().splitlines()
            reasons = {json.loads(line)["reason"] for line in rejection_lines}
            self.assertTrue(any(reason.startswith("invalid_enum:classification:BAD_CLASS") for reason in reasons))
            self.assertIn("unknown_batch_item_id", reasons)


if __name__ == "__main__":
    unittest.main()
