import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_diamond_board.py"


class MaterializeDiamondBoardTest(unittest.TestCase):
    def test_materializes_lane_first_board_and_root_markdown(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            runs_root = tmp_path / "runs"
            output_dir = tmp_path / "diamond-board-run"
            root_markdown_path = tmp_path / "diamond_board.md"

            connection = sqlite3.connect(db_path)
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            connection.close()

            unrealized_dir = runs_root / "unrealized-run"
            stranded_dir = runs_root / "stranded-run"
            transition_dir = runs_root / "transition-run"
            early_dir = runs_root / "early-run"
            for directory in (unrealized_dir, stranded_dir, transition_dir, early_dir):
                directory.mkdir(parents=True, exist_ok=True)

            (unrealized_dir / "unrealized_ideas_index.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "publication_item_id": "market_design:item-a",
                                "item_type": "market_design",
                                "title": "Market Design Idea",
                                "result_summary": "design seam",
                                "modern_equivalent": "modern design",
                                "first_step": "test design",
                                "gap_to_close": "close design gap",
                                "confidence": "high",
                            },
                            sort_keys=True,
                        ),
                        json.dumps(
                            {
                                "publication_item_id": "market_design:item-b",
                                "item_type": "market_design",
                                "title": "Second Market Design Idea",
                                "result_summary": "second design seam",
                                "modern_equivalent": "modern design two",
                                "first_step": "test design two",
                                "gap_to_close": "close design gap two",
                                "confidence": "medium",
                            },
                            sort_keys=True,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (stranded_dir / "stranded_result_ledger.jsonl").write_text(
                json.dumps(
                    {
                        "publication_item_id": "stranded_qfin:paper-a",
                        "paper_id": "paper-a",
                        "result_summary": "stranded result",
                        "modern_equivalent": "modern stranded",
                        "first_test": "test stranded",
                        "gap_to_close": "close stranded gap",
                        "confidence": "high",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            (transition_dir / "transition_state_ledger.jsonl").write_text(
                json.dumps(
                    {
                        "publication_item_id": "transition_state:pattern-a:paper-a",
                        "pattern_label": "Queue x Refill",
                        "result_summary": "transition seam",
                        "modern_equivalent": "modern transition",
                        "first_test": "test transition",
                        "gap_to_close": "close transition gap",
                        "confidence": "medium",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            (early_dir / "early_market_failure_modes_ledger.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "batch_item_id": "settlement_resolution:item-a",
                                "lane_family": "settlement_resolution",
                                "title": "Settlement Failure",
                                "failure_mode": "settlement seam",
                                "modern_equivalent": "modern settlement",
                                "first_test": "test settlement",
                                "gap_to_close": "close settlement gap",
                                "confidence": "high",
                            },
                            sort_keys=True,
                        ),
                        json.dumps(
                            {
                                "batch_item_id": "state_graph:item-a",
                                "lane_family": "state_graph",
                                "title": "State Graph Failure",
                                "failure_mode": "state graph seam",
                                "modern_equivalent": "modern state graph",
                                "first_test": "test state graph",
                                "gap_to_close": "close state graph gap",
                                "confidence": "medium",
                            },
                            sort_keys=True,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "diamond-board-run",
                    "--runs-root",
                    str(runs_root),
                    "--interpretation-run-id",
                    "diamond-run",
                    "--unrealized-run-id",
                    "unrealized-run",
                    "--stranded-run-id",
                    "stranded-run",
                    "--transition-run-id",
                    "transition-run",
                    "--early-market-run-id",
                    "early-run",
                    "--output-dir",
                    str(output_dir),
                    "--root-markdown-path",
                    str(root_markdown_path),
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "diamond_board_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["entry_count"], 6)
            self.assertEqual(metrics["lane_diversity"], 5)
            self.assertEqual(metrics["counts_by_lane"]["market_design"], 2)

            rows = [
                json.loads(line)
                for line in (output_dir / "diamond_board.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertEqual(rows[0]["lane_family"], "market_design")
            self.assertEqual(rows[1]["lane_family"], "settlement_resolution")
            self.assertEqual(rows[2]["lane_family"], "state_graph")
            self.assertEqual(rows[3]["lane_family"], "stranded_qfin")
            self.assertEqual(rows[4]["lane_family"], "transition_state")
            self.assertEqual(rows[5]["lane_family"], "market_design")
            self.assertEqual(root_markdown_path.read_text(encoding="utf-8"), (output_dir / "diamond_board.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
