import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_shortlist.py"


def seed_shortlist_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    review_packets = [
        ("packets-run", "cluster", "cluster-a", "Cluster A", {"avg_stranding": 0.95}),
        ("packets-run", "cluster", "cluster-b", "Cluster B", {"avg_stranding": 0.90}),
        ("packets-run", "bridge", "bridge-a", "Bridge A", {"max_score": 0.45}),
        ("packets-run", "composition", "composition-a", "Composition A", {"max_score": 0.40}),
        ("packets-run", "stranded_qfin", "paper-a", "Paper A", {"stranding_score": 0.30}),
    ]
    connection.executemany(
        """
        INSERT INTO review_packets (
          run_id, packet_kind, item_ref, title, packet_path, summary_json, packet_markdown, source_run_ids_json
        )
        VALUES (?, ?, ?, ?, ?, ?, '# packet', '{}')
        """,
        [
            (run_id, packet_kind, item_ref, title, f"/tmp/{item_ref}.md", json.dumps(summary, sort_keys=True))
            for run_id, packet_kind, item_ref, title, summary in review_packets
        ],
    )
    connection.commit()


class MaterializeShortlistTest(unittest.TestCase):
    def test_materializes_shortlist_with_rationale_and_bridge_composition_share(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"
            rules_path = tmp_path / "rules.yaml"

            connection = sqlite3.connect(db_path)
            seed_shortlist_fixture(connection)
            connection.close()

            rules_path.write_text(
                "shortlist_size: 4\nminimum_bridge_or_composition_share: 0.5\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "shortlist-run",
                    "--packet-run-id",
                    "packets-run",
                    "--rules-path",
                    str(rules_path),
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            connection = sqlite3.connect(db_path)
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT shortlist_id, item_type, item_ref, packet_kind, score, shortlist_rank, status, rationale_json
                FROM shortlist_items
                WHERE run_id = 'shortlist-run'
                ORDER BY shortlist_rank
                """
            ).fetchall()
            self.assertEqual(len(rows), 4)
            self.assertEqual([row["shortlist_rank"] for row in rows], [1, 2, 3, 4])

            bridge_comp = [row for row in rows if row["packet_kind"] in {"bridge", "composition"}]
            self.assertEqual(len(bridge_comp), 2)

            first_rationale = json.loads(rows[0]["rationale_json"])
            self.assertIn("selection_reason", first_rationale)
            self.assertIn("summary", first_rationale)
            self.assertEqual(rows[0]["status"], "proposed")

            metrics = json.loads((output_dir / "shortlist_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["shortlist_count"], 4)
            self.assertEqual(metrics["bridge_or_composition_count"], 2)
            self.assertEqual(metrics["counts_by_item_type"]["bridge"], 1)
            self.assertEqual(metrics["counts_by_item_type"]["composition"], 1)

            shortlist_lines = (output_dir / "shortlist.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(shortlist_lines), 4)
            parsed_first = json.loads(shortlist_lines[0])
            self.assertIn("rationale", parsed_first)

            connection.close()


if __name__ == "__main__":
    unittest.main()
