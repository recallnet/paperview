import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "materialize_research_output.py"


class MaterializeResearchOutputTests(unittest.TestCase):
    def test_materializes_report_with_required_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runs_root = tmp / "runs"
            (runs_root / "unrealized-run").mkdir(parents=True)
            (runs_root / "stranded-run").mkdir(parents=True)
            (runs_root / "transition-run").mkdir(parents=True)
            (runs_root / "findings-run").mkdir(parents=True)
            db_path = tmp / "paperview.sqlite3"

            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "init_local_store.py"), "--db-path", str(db_path)],
                check=True,
                cwd=ROOT,
            )

            (runs_root / "unrealized-run" / "unrealized_ideas_index.jsonl").write_text(
                '{"publication_item_id":"bridge:test","classification":"COMPOSITIONAL_CANDIDATE","confidence":"medium","title":"Bridge packet: queue x refill","result_summary":"Idea result","modern_equivalent":"Modern clue","first_step":"Run the first test","why_stranded_or_unrealized":"No one combined the ideas","rationale":{"top_holdout_echoes":[{"paper_id":"p1","title":"Echo One","echo_score":0.8}]}}\n',
                encoding="utf-8",
            )
            (runs_root / "unrealized-run" / "unrealized_ideas_index_metrics.json").write_text(
                '{"entry_count":1}\n',
                encoding="utf-8",
            )

            (runs_root / "stranded-run" / "stranded_result_ledger.jsonl").write_text(
                '{"publication_item_id":"stranded_qfin:test","paper_id":"paper-a","confidence":"high","priority_tier":"p1","result_summary":"Stranded result","why_stranded_or_unrealized":"Buried in q-fin language","instrument_assumed":"Execution control","modern_equivalent":"Adaptive execution","first_test":"Replay on modern data","gap_to_close":"Need queue evidence"}\n',
                encoding="utf-8",
            )
            (runs_root / "stranded-run" / "stranded_result_ledger_metrics.json").write_text(
                '{"entry_count":1}\n',
                encoding="utf-8",
            )

            (runs_root / "transition-run" / "transition_state_ledger.jsonl").write_text(
                '{"publication_item_id":"transition_state:test","pattern_label":"near auction handoff and queue value","paper_id":"paper-b","confidence":"medium","priority_tier":"p1","result_summary":"Transition result","why_stranded_or_unrealized":"Not framed as a trading seam","instrument_assumed":"Auction transition","modern_equivalent":"Auction handoff monitor","first_test":"Measure the handoff","gap_to_close":"Need venue boundary"}\n',
                encoding="utf-8",
            )
            (runs_root / "transition-run" / "transition_state_ledger_metrics.json").write_text(
                '{"entry_count":1}\n',
                encoding="utf-8",
            )

            (runs_root / "findings-run" / "findings_and_throwaways.jsonl").write_text(
                "\n".join(
                    [
                        '{"section":"accepted","operator_family":"bridge","shortlist_id":"bridge:test","classification":"COMPOSITIONAL_CANDIDATE"}',
                        '{"section":"rejected","operator_family":"unknown","shortlist_id":"bridge:bad","reason":"invalid_enum:classification:BAD_CLASS","title":"Rejected packet"}',
                        '{"section":"near_miss","operator_family":"bridge","paper_id":"paper-c","title":"Near Miss","score":1.2,"operator_label":"queue x refill"}',
                        '{"section":"stranded_qfin_failure","operator_family":"stranded_resurfacing","paper_id":"paper-d","title":"Failed Stranded","failure_reason":"not_shortlisted_for_interpretation"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (runs_root / "findings-run" / "findings_and_throwaways_metrics.json").write_text(
                '{"accepted_count":1,"rejected_count":1,"near_miss_count":1,"stranded_qfin_failure_count":1}\n',
                encoding="utf-8",
            )

            output_path = tmp / "research_output.md"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "research-output-run",
                    "--runs-root",
                    str(runs_root),
                    "--unrealized-run-id",
                    "unrealized-run",
                    "--stranded-run-id",
                    "stranded-run",
                    "--transition-run-id",
                    "transition-run",
                    "--findings-run-id",
                    "findings-run",
                    "--output-path",
                    str(output_path),
                ],
                check=True,
                cwd=ROOT,
            )

            report = output_path.read_text(encoding="utf-8")
            self.assertIn("# Research Output", report)
            self.assertIn("## Executive Summary", report)
            self.assertIn("## Unrealized Cross-Domain Ideas", report)
            self.assertIn("## Stranded Q-Fin Results", report)
            self.assertIn("## Transition-State Microstructure Seams", report)
            self.assertIn("## Near-Misses and Throwaways", report)
            self.assertIn("## What to Investigate Next", report)
            self.assertIn("Idea result", report)
            self.assertIn("Stranded result", report)
            self.assertIn("Transition result", report)


if __name__ == "__main__":
    unittest.main()
