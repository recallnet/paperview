import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "materialize_lane_memos.py"


class MaterializeLaneMemosTests(unittest.TestCase):
    def test_materializes_market_design_delayed_parity_repair_memo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports_root = tmp / "reports"
            db_path = tmp / "paperview.sqlite3"
            diamond_board_path = tmp / "diamond_board.md"
            findings_path = tmp / "findings_and_throwaways.md"
            research_output_path = tmp / "research_output.md"

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
                        ("1609.04620", "arxiv", "Price impact without order book: A study of the OTC credit index market", "2016-09-15"),
                        ("1811.08038", "arxiv", "Arbitrage Opportunities in CDS Term Structure: Theory and Implications for OTC Derivatives", "2018-12-16"),
                        ("1709.08238", "arxiv", "Counterparty Credit Limits: The Impact of a Risk-Mitigation Measure on Everyday Trading", "2021-01-22"),
                        ("2011.04367", "arxiv", "Comparing the market microstructure between two South African exchanges", "2020-11-09"),
                        ("2004.12011", "arxiv", "Trading Foreign Exchange Triplets", "2020-04-24"),
                    ],
                )
                connection.commit()
            finally:
                connection.close()

            diamond_board_path.write_text(
                "# Diamond Board\n\nModern equivalent: venue-shaped delayed parity repair\n",
                encoding="utf-8",
            )
            findings_path.write_text(
                "# Findings and Throwaways\n\n`market_design:composition:market_design_seams__parity_propagation`\n",
                encoding="utf-8",
            )
            research_output_path.write_text(
                "# Research Memo\n\nCross-market inconsistencies may persist longer when the connected venues enforce different trading or protection rules.\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "lane-memos-test",
                    "--reports-root",
                    str(reports_root),
                    "--diamond-board-path",
                    str(diamond_board_path),
                    "--findings-path",
                    str(findings_path),
                    "--research-output-path",
                    str(research_output_path),
                    "--memo-id",
                    "market-design-delayed-parity-repair",
                ],
                check=True,
                cwd=ROOT,
            )

            memo = (reports_root / "lane-memo-market-design-delayed-parity-repair.md").read_text(encoding="utf-8")
            self.assertIn("# Market-Design Delayed Parity Repair", memo)
            self.assertIn("## Thesis", memo)
            self.assertIn("## Supporting Papers", memo)
            self.assertIn("1609.04620", memo)
            self.assertIn("1811.08038", memo)
            self.assertIn("## Baseline", memo)
            self.assertIn("## First Test", memo)
            self.assertIn("## Metric", memo)
            self.assertIn("## Fail-Fast", memo)
            self.assertIn("## Gap To Close", memo)


if __name__ == "__main__":
    unittest.main()
