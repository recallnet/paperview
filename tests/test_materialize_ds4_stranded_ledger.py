import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_ds4_stranded_ledger.py"


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at) VALUES
          ('p-exec', 'arxiv', 'On Parametric Optimal Execution and Machine Learning Surrogates', 'q-fin.TR', '2022-04-18'),
          ('p-port', 'arxiv', 'Active and Passive Portfolio Management with Latent Factors', 'q-fin.PM', '2019-03-18'),
          ('p-contagion', 'arxiv', 'Price mediated contagion through capital ratio requirements with VWAP liquidation prices', 'q-fin.MF', '2019-10-28'),
          ('p-deriv', 'arxiv', 'Pricing Path-Dependent Derivatives under Multiscale Stochastic Volatility Models', 'q-fin.CP', '2020-05-09'),
          ('p-rate', 'arxiv', 'Affine multiple yield curve models', 'q-fin.MF', '2016-03-02');

        INSERT INTO stranded_resurfacing_candidates (run_id, paper_id, resurfacing_score, resurfacing_rank, membership_run_id, stranding_run_id, transition_score_run_id, rationale_json) VALUES
          ('stranded-run', 'p-exec', 0.41, 1, 'm', 's', 't', '{}'),
          ('stranded-run', 'p-port', 0.38, 2, 'm', 's', 't', '{}'),
          ('stranded-run', 'p-contagion', 0.36, 3, 'm', 's', 't', '{}'),
          ('stranded-run', 'p-deriv', 0.35, 4, 'm', 's', 't', '{}'),
          ('stranded-run', 'p-rate', 0.34, 5, 'm', 's', 't', '{}');

        INSERT INTO enhanced_interpretations (
          run_id, batch_run_id, batch_item_id, operator_family, source_kind, source_run_id, source_ref,
          family_rank, source_score, packet_title, classification, result_summary, first_step,
          instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close, confidence, raw_json
        ) VALUES
          (
            'enhanced-run', 'batch', 'stranded_qfin:p-exec',
            'stranded_qfin', 'stranded_resurfacing_candidate', 'stranded-run', 'p-exec',
            1, 0.41, 'Execution packet', 'STRANDED_QFIN_RESULT',
            'Machine-learning surrogates can speed the search for near-optimal execution schedules under parametric impact models.',
            'Replicate the surrogate-assisted execution policy on newer fragmented limit-order-book data with realistic fees.',
            'algorithmic execution in liquid futures or equities',
            'execution policy search with fast surrogates',
            'The result is practical but remained stranded inside execution-model calibration language instead of being promoted as a deployable trading workflow.',
            'Need to show that the surrogate remains stable under venue fragmentation and regime shifts.',
            'high',
            '{}'
          );
        """
    )
    connection.commit()


class MaterializeDs4StrandedLedgerTests(unittest.TestCase):
    def test_materializes_forced_translation_ledger(self):
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
                    "--stranded-run-id",
                    "stranded-run",
                    "--enhanced-interpretation-run-id",
                    "enhanced-run",
                    "--top-k",
                    "5",
                ],
                check=True,
                cwd=ROOT,
            )

            rows = [
                json.loads(line)
                for line in (reports_dir / "ds4-stranded-ledger.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual(len(rows), 5)
            self.assertTrue(all("result_plain" in row for row in rows))
            self.assertTrue(all("modern_equivalent_now" in row for row in rows))
            self.assertTrue(all("first_implementation_test" in row for row in rows))
            self.assertTrue(any(row["paper_id"] == "p-exec" and row["executable_research_task"] for row in rows))
            self.assertGreaterEqual(sum(1 for row in rows if row["executable_research_task"]), 3)

            report = (reports_dir / "ds4-stranded-ledger.md").read_text(encoding="utf-8")
            self.assertIn("# DS4 Stranded Result Ledger", report)
            self.assertIn("## Rescue-Family Diversity", report)
            self.assertIn("Why not just theory:", report)


if __name__ == "__main__":
    unittest.main()
