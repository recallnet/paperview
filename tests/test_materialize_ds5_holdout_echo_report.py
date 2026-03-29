import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from array import array
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_ds5_holdout_echo_report.py"


def vector_blob(values):
    arr = array("f", values)
    return arr.tobytes()


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at) VALUES
          ('cand-a', 'arxiv', 'Async settlement arbitrage candidate', 'cs.GT', '2020-01-01'),
          ('cand-b', 'arxiv', 'Early market professionalization candidate', 'q-fin.TR', '2012-01-01'),
          ('cand-c', 'arxiv', 'Execution control candidate', 'q-fin.MF', '2021-01-01'),
          ('hold-a', 'arxiv', '2024 settlement repair echo', 'q-fin.CP', '2024-04-01'),
          ('hold-b', 'arxiv', '2025 professionalization echo', 'econ.GN', '2025-01-01'),
          ('hold-c', 'arxiv', '2024 unrelated paper', 'math.PR', '2024-06-01');

        INSERT INTO text_views (paper_id, view_type, text, token_estimate, text_sha256) VALUES
          ('cand-a', 'title_abs', 'candidate a', 2, 'a'),
          ('cand-b', 'title_abs', 'candidate b', 2, 'b'),
          ('cand-c', 'title_abs', 'candidate c', 2, 'c'),
          ('hold-a', 'title_abs', 'holdout a', 2, 'd'),
          ('hold-b', 'title_abs', 'holdout b', 2, 'e'),
          ('hold-c', 'title_abs', 'holdout c', 2, 'f');

        INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source, rationale_json) VALUES
          ('membership-run', 'hold-a', 'holdout', 'fixture', '{}'),
          ('membership-run', 'hold-b', 'holdout', 'fixture', '{}'),
          ('membership-run', 'hold-c', 'holdout', 'fixture', '{}');
        """
    )
    connection.commit()


class MaterializeDs5HoldoutEchoReportTests(unittest.TestCase):
    def test_materializes_holdout_echo_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            reports_dir = tmp_path / "reports"
            vec_db_path = tmp_path / "vec.sqlite3"
            metrics_path = tmp_path / "embedding_metrics.json"

            connection = sqlite3.connect(db_path)
            seed_fixture(connection)
            connection.close()

            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / "ds1-translation-gap-candidates.jsonl").write_text(
                json.dumps({"paper_id": "cand-a", "challenge_capsule_matched": "settlement_async_repair", "why_far_from_realized": "far", "rank": 1}) + "\n",
                encoding="utf-8",
            )
            (reports_dir / "ds3-early-market-ledger.jsonl").write_text(
                json.dumps({"paper_id": "cand-b", "lane_family": "lifecycle", "failure_mode": "Professionalization lag", "rank": 1}) + "\n",
                encoding="utf-8",
            )
            (reports_dir / "ds4-stranded-ledger.jsonl").write_text(
                json.dumps({"paper_id": "cand-c", "rescue_family": "execution_control", "modern_equivalent_now": "adaptive execution", "rescue_rank": 1}) + "\n",
                encoding="utf-8",
            )

            vec_connection = sqlite3.connect(vec_db_path)
            vec_connection.execute("CREATE TABLE vec_s1_title_abs_main_384 (rowid INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
            embeddings = {
                1: [1.0, 0.0, 0.0],
                2: [0.0, 1.0, 0.0],
                3: [0.7, 0.7, 0.0],
                4: [0.96, 0.04, 0.0],
                5: [0.03, 0.97, 0.0],
                6: [0.0, 0.0, 1.0],
            }
            for rowid, vector in embeddings.items():
                vec_connection.execute(
                    "INSERT INTO vec_s1_title_abs_main_384 (rowid, embedding) VALUES (?, ?)",
                    (rowid, vector_blob(vector)),
                )
            vec_connection.commit()
            vec_connection.close()

            metrics_path.write_text(
                json.dumps(
                    {
                        "vec_db_path": str(vec_db_path),
                        "spaces": [
                            {
                                "name": "s1_title_abs_main",
                                "view_type": "title_abs",
                                "dims": 384,
                                "table_name": "vec_s1_title_abs_main_384",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--reports-dir",
                    str(reports_dir),
                    "--embedding-metrics-path",
                    str(metrics_path),
                    "--vec-db-path",
                    str(vec_db_path),
                    "--membership-run-id",
                    "membership-run",
                    "--top-k-candidates",
                    "5",
                    "--top-k-echoes",
                    "2",
                ],
                check=True,
                cwd=ROOT,
            )

            rows = [
                json.loads(line)
                for line in (reports_dir / "ds5-holdout-echo-report.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["echo_verdict"], "validation")
            self.assertTrue(all("top_holdout_echoes" in row for row in rows))
            self.assertTrue(all(len(row["top_holdout_echoes"]) == 2 for row in rows))

            report = (reports_dir / "ds5-holdout-echo-report.md").read_text(encoding="utf-8")
            self.assertIn("# DS5 Holdout Echo Report", report)
            self.assertIn("## Candidate-Family Diversity", report)
            self.assertIn("## Verdict Mix", report)


if __name__ == "__main__":
    unittest.main()
