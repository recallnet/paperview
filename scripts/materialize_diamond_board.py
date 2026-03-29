#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_RUNS_ROOT = ROOT / "data" / "structural-analogy" / "runs"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize the canonical diamond board from publication surfaces.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="diamond-board-20260329")
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--interpretation-run-id", default="diamond-interpretation-ingestion-20260329")
    parser.add_argument("--unrealized-run-id", default="unrealized-ideas-index-diamond-20260329")
    parser.add_argument("--stranded-run-id", default="stranded-result-ledger-diamond-20260329")
    parser.add_argument("--transition-run-id", default="transition-state-ledger-diamond-20260329")
    parser.add_argument("--early-market-run-id", default="early-market-failure-modes-20260329")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--root-markdown-path", default=str(ROOT / "diamond_board.md"))
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def ensure_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS diamond_board_entries (
          run_id TEXT NOT NULL,
          publication_item_id TEXT NOT NULL,
          lane_family TEXT NOT NULL,
          source_surface TEXT NOT NULL,
          board_rank INTEGER NOT NULL,
          title TEXT NOT NULL,
          result_summary TEXT NOT NULL,
          modern_equivalent TEXT NOT NULL,
          first_test TEXT NOT NULL,
          gap_to_close TEXT NOT NULL,
          confidence TEXT NOT NULL,
          rationale_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, publication_item_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_diamond_board_entries_run_rank
        ON diamond_board_entries (run_id, board_rank)
        """
    )


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def render_markdown(rows: list[dict]) -> str:
    lane_counts = {}
    for row in rows:
        lane_counts[row["lane_family"]] = lane_counts.get(row["lane_family"], 0) + 1
    lines = [
        "# Diamond Board",
        "",
        f"- entry count: `{len(rows)}`",
        f"- lane diversity: `{len(lane_counts)}`",
        "",
        "## Lane Coverage",
        "",
    ]
    for lane in sorted(lane_counts):
        lines.append(f"- `{lane}`: `{lane_counts[lane]}`")
    lines.extend(["", "## Board", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['board_rank']}. {row['title']}",
                "",
                f"- lane family: `{row['lane_family']}`",
                f"- source surface: `{row['source_surface']}`",
                f"- publication item id: `{row['publication_item_id']}`",
                f"- confidence: `{row['confidence']}`",
                "",
                f"Result: {row['result_summary']}",
                "",
                f"Modern equivalent: {row['modern_equivalent']}",
                "",
                f"First test: {row['first_test']}",
                "",
                f"Gap to close: {row['gap_to_close']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def select_board_rows(entries: list[dict]) -> list[dict]:
    ordered = sorted(entries, key=lambda row: (row["lane_family"], row["source_surface"], row["publication_item_id"]))
    # @context decision -- The diamond board is the human-facing diversity check for S33. It must
    # show one live survivor from every lane before repeating a stronger lane, or the board will
    # hide publication skew instead of exposing it.
    selected = []
    seen_lanes = set()
    for row in ordered:
        if row["lane_family"] in seen_lanes:
            continue
        selected.append(row)
        seen_lanes.add(row["lane_family"])
    for row in ordered:
        if row in selected:
            continue
        selected.append(row)
    for rank, row in enumerate(selected, start=1):
        row["board_rank"] = rank
        # @context decision -- The same interpreted thesis can legitimately publish to multiple
        # S33 surfaces, such as an unrealized index row and the early-market failure ledger. The
        # board stores source-qualified ids so diversity accounting does not collapse distinct
        # publication surfaces into a false uniqueness conflict.
        row["board_publication_item_id"] = f"{row['source_surface']}:{row['publication_item_id']}"
    return selected


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    runs_root = Path(args.runs_root).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else runs_root / args.run_id
    root_markdown_path = Path(args.root_markdown_path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "diamond_board",
            "started",
            {
                "interpretation_run_id": args.interpretation_run_id,
                "unrealized_run_id": args.unrealized_run_id,
                "stranded_run_id": args.stranded_run_id,
                "transition_run_id": args.transition_run_id,
                "early_market_run_id": args.early_market_run_id,
            },
        )
        unrealized_rows = load_jsonl(runs_root / args.unrealized_run_id / "unrealized_ideas_index.jsonl")
        stranded_rows = load_jsonl(runs_root / args.stranded_run_id / "stranded_result_ledger.jsonl")
        transition_rows = load_jsonl(runs_root / args.transition_run_id / "transition_state_ledger.jsonl")
        early_rows = load_jsonl(runs_root / args.early_market_run_id / "early_market_failure_modes_ledger.jsonl")

        entries = []
        for row in unrealized_rows:
            entries.append(
                {
                    "lane_family": row["item_type"],
                    "source_surface": "unrealized_ideas_index",
                    "publication_item_id": row["publication_item_id"],
                    "title": row["title"],
                    "result_summary": row["result_summary"],
                    "modern_equivalent": row["modern_equivalent"],
                    "first_test": row["first_step"],
                    "gap_to_close": row["gap_to_close"],
                    "confidence": row["confidence"],
                }
            )
        for row in stranded_rows:
            entries.append(
                {
                    "lane_family": "stranded_qfin",
                    "source_surface": "stranded_result_ledger",
                    "publication_item_id": row["publication_item_id"],
                    "title": row["paper_id"],
                    "result_summary": row["result_summary"],
                    "modern_equivalent": row["modern_equivalent"],
                    "first_test": row["first_test"],
                    "gap_to_close": row["gap_to_close"],
                    "confidence": row["confidence"],
                }
            )
        for row in transition_rows:
            entries.append(
                {
                    "lane_family": "transition_state",
                    "source_surface": "transition_state_ledger",
                    "publication_item_id": row["publication_item_id"],
                    "title": row["pattern_label"],
                    "result_summary": row["result_summary"],
                    "modern_equivalent": row["modern_equivalent"],
                    "first_test": row["first_test"],
                    "gap_to_close": row["gap_to_close"],
                    "confidence": row["confidence"],
                }
            )
        for row in early_rows:
            entries.append(
                {
                    "lane_family": row["lane_family"],
                    "source_surface": "early_market_failure_modes_ledger",
                    "publication_item_id": row["batch_item_id"],
                    "title": row["title"],
                    "result_summary": row["failure_mode"],
                    "modern_equivalent": row["modern_equivalent"],
                    "first_test": row["first_test"],
                    "gap_to_close": row["gap_to_close"],
                    "confidence": row["confidence"],
                }
            )

        board_rows = select_board_rows(entries)
        connection.execute("DELETE FROM diamond_board_entries WHERE run_id = ?", (args.run_id,))
        for row in board_rows:
            connection.execute(
                """
                INSERT INTO diamond_board_entries (
                  run_id, publication_item_id, lane_family, source_surface, board_rank, title,
                  result_summary, modern_equivalent, first_test, gap_to_close, confidence, rationale_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.run_id,
                    row["board_publication_item_id"],
                    row["lane_family"],
                    row["source_surface"],
                    row["board_rank"],
                    row["title"],
                    row["result_summary"],
                    row["modern_equivalent"],
                    row["first_test"],
                    row["gap_to_close"],
                    row["confidence"],
                    json.dumps({}, sort_keys=True),
                ),
            )

        jsonl_path = output_dir / "diamond_board.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in board_rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown = render_markdown(board_rows)
        markdown_path = output_dir / "diamond_board.md"
        markdown_path.write_text(markdown, encoding="utf-8")
        root_markdown_path.write_text(markdown, encoding="utf-8")

        metrics = {
            "run_id": args.run_id,
            "interpretation_run_id": args.interpretation_run_id,
            "entry_count": len(board_rows),
            "lane_diversity": len({row["lane_family"] for row in board_rows}),
            "counts_by_lane": {
                lane: sum(1 for row in board_rows if row["lane_family"] == lane)
                for lane in sorted({row["lane_family"] for row in board_rows})
            },
            "root_markdown_path": str(root_markdown_path),
        }
        metrics_path = output_dir / "diamond_board_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(connection, args.run_id, "diamond_board", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
