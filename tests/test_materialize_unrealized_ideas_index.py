import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_unrealized_ideas_index.py"


def seed_unrealized_index_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    connection.executemany(
        """
        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at)
        VALUES (?, 'arxiv', ?, 'q-fin.TR', ?)
        """,
        [
            ("source-bridge", "Source Bridge", "2023-01-01"),
            ("source-market-design", "Source Market Design", "2023-01-03"),
            ("source-paper", "Source Paper", "2023-01-02"),
            ("holdout-a", "Holdout A", "2024-01-15"),
            ("holdout-b", "Holdout B", "2024-01-16"),
            ("holdout-c", "Holdout C", "2024-01-17"),
        ],
    )

    connection.executemany(
        """
        INSERT INTO review_packets (
          run_id, packet_kind, item_ref, title, packet_path, summary_json, packet_markdown, source_run_ids_json
        )
        VALUES (?, ?, ?, ?, ?, ?, '# packet', '{}')
        """,
        [
            (
                "packet-run",
                "bridge",
                "bridge-a",
                "Bridge Packet",
                "/tmp/bridge-a.md",
                '{"representative_papers":["source-bridge"]}',
            ),
            (
                "packet-run",
                "stranded_qfin",
                "source-paper",
                "Stranded Packet",
                "/tmp/source-paper.md",
                '{"paper_id":"source-paper"}',
            ),
            (
                "packet-run",
                "bridge",
                "composition-a",
                "Composition Pair As Bridge",
                "/tmp/bridge-composition-a.md",
                '{"representative_papers":["source-bridge"]}',
            ),
            (
                "packet-run",
                "bridge",
                "bridge-b",
                "Bridge Without Validation",
                "/tmp/bridge-b.md",
                '{"representative_papers":["source-bridge"]}',
            ),
            (
                "packet-run",
                "composition",
                "composition-a",
                "Composition Packet",
                "/tmp/composition-a.md",
                '{"representative_papers":["source-bridge"]}',
            ),
        ],
    )

    connection.executemany(
        """
        INSERT INTO shortlist_items (
          run_id, shortlist_id, item_type, item_ref, packet_run_id, packet_kind, packet_item_ref,
          score, shortlist_rank, status, rationale_json
        )
        VALUES (?, ?, ?, ?, 'packet-run', ?, ?, ?, ?, 'proposed', '{}')
        """,
        [
            ("shortlist-run", "bridge:bridge-a", "bridge", "bridge-a", "bridge", "bridge-a", 2.0, 1),
            ("shortlist-run", "paper:source-paper", "paper", "source-paper", "stranded_qfin", "source-paper", 1.0, 2),
            ("shortlist-run", "composition:composition-a", "composition", "composition-a", "composition", "composition-a", 1.5, 3),
        ],
    )

    connection.executemany(
        """
        INSERT INTO selective_interpretations (
          run_id, shortlist_run_id, shortlist_id, classification, result_summary, first_step,
          instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close,
          confidence, raw_json
        )
        VALUES (?, 'shortlist-run', ?, ?, 'result', 'step', 'instrument', 'modern', 'why', 'gap', 'high', '{}')
        """,
        [
            ("interpret-run", "bridge:bridge-a", "TRANSLATION_CANDIDATE"),
            ("interpret-run", "paper:source-paper", "STRANDED_QFIN_RESULT"),
            ("interpret-run", "composition:composition-a", "NO_TRANSLATION"),
        ],
    )

    connection.executemany(
        """
        INSERT INTO enhanced_interpretations (
          run_id, batch_run_id, batch_item_id, operator_family, source_kind, source_run_id, source_ref,
          family_rank, source_score, packet_title, classification, result_summary, first_step,
          instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close,
          confidence, raw_json
        )
        VALUES (
          'enhanced-run', 'enhanced-batch-run', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'result', 'step',
          'instrument', 'modern', 'why', 'gap', 'high', '{}'
        )
        """,
        [
            ("bridge:bridge-a", "bridge", "review_packet", "packet-run", "bridge-a", 1, 2.4, "Bridge Packet", "TRANSLATION_CANDIDATE"),
            ("bridge:composition-a", "bridge", "review_packet", "packet-run", "composition-a", 2, 2.1, "Composition Pair As Bridge", "COMPOSITIONAL_CANDIDATE"),
            ("bridge:bridge-b", "bridge", "review_packet", "packet-run", "bridge-b", 3, 1.8, "Bridge Without Validation", "TRANSLATION_CANDIDATE"),
            (
                "market_design:composition:market_design_seams__refill_lag_resiliency",
                "market_design",
                "composition_candidate_pair",
                "composition-broadened-run",
                "market_design_seams__refill_lag_resiliency",
                1,
                2.7,
                "Composition packet: market_design_seams x refill_lag_resiliency",
                "TRANSLATION_CANDIDATE",
            ),
        ],
    )

    connection.executemany(
        """
        INSERT INTO anchors (anchor_id, label, anchor_type, tags_json)
        VALUES (?, ?, 'positive', '[]')
        """,
        [
            ("market_design_seams", "Market Design"),
            ("refill_lag_resiliency", "Refill Resiliency"),
        ],
    )
    connection.execute(
        """
        INSERT INTO composition_candidates (
          run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json
        )
        VALUES ('composition-broadened-run', 'market_design_seams', 'refill_lag_resiliency', 'source-market-design', 3.4, 1, '{}')
        """
    )

    connection.executemany(
        """
        INSERT INTO holdout_echoes (
          run_id, interpretation_run_id, shortlist_id, holdout_paper_id, echo_score, echo_rank,
          source_paper_ids_json, rationale_json
        )
        VALUES (?, 'interpret-run', ?, ?, ?, ?, ?, '{}')
        """,
        [
            ("echo-run", "bridge:bridge-a", "holdout-a", 0.9, 1, '["source-bridge"]'),
            ("echo-run", "bridge:bridge-a", "holdout-b", 0.8, 2, '["source-bridge"]'),
            ("echo-run", "paper:source-paper", "holdout-c", 0.85, 1, '["source-paper"]'),
            ("echo-run", "composition:composition-a", "holdout-b", 0.95, 1, '["source-bridge"]'),
        ],
    )

    connection.execute(
        """
        INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source, rationale_json)
        VALUES ('membership-run', 'source-paper', 'realized_market', 'fixture', '{}')
        """
    )

    connection.commit()


