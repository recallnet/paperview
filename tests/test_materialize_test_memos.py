import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "materialize_test_memos.py"


class MaterializeTestMemosTests(unittest.TestCase):
    def test_materializes_all_three_test_memos(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            runs_root = tmp / "runs"
            (runs_root / "unrealized-run").mkdir(parents=True)
            (runs_root / "transition-run").mkdir(parents=True)
            (runs_root / "findings-run").mkdir(parents=True)
            reports_root = tmp / "reports"
            research_output_path = tmp / "research_output.md"
            db_path = tmp / "paperview.sqlite3"

            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "init_local_store.py"), "--db-path", str(db_path)],
                check=True,
                cwd=ROOT,
            )

            connection = sqlite3.connect(str(db_path))
            try:
                connection.executemany(
                    "INSERT INTO papers (paper_id, source_corpus, title, published_at) VALUES (?, ?, ?, ?)",
                    [
                        ("1902.10743", "arxiv", "Queue Refill Paper", "2025-03-29"),
                        ("2408.03181", "arxiv", "Coupled LOB Paper", "2024-08-06"),
                        ("2406.04969", "arxiv", "LOB Algebra Paper", "2024-06-07"),
                        ("2101.03086", "arxiv", "Auction Queue Paper", "2021-01-08"),
                        ("1011.6402", "arxiv", "Order Book Events Paper", "2011-04-13"),
                        ("cond-mat/0210475", "arxiv", "Double Auction Paper", "2002-10-22"),
                        ("1005.0182", "arxiv", "Multi Agent LOB Paper", "2010-10-28"),
                        ("2009.02808", "arxiv", "LOB Shape Paper", "2020-09-06"),
                    ],
                )
                connection.commit()
            finally:
                connection.close()

            (runs_root / "unrealized-run" / "unrealized_ideas_index.jsonl").write_text(
                '{"result_summary":"Passive quote value after a shock appears to depend on both queue priority and liquidity refill lag rather than on spread alone.","first_step":"Measure queue-position edge after volatility shocks with refill-time controls on recent LOB data.","why_stranded_or_unrealized":"The literature isolates queue value and resiliency separately and stops short of an execution rule that combines them."}\n',
                encoding="utf-8",
            )
            (runs_root / "transition-run" / "transition_state_ledger.jsonl").write_text(
                "\n".join(
                    [
                        '{"pattern_label":"near auction handoff and queue value","result_summary":"Queue value appears to change abruptly at the auction-to-continuous transition, suggesting a distinct post-uncrossing quoting regime.","first_test":"Measure whether queue priority gained immediately after auction uncrossing predicts short-horizon adverse selection.","gap_to_close":"Need a venue-by-venue definition of the auction-to-book state boundary."}',
                        '{"pattern_label":"near auction handoff and refill resiliency","result_summary":"Liquidity refill after auction uncrossing may lag the new price enough to create a brief execution edge."}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (runs_root / "findings-run" / "findings_and_throwaways.jsonl").write_text(
                "\n".join(
                    [
                        '{"section":"accepted","shortlist_id":"bridge:maker_stress_inventory_retreat__queue_value_passive_quoting","result_summary":"Displayed depth can lose protective value when makers retreat under stress, changing what queue position is worth.","first_step":"Backtest queue survival and fill quality when maker inventory stress indicators spike."}',
                        '{"section":"near_miss","paper_id":"2009.02808"}',
                        '{"section":"near_miss","paper_id":"cond-mat/0210475"}',
                        '{"section":"near_miss","paper_id":"1005.0182"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            research_output_path.write_text(
                "# Research Memo\n\nThere may be executable edge in modeling passive quote value immediately after shocks, auctions, or maker withdrawals, especially when refill timing and queue dynamics diverge from naive displayed-depth assumptions.\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "test-memos-run",
                    "--runs-root",
                    str(runs_root),
                    "--reports-root",
                    str(reports_root),
                    "--research-output-path",
                    str(research_output_path),
                    "--unrealized-run-id",
                    "unrealized-run",
                    "--transition-run-id",
                    "transition-run",
                    "--findings-run-id",
                    "findings-run",
                ],
                check=True,
                cwd=ROOT,
            )

            queue_memo = (reports_root / "test-memo-queue-refill.md").read_text(encoding="utf-8")
            auction_memo = (reports_root / "test-memo-auction-handoff.md").read_text(encoding="utf-8")
            maker_memo = (reports_root / "test-memo-maker-retreat.md").read_text(encoding="utf-8")

            self.assertIn("## Thesis", queue_memo)
            self.assertIn("## Event Definitions", queue_memo)
            self.assertIn("## Seam-Aware Policy", queue_memo)
            self.assertIn("1902.10743", queue_memo)

            self.assertIn("## Venue-Specific State Boundary", auction_memo)
            self.assertIn("## Test 1", auction_memo)
            self.assertIn("## Test 2", auction_memo)
            self.assertIn("2101.03086", auction_memo)

            self.assertIn("## Maker Withdrawal Proxies", maker_memo)
            self.assertIn("## Regime Classifier", maker_memo)
            self.assertIn("## Success Metric", maker_memo)
            self.assertIn("1005.0182", maker_memo)


if __name__ == "__main__":
    unittest.main()
