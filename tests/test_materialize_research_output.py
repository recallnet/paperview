import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "materialize_research_output.py"


class MaterializeResearchOutputTests(unittest.TestCase):
    def test_materializes_report_as_research_memo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runs_root = tmp / "runs"
            (runs_root / "unrealized-run").mkdir(parents=True)
            (runs_root / "stranded-run").mkdir(parents=True)
            (runs_root / "transition-run").mkdir(parents=True)
            (runs_root / "findings-run").mkdir(parents=True)
            (runs_root / "stranding-score-materialization-20260328").mkdir(parents=True)
            (runs_root / "shortlist-run").mkdir(parents=True)
            (runs_root / "enhanced-run").mkdir(parents=True)
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
                "\n".join(
                    [
                        '{"paper_id":"2106.00581","confidence":"medium","priority_tier":"p2","result_summary":"Stranded result one","why_stranded_or_unrealized":"Buried in q-fin language","modern_equivalent":"Adaptive execution","first_test":"Replay on modern data","gap_to_close":"Need queue evidence"}',
                        '{"paper_id":"2204.08581","confidence":"high","priority_tier":"p2","result_summary":"Stranded result two","why_stranded_or_unrealized":"Buried in execution calibration language","modern_equivalent":"Execution policy search with fast surrogates","first_test":"Replay on fragmented data","gap_to_close":"Need regime stability evidence"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (runs_root / "stranded-run" / "stranded_result_ledger_metrics.json").write_text(
                '{"entry_count":2}\n',
                encoding="utf-8",
            )

            (runs_root / "transition-run" / "transition_state_ledger.jsonl").write_text(
                "\n".join(
                    [
                        '{"pattern_label":"near auction handoff and queue value","paper_id":"2101.03086","confidence":"medium","priority_tier":"p1","result_summary":"Transition result one","why_stranded_or_unrealized":"Not framed as a trading seam","modern_equivalent":"Auction handoff queue-value model","first_test":"Measure the handoff","gap_to_close":"Need venue boundary"}',
                        '{"pattern_label":"near auction handoff and refill resiliency","paper_id":"1011.6402","confidence":"medium","priority_tier":"p1","result_summary":"Transition result two","why_stranded_or_unrealized":"Not framed as a trading seam","modern_equivalent":"Auction handoff refill-lag monitor","first_test":"Measure refill lag","gap_to_close":"Need higher resolution data"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (runs_root / "transition-run" / "transition_state_ledger_metrics.json").write_text(
                '{"entry_count":2}\n',
                encoding="utf-8",
            )

            (runs_root / "findings-run" / "findings_and_throwaways.jsonl").write_text(
                "\n".join(
                    [
                        '{"section":"accepted","operator_family":"bridge","shortlist_id":"bridge:test","classification":"COMPOSITIONAL_CANDIDATE"}',
                        '{"section":"accepted","operator_family":"bridge","shortlist_id":"bridge:maker_stress_inventory_retreat__queue_value_passive_quoting","classification":"TRANSLATION_CANDIDATE","result_summary":"Displayed depth can lose protective value when makers retreat under stress, changing what queue position is worth.","first_step":"Backtest queue survival during maker withdrawal."}',
                        '{"section":"rejected","operator_family":"unknown","shortlist_id":"bridge:bad","reason":"invalid_enum:classification:BAD_CLASS","title":"Rejected packet"}',
                        '{"section":"near_miss","operator_family":"bridge","paper_id":"paper-c","title":"Near Miss","score":1.2,"operator_label":"queue x refill"}',
                        '{"section":"near_miss","operator_family":"bridge","paper_id":"2009.02808","title":"Queue Near Miss","score":1.2,"operator_label":"queue x refill"}',
                        '{"section":"near_miss","operator_family":"bridge","paper_id":"cond-mat/0210475","title":"Auction Near Miss","score":1.1,"operator_label":"auction x refill"}',
                        '{"section":"near_miss","operator_family":"bridge","paper_id":"1005.0182","title":"Maker Near Miss","score":1.0,"operator_label":"maker x queue"}',
                        '{"section":"near_miss","operator_family":"contrast","paper_id":"2205.14699","title":"DeFi Near Miss One","score":0.9,"operator_label":"settlement contrast"}',
                        '{"section":"near_miss","operator_family":"contrast","paper_id":"2012.13230","title":"DeFi Near Miss Two","score":0.8,"operator_label":"pool contrast"}',
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
            (runs_root / "stranding-score-materialization-20260328" / "stranding_score_metrics.json").write_text(
                '{"scored_papers":17323}\n',
                encoding="utf-8",
            )
            (runs_root / "shortlist-run" / "shortlist_metrics.json").write_text(
                '{"shortlist_count":24}\n',
                encoding="utf-8",
            )
            (runs_root / "enhanced-run" / "enhanced_interpretation_ingestion_metrics.json").write_text(
                '{"accepted_count":8}\n',
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
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--enhanced-interpretation-run-id",
                    "enhanced-run",
                    "--output-path",
                    str(output_path),
                ],
                check=True,
                cwd=ROOT,
            )

            report = output_path.read_text(encoding="utf-8")
            self.assertIn("# Research Memo", report)
            self.assertIn(
                "There may be executable edge in modeling passive quote value immediately after shocks, auctions, or maker withdrawals, especially when refill timing and queue dynamics diverge from naive displayed-depth assumptions.",
                report,
            )
            self.assertIn("## Three Best Practical Leads", report)
            self.assertIn("## The Stranded Results That Came Back", report)
            self.assertIn("## The Transition-State Seam Map", report)
            self.assertIn("## The Conversion Funnel", report)
            self.assertIn("## What To Do Next", report)
            self.assertIn("## The Near-Misses That Matter", report)
            self.assertIn("Idea result", report)
            self.assertIn("Stranded result one", report)
            self.assertIn("Transition result one", report)
            self.assertNotIn("publication id", report.lower())
            self.assertNotIn("publication item id", report.lower())
            self.assertNotRegex(report.lower(), r"score[: ]+`")


if __name__ == "__main__":
    unittest.main()
