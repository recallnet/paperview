import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_ds2_bridge_zones.py"


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO anchors (anchor_id, label, anchor_type, tags_json) VALUES
          ('auction_parimutuel_design', 'Auction / pari-mutuel / contingent-claim design', 'positive', '[]'),
          ('auction_handoff', 'Auction handoff / reopening seam', 'positive', '[]'),
          ('refill_lag_local_shock', 'Refill lag / local shock', 'positive', '[]'),
          ('refill_lag_resiliency', 'Refill lag / resiliency', 'positive', '[]'),
          ('amm_settlement_latency', 'AMM / settlement latency', 'positive', '[]'),
          ('settlement_resolution_seams', 'Settlement / resolution seams', 'positive', '[]'),
          ('parity_propagation_delayed_repair', 'Parity propagation / delayed repair', 'positive', '[]'),
          ('state_graph_inconsistencies', 'State-graph inconsistencies', 'positive', '[]'),
          ('market_design_seams', 'Market-design seams', 'positive', '[]'),
          ('participant_pathologies', 'Participant pathologies', 'positive', '[]'),
          ('queue_value_passive_quoting', 'Queue value / passive quoting', 'positive', '[]'),
          ('lifecycle_professionalization', 'Lifecycle / professionalization', 'positive', '[]');

        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at) VALUES
          ('p-auction', 'arxiv', 'Price impact in equity auctions', 'q-fin.TR', '2023-01-01'),
          ('p-double-auction', 'arxiv', 'Statistical theory of the continuous double auction', 'cond-mat.stat-mech', '2002-10-01'),
          ('p-settlement', 'arxiv', 'Risks in arbitrage and market-making in blockchain-based currency markets', 'econ.GN', '2023-04-17'),
          ('p-derivatives', 'arxiv', 'Arbitrage Opportunities in CDS Term Structure', 'q-fin.PR', '2018-11-19'),
          ('p-design', 'arxiv', 'Market Manipulation as a Security Problem', 'q-fin.TR', '2019-03-28'),
          ('p-hft', 'arxiv', 'Simulating the Synchronizing Behavior of High-Frequency Trading in Multiple Markets', 'q-fin.TR', '2013-11-17'),
          ('p-queue', 'arxiv', 'Automated Liquidity Provision and the Demise of Traditional Market Making', 'q-fin.TR', '2010-07-14'),
          ('p-latency', 'arxiv', 'The Importance of Low Latency to Order Book Imbalance Trading Strategies', 'q-fin.TR', '2020-06-15'),
          ('p-defi', 'arxiv', 'Behavior of Liquidity Providers in Decentralized Exchanges', 'q-fin.CP', '2021-10-11'),
          ('p-adoption', 'arxiv', 'The Adoption of Blockchain-based Decentralized Exchanges', 'q-fin.TR', '2021-07-21');

        INSERT INTO bridge_candidates (run_id, source_anchor_id, target_anchor_id, paper_id, bridge_score, bridge_rank, rationale_json) VALUES
          ('bridge-materialization-20260328-broadened', 'auction_parimutuel_design', 'refill_lag_local_shock', 'p-double-auction', 2.35, 1, '{}'),
          ('bridge-materialization-20260328-broadened', 'auction_handoff', 'refill_lag_local_shock', 'p-auction', 2.27, 2, '{}'),
          ('bridge-materialization-20260328-broadened', 'amm_settlement_latency', 'parity_propagation_delayed_repair', 'p-settlement', 1.93, 1, '{}'),
          ('bridge-materialization-20260328-broadened', 'settlement_resolution_seams', 'state_graph_inconsistencies', 'p-derivatives', 1.87, 2, '{}'),
          ('bridge-materialization-20260328-broadened', 'market_design_seams', 'participant_pathologies', 'p-design', 2.40, 1, '{}'),
          ('bridge-materialization-20260328-broadened', 'auction_handoff', 'participant_pathologies', 'p-hft', 2.36, 2, '{}'),
          ('bridge-materialization-20260328-broadened', 'queue_value_passive_quoting', 'market_design_seams', 'p-latency', 2.31, 1, '{}'),
          ('bridge-materialization-20260328-broadened', 'lifecycle_professionalization', 'market_design_seams', 'p-adoption', 2.19, 1, '{}'),
          ('bridge-materialization-20260328-broadened', 'lifecycle_professionalization', 'participant_pathologies', 'p-defi', 2.18, 2, '{}');

        INSERT INTO composition_candidates (run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json) VALUES
          ('composition-materialization-20260328-broadened', 'auction_handoff', 'refill_lag_resiliency', 'p-auction', 3.24, 1, '{}'),
          ('composition-materialization-20260328-broadened', 'settlement_resolution_seams', 'state_graph_inconsistencies', 'p-settlement', 3.14, 1, '{}'),
          ('composition-materialization-20260328-broadened', 'market_design_seams', 'participant_pathologies', 'p-design', 3.25, 1, '{}'),
          ('composition-materialization-20260328-broadened', 'queue_value_passive_quoting', 'lifecycle_professionalization', 'p-queue', 3.19, 1, '{}'),
          ('composition-materialization-20260328-broadened', 'queue_value_passive_quoting', 'participant_pathologies', 'p-latency', 3.16, 2, '{}'),
          ('composition-materialization-20260328-broadened', 'lifecycle_professionalization', 'market_design_seams', 'p-defi', 3.23, 1, '{}'),
          ('composition-materialization-20260328-broadened', 'amm_settlement_latency', 'settlement_resolution_seams', 'p-adoption', 3.11, 2, '{}');
        """
    )
    connection.commit()


class MaterializeDs2BridgeZonesTests(unittest.TestCase):
    def test_materializes_bridge_zone_reports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            reports_dir = tmp_path / "reports"

            connection = sqlite3.connect(db_path)
            seed_fixture(connection)
            connection.close()

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--reports-dir",
                    str(reports_dir),
                    "--top-k",
                    "10",
                ],
                check=True,
                cwd=ROOT,
            )

            rows = [
                json.loads(line)
                for line in (reports_dir / "ds2-bridge-zones.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(row["top_papers"] for row in rows))
            self.assertTrue(all(len(row["candidate_translation_questions"]) == 3 for row in rows))
            zone_ids = {row["zone_id"] for row in rows}
            self.assertIn("settlement_parity_repair", zone_ids)
            self.assertIn("defi_immature_repair", zone_ids)

            report = (reports_dir / "ds2-bridge-zones-report.md").read_text(encoding="utf-8")
            self.assertIn("# DS2 Bridge-Zone Mining", report)
            self.assertIn("## Candidate-Family Diversity", report)
            self.assertIn("Auction / Pari-Mutuel x Refill / Shock-Recovery", report)
            self.assertIn("DeFi / Bridge / Liquidation x Immature-Market Repair", report)


if __name__ == "__main__":
    unittest.main()