class MaterializeUnrealizedIdeasIndexTest(unittest.TestCase):
    def test_materializes_positive_index_and_excludes_fully_leaked_rows(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"

            connection = sqlite3.connect(db_path)
            seed_unrealized_index_fixture(connection)
            connection.close()

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "index-run",
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--interpretation-run-id",
                    "interpret-run",
                    "--holdout-run-id",
                    "echo-run",
                    "--membership-run-id",
                    "membership-run",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "unrealized_ideas_index_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["entry_count"], 1)
            self.assertEqual(metrics["top_ranked_shortlist_id"], "bridge:bridge-a")

            rows = [
                json.loads(line)
                for line in (output_dir / "unrealized_ideas_index.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual([row["shortlist_id"] for row in rows], ["bridge:bridge-a"])
            self.assertEqual(rows[0]["realized_market_leakage_score"], 0.0)
            self.assertEqual(rows[0]["classification"], "TRANSLATION_CANDIDATE")
            self.assertNotIn("paper:source-paper", [row["shortlist_id"] for row in rows])
            self.assertNotIn("composition:composition-a", [row["shortlist_id"] for row in rows])

            markdown = (output_dir / "unrealized_ideas_index.md").read_text(encoding="utf-8")
            self.assertIn("# Unrealized Ideas Index", markdown)
            self.assertIn("Bridge Packet", markdown)
            self.assertIn("realized-market leakage: `0.0`", markdown)

    def test_materializes_enhanced_bridge_rows_with_validation_linkage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"

            connection = sqlite3.connect(db_path)
            seed_unrealized_index_fixture(connection)
            connection.close()

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "enhanced-index-run",
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--interpretation-source",
                    "enhanced_bridge",
                    "--interpretation-run-id",
                    "enhanced-run",
                    "--validation-interpretation-run-id",
                    "interpret-run",
                    "--holdout-run-id",
                    "echo-run",
                    "--membership-run-id",
                    "membership-run",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "unrealized_ideas_index_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["entry_count"], 2)
            self.assertEqual(metrics["top_ranked_publication_item_id"], "bridge:bridge-a")

            rows = [
                json.loads(line)
                for line in (output_dir / "unrealized_ideas_index.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual([row["publication_item_id"] for row in rows], ["bridge:bridge-a", "bridge:composition-a"])
            self.assertEqual(rows[0]["publication_source_surface"], "enhanced_interpretation")
            self.assertEqual(rows[0]["shortlist_id"], "bridge:bridge-a")
            self.assertEqual(rows[1]["shortlist_id"], "composition:composition-a")
            self.assertNotIn("bridge:bridge-b", [row["publication_item_id"] for row in rows])

            markdown = (output_dir / "unrealized_ideas_index.md").read_text(encoding="utf-8")
            self.assertIn("publication item id: `bridge:bridge-a`", markdown)
            self.assertIn("publication source surface: `enhanced_interpretation`", markdown)

    def test_materializes_broadened_lane_rows_without_shortlist_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"

            connection = sqlite3.connect(db_path)
            seed_unrealized_index_fixture(connection)
            connection.close()

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "broadened-index-run",
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--interpretation-source",
                    "enhanced_broadened",
                    "--interpretation-run-id",
                    "enhanced-run",
                    "--validation-interpretation-run-id",
                    "interpret-run",
                    "--holdout-run-id",
                    "echo-run",
                    "--membership-run-id",
                    "membership-run",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "unrealized_ideas_index_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["entry_count"], 4)
            rows = [
                json.loads(line)
                for line in (output_dir / "unrealized_ideas_index.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            broadened = next(row for row in rows if row["publication_item_id"] == "market_design:composition:market_design_seams__refill_lag_resiliency")
            self.assertEqual(broadened["item_type"], "market_design")
            self.assertEqual(broadened["holdout_echo_score"], 0.0)
            self.assertEqual(broadened["realized_market_leakage_score"], 0.0)
            self.assertEqual(broadened["publication_source_surface"], "enhanced_interpretation")
            self.assertEqual(
                broadened["rationale"]["source_paper_ids"],
                ["source-market-design"],
            )

            markdown = (output_dir / "unrealized_ideas_index.md").read_text(encoding="utf-8")
            self.assertIn("Composition packet: market_design_seams x refill_lag_resiliency", markdown)


if __name__ == "__main__":
    unittest.main()
