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

    def test_materializes_settlement_lag_resolution_friction_memo(self):
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
                        ("1811.08038", "arxiv", "Arbitrage Opportunities in CDS Term Structure: Theory and Implications for OTC Derivatives", "2018-12-16"),
                        ("1709.08238", "arxiv", "Counterparty Credit Limits: The Impact of a Risk-Mitigation Measure on Everyday Trading", "2021-01-22"),
                        ("1609.04620", "arxiv", "Price impact without order book: A study of the OTC credit index market", "2016-09-15"),
                        ("1101.3926", "arxiv", "Collateral Margining in Arbitrage-Free Counterparty Valuation Adjustment including Re-Hypotecation and Netting", "2011-01-20"),
                        ("1312.0128", "arxiv", "CCPs, Central Clearing, CSA, Credit Collateral and Funding Costs Valuation FAQ: Re-hypothecation, CVA, Closeout, Netting, WWR, Gap-Risk, Initial and Variation Margins, Multiple Discount Curves, FVA?", "2013-12-03"),
                        ("2106.06389", "arxiv", "An Empirical Study of DeFi Liquidations: Incentives, Risks, and Instabilities", "2021-10-01"),
                        ("2009.13235", "arxiv", "Liquidations: DeFi on a Knife-edge", "2021-12-11"),
                    ],
                )
                connection.commit()
            finally:
                connection.close()

            diamond_board_path.write_text(
                "# Diamond Board\n\nModern equivalent: rule-conditioned settlement lag arbitrage\n",
                encoding="utf-8",
            )
            findings_path.write_text(
                "# Findings and Throwaways\n\n`settlement_resolution:composition:market_design_seams__settlement_resolution_seams`\n",
                encoding="utf-8",
            )
            research_output_path.write_text(
                "# Research Memo\n\nModern equivalent: settlement-lag arbitrage and resolution-friction timing\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "lane-memos-test-settlement",
                    "--reports-root",
                    str(reports_root),
                    "--diamond-board-path",
                    str(diamond_board_path),
                    "--findings-path",
                    str(findings_path),
                    "--research-output-path",
                    str(research_output_path),
                    "--memo-id",
                    "settlement-lag-resolution-friction-timing",
                ],
                check=True,
                cwd=ROOT,
            )

            memo = (reports_root / "lane-memo-settlement-lag-resolution-friction-timing.md").read_text(encoding="utf-8")
            self.assertIn("# Settlement-Lag / Resolution-Friction Timing", memo)
            self.assertIn("## Thesis", memo)
            self.assertIn("## Supporting Papers", memo)
            self.assertIn("1811.08038", memo)
            self.assertIn("1709.08238", memo)
            self.assertIn("## Baseline", memo)
            self.assertIn("## First Test", memo)
            self.assertIn("## Metric", memo)
            self.assertIn("## Fail-Fast", memo)
            self.assertIn("## Gap To Close", memo)

    def test_materializes_rule_sensitive_toxic_flow_memo(self):
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
                        ("1104.0587", "arxiv", "How does the market react to your order flow?", "2012-05-01"),
                        ("0908.0202", "arxiv", "Market impact and trading profile of large trading orders in stock markets", "2009-08-03"),
                        ("1903.12458", "arxiv", "Market Manipulation as a Security Problem", "2019-03-29"),
                        ("1311.4160", "arxiv", "Simulating the Synchronizing Behavior of High-Frequency Trading in Multiple Markets", "2013-11-17"),
                        ("2006.08682", "arxiv", "The Importance of Low Latency to Order Book Imbalance Trading Strategies", "2020-06-15"),
                        ("2009.02808", "arxiv", "Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants", "2020-09-06"),
                        ("2003.04425", "arxiv", "Informed trading, limit order book and implementation shortfall: equilibrium and asymptotics", "2020-03-09"),
                    ],
                )
                connection.commit()
            finally:
                connection.close()

            diamond_board_path.write_text(
                "# Diamond Board\n\nModern equivalent: rule-sensitive toxic-flow filters\n",
                encoding="utf-8",
            )
            findings_path.write_text(
                "# Findings and Throwaways\n\n`participant_pathologies:1104.0587`\n",
                encoding="utf-8",
            )
            research_output_path.write_text(
                "# Research Memo\n\nParticipant pathologies such as toxic or manipulative flow may become more predictable when they interact with specific market-design rules.\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "lane-memos-test-toxic",
                    "--reports-root",
                    str(reports_root),
                    "--diamond-board-path",
                    str(diamond_board_path),
                    "--findings-path",
                    str(findings_path),
                    "--research-output-path",
                    str(research_output_path),
                    "--memo-id",
                    "rule-sensitive-toxic-flow-filters",
                ],
                check=True,
                cwd=ROOT,
            )

            memo = (reports_root / "lane-memo-rule-sensitive-toxic-flow-filters.md").read_text(encoding="utf-8")
            self.assertIn("# Rule-Sensitive Toxic-Flow Filters", memo)
            self.assertIn("## Thesis", memo)
            self.assertIn("## Supporting Papers", memo)
            self.assertIn("1104.0587", memo)
            self.assertIn("0908.0202", memo)
            self.assertIn("## Baseline", memo)
            self.assertIn("## First Test", memo)
            self.assertIn("## Metric", memo)
            self.assertIn("## Fail-Fast", memo)
            self.assertIn("## Gap To Close", memo)


if __name__ == "__main__":
    unittest.main()
