import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_stranded_result_ledger.py"


def seed_stranded_ledger_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    connection.executemany(
        """
        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at)
        VALUES (?, 'arxiv', ?, ?, ?)
        """,
        [
            ("paper-a", "Paper A", "q-fin.PR", "2020-01-01"),
            ("paper-b", "Paper B", "q-fin.TR", "2021-01-01"),
        ],
    )

    connection.executemany(
        """
        INSERT INTO shortlist_items (
          run_id, shortlist_id, item_type, item_ref, packet_run_id, packet_kind, packet_item_ref,
          score, shortlist_rank, status, rationale_json
        )
        VALUES (?, ?, 'paper', ?, 'packet-run', 'stranded_qfin', ?, ?, ?, 'proposed', '{}')
        """,
        [
            ("shortlist-run", "paper:paper-a", "paper-a", "paper-a", 1.0, 1),
            ("shortlist-run", "paper:paper-b", "paper-b", "paper-b", 0.8, 2),
        ],
    )

    connection.executemany(
        """
        INSERT INTO selective_interpretations (
          run_id, shortlist_run_id, shortlist_id, classification, result_summary, first_step,
          instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close,
          confidence, raw_json
        )
        VALUES (?, 'shortlist-run', ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}')
        """,
        [
            (
                "interpret-run",
                "paper:paper-a",
                "STRANDED_QFIN_RESULT",
                "result-a",
                "test-a",
                "instrument-a",
                "modern-a",
                "why-a",
                "gap-a",
                "high",
            ),
            (
                "interpret-run",
                "paper:paper-b",
                "TRANSLATION_CANDIDATE",
                "result-b",
                "test-b",
                "instrument-b",
                "modern-b",
                "why-b",
                "gap-b",
                "medium",
            ),
        ],
    )

    connection.executemany(
        """
        INSERT INTO stranding_scores (
          run_id, paper_id, membership_run_id, score_version, stranding_score,
          instrument_gap_score, access_barrier_score, implementation_barrier_score,
          result_specificity_score, resolution_mechanics_score, survey_penalty_score,
          empirical_only_penalty_score, stranded_alpha_bonus, feature_json
        )
        VALUES (?, ?, 'membership-run', 'v1', ?, 0, 0, 0, 0, 0, 0, 0, 0, '{}')
        """,
        [
            ("stranding-run", "paper-a", 0.32),
            ("stranding-run", "paper-b", 0.28),
        ],
    )

    connection.commit()


class MaterializeStrandedResultLedgerTest(unittest.TestCase):
    def test_materializes_only_stranded_qfin_results(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"

            connection = sqlite3.connect(db_path)
            seed_stranded_ledger_fixture(connection)
            connection.close()

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "ledger-run",
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--interpretation-run-id",
                    "interpret-run",
                    "--stranding-run-id",
                    "stranding-run",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "stranded_result_ledger_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["entry_count"], 1)
            self.assertEqual(metrics["top_ranked_paper_id"], "paper-a")

            rows = [
                json.loads(line)
                for line in (output_dir / "stranded_result_ledger.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["paper_id"], "paper-a")
            self.assertEqual(rows[0]["priority_tier"], "p1")
            self.assertEqual(rows[0]["relation_type"], "direct")
            self.assertEqual(rows[0]["first_test"], "test-a")

            markdown = (output_dir / "stranded_result_ledger.md").read_text(encoding="utf-8")
            self.assertIn("# Stranded Result Ledger", markdown)
            self.assertIn("paper-a", markdown)
            self.assertNotIn("paper-b", markdown)


if __name__ == "__main__":
    unittest.main()
