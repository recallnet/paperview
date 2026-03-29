import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_ds3_early_market_ledger.py"


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO anchors (anchor_id, label, anchor_type, tags_json) VALUES
          ('market_design_seams', 'Market-design seams', 'positive', '[]'),
          ('participant_pathologies', 'Participant pathologies', 'positive', '[]'),
          ('amm_settlement_latency', 'AMM / settlement latency', 'positive', '[]'),
          ('settlement_resolution_seams', 'Settlement / resolution seams', 'positive', '[]'),
          ('state_graph_inconsistencies', 'State-graph inconsistencies', 'positive', '[]'),
          ('parity_propagation_delayed_repair', 'Parity propagation / delayed repair', 'positive', '[]'),
          ('lifecycle_professionalization', 'Lifecycle / professionalization', 'positive', '[]'),
          ('queue_value_passive_quoting', 'Queue value / passive quoting', 'positive', '[]');

        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at) VALUES
          ('p-market', 'arxiv', 'Venue rule changes and refill asymmetry', 'q-fin.TR', '2021-01-01'),
          ('p-settlement', 'arxiv', 'Settlement timing and arbitrage repair', 'econ.GN', '2021-01-02'),
          ('p-participant', 'arxiv', 'Latency and manipulation around thin books', 'q-fin.TR', '2021-01-03'),
          ('p-state', 'arxiv', 'Cross-market parity disagreement under fragmented rules', 'q-fin.PR', '2021-01-04'),
          ('p-life', 'arxiv', 'Adoption and professionalization in decentralized exchanges', 'q-fin.TR', '2021-01-05'),
          ('p-stranded', 'arxiv', 'Execution control under illiquidity', 'q-fin.MF', '2021-01-06'),
          ('p-transition', 'arxiv', 'Auction refill asymmetry', 'q-fin.ST', '2021-01-07');

        INSERT INTO agitator_patterns (pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active) VALUES
          ('near_transition_auction_refill', 'near auction handoff and refill resiliency', 'composition', '', '[]', '[]', 1);

        INSERT INTO composition_candidates (run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json) VALUES
          ('composition-run', 'market_design_seams', 'queue_value_passive_quoting', 'p-market', 3.10, 1, '{}'),
          ('composition-run', 'amm_settlement_latency', 'settlement_resolution_seams', 'p-settlement', 3.20, 1, '{}'),
          ('composition-run', 'market_design_seams', 'participant_pathologies', 'p-participant', 3.15, 1, '{}'),
          ('composition-run', 'settlement_resolution_seams', 'state_graph_inconsistencies', 'p-state', 3.05, 1, '{}'),
          ('composition-run', 'lifecycle_professionalization', 'market_design_seams', 'p-life', 3.25, 1, '{}');

        INSERT INTO stranded_resurfacing_candidates (run_id, paper_id, resurfacing_score, resurfacing_rank, membership_run_id, stranding_run_id, transition_score_run_id, rationale_json) VALUES
          ('stranded-run', 'p-stranded', 0.41, 1, 'm', 's', 't', '{}');

        INSERT INTO transition_state_candidates (run_id, pattern_id, paper_id, transition_state_candidate_score, transition_state_rank, rationale_json) VALUES
          ('transition-run', 'near_transition_auction_refill', 'p-transition', 0.67, 1, '{}');

        INSERT INTO enhanced_interpretations (
          run_id, batch_run_id, batch_item_id, operator_family, source_kind, source_run_id, source_ref,
          family_rank, source_score, packet_title, classification, result_summary, first_step,
          instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close, confidence, raw_json
        ) VALUES
          (
            'enhanced-run', 'batch', 'settlement_resolution:composition:amm_settlement_latency__settlement_resolution_seams',
            'settlement_resolution', 'composition_candidate_pair', 'composition-run', 'amm_settlement_latency__settlement_resolution_seams',
            1, 3.2, 'Settlement packet', 'TRANSLATION_CANDIDATE', 'Settlement seam',
            'Test settlement-cycle timing against convergence windows.',
            'fragmented market', 'settlement-lag arbitrage', 'The literature frames this as architecture rather than a trade seam.',
            'Need synchronized settlement timestamps.', 'medium', '{}'
          ),
          (
            'enhanced-run', 'batch', 'stranded_qfin:p-stranded',
            'stranded_qfin', 'stranded_resurfacing_candidate', 'stranded-run', 'p-stranded',
            1, 0.41, 'Stranded packet', 'STRANDED_QFIN_RESULT', 'Stranded result',
            'Replay the control on modern intraday data.',
            'illiquid market', 'impact-aware execution control', 'It stayed buried in math-finance language.',
            'Need modern queue evidence.', 'medium', '{}'
          );
        """
    )
    connection.commit()


class MaterializeDs3EarlyMarketLedgerTests(unittest.TestCase):
    def test_materializes_early_market_ledger(self):
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
                    "--composition-run-id",
                    "composition-run",
                    "--transition-run-id",
                    "transition-run",
                    "--stranded-run-id",
                    "stranded-run",
                    "--enhanced-interpretation-run-id",
                    "enhanced-run",
                    "--top-k",
                    "6",
                ],
                check=True,
                cwd=ROOT,
            )

            rows = [
                json.loads(line)
                for line in (reports_dir / "ds3-early-market-ledger.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual(len(rows), 6)
            self.assertTrue(all("failure_mode" in row for row in rows))
            self.assertTrue(all("what_closes_it" in row for row in rows))
            self.assertTrue(all("likely_market_stage" in row for row in rows))
            self.assertGreaterEqual(sum(1 for row in rows if row["lane_family"] != "transition_state"), 5)
            settlement_row = next(row for row in rows if row["paper_id"] == "p-settlement")
            self.assertEqual(settlement_row["first_test"], "Test settlement-cycle timing against convergence windows.")

            report = (reports_dir / "ds3-early-market-ledger.md").read_text(encoding="utf-8")
            self.assertIn("# DS3 Early-Market Failure Mode Ledger", report)
            self.assertIn("## Candidate-Family Diversity", report)
            self.assertIn("non-transition-state entries", report)


if __name__ == "__main__":
    unittest.main()
