import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "materialize_transition_state_ledger.py"


class MaterializeTransitionStateLedgerTests(unittest.TestCase):
    def test_materializes_ledger_from_transition_candidates_and_interpretations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical_db = tmp / "paperview.sqlite3"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "init_local_store.py"), "--db-path", str(canonical_db)],
                check=True,
                cwd=ROOT,
            )
            conn = sqlite3.connect(str(canonical_db))
            conn.executescript(
                """
                INSERT INTO agitator_patterns (
                  pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active
                ) VALUES
                  ('near_transition_queue_refill', 'Queue x Refill', 'transition', 'queue refill', '[]', '[]', 1),
                  ('near_transition_auction_refill', 'Auction x Refill', 'transition', 'auction refill', '[]', '[]', 1),
                  ('near_transition_maker_queue', 'Maker x Queue', 'transition', 'maker queue', '[]', '[]', 1);

                INSERT INTO papers (paper_id, source_corpus, title, abstract, primary_category, published_at) VALUES
                  ('queue-paper', 'arxiv', 'Queue Paper', '', 'q-fin.TR', '2021-01-01'),
                  ('auction-paper', 'arxiv', 'Auction Paper', '', 'q-fin.MF', '2020-01-01'),
                  ('maker-paper', 'arxiv', 'Maker Paper', '', 'q-fin.TR', '2019-01-01');

                INSERT INTO shortlist_items (
                  run_id, shortlist_id, item_type, item_ref, packet_run_id, packet_kind, packet_item_ref,
                  score, shortlist_rank, status, rationale_json
                ) VALUES
                  ('shortlist-run', 'composition:queue_value_passive_quoting__refill_lag_local_shock', 'composition', 'queue_value_passive_quoting__refill_lag_local_shock', 'packet-run', 'composition', 'queue_value_passive_quoting__refill_lag_local_shock', 2.0, 1, 'proposed', '{}'),
                  ('shortlist-run', 'bridge:auction_parimutuel_design__refill_lag_local_shock', 'bridge', 'auction_parimutuel_design__refill_lag_local_shock', 'packet-run', 'bridge', 'auction_parimutuel_design__refill_lag_local_shock', 1.8, 2, 'proposed', '{}'),
                  ('shortlist-run', 'bridge:maker_stress_inventory_retreat__queue_value_passive_quoting', 'bridge', 'maker_stress_inventory_retreat__queue_value_passive_quoting', 'packet-run', 'bridge', 'maker_stress_inventory_retreat__queue_value_passive_quoting', 1.5, 3, 'proposed', '{}');

                INSERT INTO selective_interpretations (
                  run_id, shortlist_run_id, shortlist_id, classification, result_summary, first_step,
                  instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close,
                  confidence, raw_json
                ) VALUES
                  ('interpret-run', 'shortlist-run', 'composition:queue_value_passive_quoting__refill_lag_local_shock', 'COMPOSITIONAL_CANDIDATE', 'queue result', 'queue step', 'queue instrument', 'queue clue', 'queue why', 'queue gap', 'medium', '{}'),
                  ('interpret-run', 'shortlist-run', 'bridge:auction_parimutuel_design__refill_lag_local_shock', 'TRANSLATION_CANDIDATE', 'auction result', 'auction step', 'auction instrument', 'auction clue', 'auction why', 'auction gap', 'high', '{}'),
                  ('interpret-run', 'shortlist-run', 'bridge:maker_stress_inventory_retreat__queue_value_passive_quoting', 'NO_TRANSLATION', 'maker result', 'maker step', 'maker instrument', 'maker clue', 'maker why', 'maker gap', 'medium', '{}');

                INSERT INTO transition_state_candidates (
                  run_id, pattern_id, paper_id, transition_state_candidate_score, transition_state_rank, rationale_json
                ) VALUES
                  ('candidate-run', 'near_transition_queue_refill', 'queue-paper', 0.72, 1, '{}'),
                  ('candidate-run', 'near_transition_auction_refill', 'auction-paper', 0.68, 1, '{}'),
                  ('candidate-run', 'near_transition_maker_queue', 'maker-paper', 0.47, 1, '{}');
                """
            )
            conn.commit()
            conn.close()

            output_dir = tmp / "transition-ledger-run"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "ledger-run",
                    "--candidate-run-id",
                    "candidate-run",
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--interpretation-run-id",
                    "interpret-run",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            conn = sqlite3.connect(str(canonical_db))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT pattern_id, shortlist_id, paper_id, ledger_rank, transition_state_score, relation_type
                    FROM transition_state_ledger
                    WHERE run_id='ledger-run'
                    ORDER BY ledger_rank, pattern_id
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual([row["pattern_id"] for row in rows], ["near_transition_queue_refill", "near_transition_auction_refill"])
            self.assertEqual(rows[0]["shortlist_id"], "composition:queue_value_passive_quoting__refill_lag_local_shock")
            self.assertEqual(rows[1]["shortlist_id"], "bridge:auction_parimutuel_design__refill_lag_local_shock")
            self.assertEqual(rows[0]["relation_type"], "calibration")
            self.assertEqual(rows[1]["relation_type"], "adaptation")

            metrics = json.loads((output_dir / "transition_state_ledger_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["entry_count"], 2)
            self.assertEqual(metrics["top_ranked_pattern_id"], "near_transition_queue_refill")

            markdown = (output_dir / "transition_state_ledger.md").read_text(encoding="utf-8")
            self.assertIn("# Transition-State Microstructure Ledger", markdown)
            self.assertIn("Queue x Refill", markdown)
            self.assertNotIn("Maker x Queue", markdown)


if __name__ == "__main__":
    unittest.main()
