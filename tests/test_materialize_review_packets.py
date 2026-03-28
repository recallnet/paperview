import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_review_packets.py"


def seed_packet_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    connection.executemany(
        """
        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at)
        VALUES (?, 'arxiv', ?, ?, ?)
        """,
        [
            ("p_cluster_a", "Queue Shock Dynamics", "q-fin.TR", "2020-01-01"),
            ("p_cluster_b", "Auction Spillover Design", "cs.GT", "2021-01-01"),
            ("p_bridge", "Bridge Market Maker", "q-fin.TR", "2020-02-01"),
            ("p_comp", "Composed Settlement Design", "cs.GT", "2021-02-01"),
            ("p_stranded", "Incomplete Market Friction", "q-fin.PR", "2019-05-01"),
        ],
    )

    connection.execute(
        """
        INSERT INTO clusters (run_id, cluster_id, level, algorithm, size, label, summary)
        VALUES ('cluster-run', 'cluster-mid-1', 'mid', 'louvain', 2, 'Queue / Auction', 'mixed cluster')
        """
    )
    connection.executemany(
        """
        INSERT INTO cluster_members (run_id, cluster_id, paper_id)
        VALUES ('cluster-run', 'cluster-mid-1', ?)
        """,
        [("p_cluster_a",), ("p_cluster_b",)],
    )

    connection.executemany(
        """
        INSERT INTO anchors (anchor_id, label, anchor_type, tags_json)
        VALUES (?, ?, 'positive', '[]')
        """,
        [
            ("queue_anchor", "Queue",),
            ("auction_anchor", "Auction",),
            ("settlement_anchor", "Settlement",),
        ],
    )

    connection.execute(
        """
        INSERT INTO bridge_candidates (
          run_id, source_anchor_id, target_anchor_id, paper_id, bridge_score, bridge_rank, rationale_json
        )
        VALUES ('bridge-run', 'queue_anchor', 'auction_anchor', 'p_bridge', 2.5, 1, '{}')
        """
    )
    connection.execute(
        """
        INSERT INTO composition_candidates (
          run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json
        )
        VALUES ('composition-run', 'queue_anchor', 'settlement_anchor', 'p_comp', 3.25, 1, '{}')
        """
    )

    connection.executemany(
        """
        INSERT INTO stranding_scores (
          run_id, paper_id, membership_run_id, score_version, stranding_score,
          instrument_gap_score, access_barrier_score, implementation_barrier_score,
          result_specificity_score, resolution_mechanics_score,
          survey_penalty_score, empirical_only_penalty_score, stranded_alpha_bonus, feature_json
        )
        VALUES (?, ?, 'membership-run', 'v1', ?, 0.2, 0.1, 0.0, 0.3, 0.1, 0.0, 0.0, 0.0, '{}')
        """,
        [
            ("stranding-run", "p_cluster_a", 0.22),
            ("stranding-run", "p_cluster_b", 0.18),
            ("stranding-run", "p_stranded", 0.41),
        ],
    )
    connection.execute(
        """
        INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source, rationale_json)
        VALUES ('membership-run', 'p_stranded', 'stranded_alpha', 'fixture', '{}')
        """
    )

    connection.commit()


class MaterializeReviewPacketsTest(unittest.TestCase):
    def test_materializes_all_packet_kinds_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"

            connection = sqlite3.connect(db_path)
            seed_packet_fixture(connection)
            connection.close()

            base_cmd = [
                sys.executable,
                str(SCRIPT_PATH),
                "--db-path",
                str(db_path),
                "--run-id",
                "review-run",
                "--cluster-run-id",
                "cluster-run",
                "--bridge-run-id",
                "bridge-run",
                "--composition-run-id",
                "composition-run",
                "--stranding-run-id",
                "stranding-run",
                "--membership-run-id",
                "membership-run",
                "--output-dir",
                str(output_dir),
                "--top-clusters",
                "1",
                "--top-bridges",
                "1",
                "--top-compositions",
                "1",
                "--top-stranded",
                "1",
            ]

            subprocess.run(base_cmd, check=True, cwd=ROOT)
            subprocess.run(base_cmd, check=True, cwd=ROOT)

            connection = sqlite3.connect(db_path)
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT packet_kind, item_ref, title, packet_path, summary_json, packet_markdown
                FROM review_packets
                WHERE run_id = 'review-run'
                ORDER BY packet_kind, item_ref
                """
            ).fetchall()
            self.assertEqual(len(rows), 4)
            self.assertEqual([row["packet_kind"] for row in rows], ["bridge", "cluster", "composition", "stranded_qfin"])

            metrics = json.loads((output_dir / "review_packet_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["packet_counts"], {"bridge": 1, "cluster": 1, "composition": 1, "stranded_qfin": 1})
            self.assertEqual(metrics["total_packets"], 4)

            for row in rows:
                packet_path = Path(row["packet_path"])
                self.assertTrue(packet_path.exists())
                self.assertIn("#", row["packet_markdown"])
                self.assertTrue(json.loads(row["summary_json"]))

            cluster_markdown = rows[1]["packet_markdown"]
            self.assertIn("Queue Shock Dynamics", cluster_markdown)
            self.assertIn("Auction Spillover Design", cluster_markdown)

            stranded_markdown = rows[3]["packet_markdown"]
            self.assertIn("Incomplete Market Friction", stranded_markdown)

            connection.close()


if __name__ == "__main__":
    unittest.main()
