import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from array import array
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_holdout_echoes.py"


def write_embedding_metrics(path: Path, vec_db_path: Path) -> None:
    payload = {
        "vec_db_path": str(vec_db_path),
        "spaces": [
            {
                "name": "s1_title_abs_main",
                "dims": 2,
                "view_type": "title_abs",
                "table_name": "vec_s1_title_abs_main_2",
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def seed_holdout_echo_fixture(canonical_connection: sqlite3.Connection, vec_connection: sqlite3.Connection) -> None:
    canonical_connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    canonical_connection.executemany(
        """
        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at)
        VALUES (?, 'arxiv', ?, 'q-fin.TR', ?)
        """,
        [
            ("source-paper", "Source Paper", "2023-01-01"),
            ("holdout-near", "Holdout Near", "2024-01-15"),
            ("holdout-far", "Holdout Far", "2024-01-16"),
        ],
    )
    canonical_connection.executemany(
        """
        INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256)
        VALUES (?, ?, 'title_abs', ?, 1, ?)
        """,
        [
            (1, "source-paper", "source", "sha-source"),
            (2, "holdout-near", "near", "sha-near"),
            (3, "holdout-far", "far", "sha-far"),
        ],
    )
    canonical_connection.executemany(
        """
        INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source, rationale_json)
        VALUES ('membership-run', ?, 'holdout', 'fixture', '{}')
        """,
        [("holdout-near",), ("holdout-far",)],
    )
    canonical_connection.execute(
        """
        INSERT INTO review_packets (
          run_id, packet_kind, item_ref, title, packet_path, summary_json, packet_markdown, source_run_ids_json
        )
        VALUES (
          'packet-run',
          'composition',
          'composition-a',
          'Composition Packet',
          '/tmp/composition-a.md',
          '{"representative_papers":["source-paper"]}',
          '# packet',
          '{}'
        )
        """
    )
    canonical_connection.execute(
        """
        INSERT INTO shortlist_items (
          run_id, shortlist_id, item_type, item_ref, packet_run_id, packet_kind, packet_item_ref,
          score, shortlist_rank, status, rationale_json
        )
        VALUES (
          'shortlist-run',
          'composition:composition-a',
          'composition',
          'composition-a',
          'packet-run',
          'composition',
          'composition-a',
          1.0,
          1,
          'proposed',
          '{}'
        )
        """
    )
    canonical_connection.execute(
        """
        INSERT INTO selective_interpretations (
          run_id, shortlist_run_id, shortlist_id, classification, result_summary, first_step,
          instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close,
          confidence, raw_json
        )
        VALUES (
          'interpret-run',
          'shortlist-run',
          'composition:composition-a',
          'COMPOSITIONAL_CANDIDATE',
          'summary',
          'step',
          'instrument',
          'modern',
          'why',
          'gap',
          'medium',
          '{}'
        )
        """
    )

    vec_connection.execute("CREATE TABLE vec_s1_title_abs_main_2 (rowid INTEGER PRIMARY KEY, embedding BLOB NOT NULL)")
    vectors = {
        1: array("f", [1.0, 0.0]),
        2: array("f", [0.95, 0.05]),
        3: array("f", [0.0, 1.0]),
    }
    for rowid, vector in vectors.items():
        vec_connection.execute(
            "INSERT INTO vec_s1_title_abs_main_2 (rowid, embedding) VALUES (?, ?)",
            (rowid, vector.tobytes()),
        )

    canonical_connection.commit()
    vec_connection.commit()


class MaterializeHoldoutEchoesTest(unittest.TestCase):
    def test_materializes_nearest_holdout_echoes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            vec_db_path = tmp_path / "vec.sqlite3"
            metrics_path = tmp_path / "embedding_metrics.json"
            output_dir = tmp_path / "run"

            canonical_connection = sqlite3.connect(db_path)
            vec_connection = sqlite3.connect(vec_db_path)
            seed_holdout_echo_fixture(canonical_connection, vec_connection)
            canonical_connection.close()
            vec_connection.close()
            write_embedding_metrics(metrics_path, vec_db_path)

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "echo-run",
                    "--interpretation-run-id",
                    "interpret-run",
                    "--membership-run-id",
                    "membership-run",
                    "--embedding-metrics-path",
                    str(metrics_path),
                    "--output-dir",
                    str(output_dir),
                    "--top-k",
                    "2",
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "holdout_echo_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["echo_count"], 2)
            self.assertEqual(metrics["interpreted_shortlist_count"], 1)
            self.assertEqual(metrics["shortlists_with_echoes"], 1)

            rows = [json.loads(line) for line in (output_dir / "holdout_echoes.jsonl").read_text(encoding="utf-8").strip().splitlines()]
            self.assertEqual(rows[0]["holdout_paper_id"], "holdout-near")
            self.assertEqual(rows[0]["echo_rank"], 1)
            self.assertEqual(rows[1]["holdout_paper_id"], "holdout-far")


if __name__ == "__main__":
    unittest.main()
