import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_run_summary.py"


class MaterializeRunSummaryTests(unittest.TestCase):
    def test_materializes_reconciled_root_summary(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            runs_root = tmp_path / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            connection = sqlite3.connect(db_path)
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            connection.executemany(
                """
                INSERT INTO enhanced_interpretations (
                  run_id, batch_run_id, batch_item_id, operator_family, source_kind, source_run_id, source_ref,
                  family_rank, source_score, packet_title, classification, result_summary, first_step,
                  instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close,
                  confidence, raw_json
                ) VALUES (?, 'batch-run', ?, ?, 'fixture', 'source-run', ?, ?, 1.0, ?, ?, 'result', 'step', 'instrument', 'modern', 'why', 'gap', 'high', '{}')
                """,
                [
                    ("enhanced-run", "market_design:item-a", "market_design", "market_design:item-a", 1, "Market design packet", "TRANSLATION_CANDIDATE"),
                    ("enhanced-run", "stranded_qfin:item-b", "stranded_qfin", "stranded_qfin:item-b", 1, "Stranded packet", "STRANDED_QFIN_RESULT"),
                    ("enhanced-run", "transition_state:item-c", "transition_state", "transition_state:item-c", 1, "Transition packet", "TRANSLATION_CANDIDATE"),
                    ("enhanced-run", "market_design:item-reject", "market_design", "market_design:item-reject", 2, "Rejected packet", "NO_TRANSLATION"),
                ],
            )
            connection.commit()
            connection.close()

            (runs_root / "shortlist-run").mkdir()
            (runs_root / "enhanced-run").mkdir()
            (runs_root / "unrealized-run").mkdir()
            (runs_root / "stranded-run").mkdir()
            (runs_root / "transition-run").mkdir()
            (runs_root / "findings-run").mkdir()

            (runs_root / "shortlist-run" / "shortlist_metrics.json").write_text('{"shortlist_count": 7}\n', encoding="utf-8")
            (runs_root / "enhanced-run" / "enhanced_interpretation_ingestion_metrics.json").write_text(
                '{"accepted_count": 3, "rejected_count": 1}\n',
                encoding="utf-8",
            )
            (runs_root / "unrealized-run" / "unrealized_ideas_index_metrics.json").write_text(
                '{"entry_count": 1}\n',
                encoding="utf-8",
            )
            (runs_root / "unrealized-run" / "unrealized_ideas_index.jsonl").write_text(
                '{"publication_item_id":"market_design:item-a","item_type":"market_design"}\n',
                encoding="utf-8",
            )
            (runs_root / "stranded-run" / "stranded_result_ledger_metrics.json").write_text(
                '{"entry_count": 1}\n',
                encoding="utf-8",
            )
            (runs_root / "stranded-run" / "stranded_result_ledger.jsonl").write_text(
                '{"publication_item_id":"stranded_qfin:item-b"}\n',
                encoding="utf-8",
            )
            (runs_root / "transition-run" / "transition_state_ledger_metrics.json").write_text(
                '{"entry_count": 1}\n',
                encoding="utf-8",
            )
            (runs_root / "transition-run" / "transition_state_ledger.jsonl").write_text(
                '{"publication_item_id":"transition_state:item-c"}\n',
                encoding="utf-8",
            )
            (runs_root / "findings-run" / "findings_and_throwaways_metrics.json").write_text(
                '{"accepted_count": 3, "rejected_count": 1, "near_miss_count": 4, "stranded_qfin_failure_count": 1}\n',
                encoding="utf-8",
            )
            (runs_root / "findings-run" / "findings_and_throwaways.jsonl").write_text(
                "\n".join(
                    [
                        '{"section":"accepted","shortlist_id":"market_design:item-a","operator_family":"market_design"}',
                        '{"section":"accepted","shortlist_id":"stranded_qfin:item-b","operator_family":"stranded_qfin"}',
                        '{"section":"accepted","shortlist_id":"transition_state:item-c","operator_family":"transition_state"}',
                        '{"section":"rejected","shortlist_id":"market_design:item-reject","operator_family":"market_design"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            output_json = tmp_path / "run_summary.json"
            output_md = tmp_path / "run_summary.md"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "run-summary-test",
                    "--runs-root",
                    str(runs_root),
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--enhanced-interpretation-run-id",
                    "enhanced-run",
                    "--unrealized-run-id",
                    "unrealized-run",
                    "--stranded-run-id",
                    "stranded-run",
                    "--transition-run-id",
                    "transition-run",
                    "--findings-run-id",
                    "findings-run",
                    "--output-json-path",
                    str(output_json),
                    "--output-md-path",
                    str(output_md),
                ],
                check=True,
                cwd=ROOT,
            )

            summary = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["counts"]["shortlist_count"], 7)
            self.assertEqual(summary["counts"]["enhanced_interpretation_accepted_count"], 3)
            self.assertEqual(summary["counts"]["published_entry_count"], 3)
            self.assertEqual(summary["accepted_by_lane"]["market_design"], 1)
            self.assertEqual(summary["published_by_lane"]["transition_state"], 1)
            self.assertEqual(summary["reconciliation"]["accepted_not_in_findings"], [])
            self.assertEqual(summary["reconciliation"]["accepted_not_in_publication"], [])
            self.assertTrue(summary["reconciliation"]["all_accepted_items_exposed"])

            markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("# Canonical Run Summary", markdown)
            self.assertIn("accepted enhanced interpretations: `3`", markdown)
            self.assertIn("all accepted items exposed: `true`", markdown)


if __name__ == "__main__":
    unittest.main()
