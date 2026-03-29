#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
EARLY_MARKET_LANES = (
    "market_design",
    "settlement_resolution",
    "participant_pathologies",
    "state_graph",
)
LIKELY_STAGE = {
    "market_design": "bootstrap_fragmentation",
    "settlement_resolution": "weak_post_trade",
    "participant_pathologies": "thin_unprofessionalized",
    "state_graph": "weakly_arbitraged_multi_venue",
}
WRONG_ACTOR = {
    "market_design": "venue operator or rule designer",
    "settlement_resolution": "clearer, collateral manager, or basis trader",
    "participant_pathologies": "uninformed or manipulative participant",
    "state_graph": "arbitrageur or cross-market hedger",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize the early-market failure modes ledger from diamond interpretations.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="early-market-failure-modes-20260329")
    parser.add_argument("--interpretation-run-id", default="diamond-interpretation-ingestion-20260329")
    parser.add_argument("--output-dir", default=None)
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
        CREATE TABLE IF NOT EXISTS early_market_failure_modes_ledger (
          run_id TEXT NOT NULL,
          interpretation_run_id TEXT NOT NULL,
          batch_item_id TEXT NOT NULL,
          lane_family TEXT NOT NULL,
          title TEXT NOT NULL,
          failure_mode TEXT NOT NULL,
          wrong_actor TEXT NOT NULL,
          why_persists TEXT NOT NULL,
          what_closes_it TEXT NOT NULL,
          likely_market_stage TEXT NOT NULL,
          first_test TEXT NOT NULL,
          modern_equivalent TEXT NOT NULL,
          gap_to_close TEXT NOT NULL,
          confidence TEXT NOT NULL,
          ledger_rank INTEGER NOT NULL,
          rationale_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, batch_item_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_early_market_failure_modes_run_rank
        ON early_market_failure_modes_ledger (run_id, ledger_rank)
        """
    )


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Early-Market Failure Modes Ledger",
        "",
        f"- entry count: `{len(rows)}`",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['ledger_rank']}. {row['title']}",
                "",
                f"- lane family: `{row['lane_family']}`",
                f"- wrong actor: `{row['wrong_actor']}`",
                f"- likely market stage: `{row['likely_market_stage']}`",
                f"- confidence: `{row['confidence']}`",
                "",
                f"Failure mode: {row['failure_mode']}",
                "",
                f"Why it persists: {row['why_persists']}",
                "",
                f"What closes it: {row['what_closes_it']}",
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


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "early_market_failure_modes_ledger",
            "started",
            {
                "interpretation_run_id": args.interpretation_run_id,
            },
        )
        rows = connection.execute(
            """
            SELECT
              batch_item_id,
              lane_family,
              packet_title,
              result_summary,
              why_stranded_or_unrealized,
              gap_to_close,
              modern_equivalent,
              first_test,
              confidence,
              shortlist_rank
            FROM diamond_interpretations
            WHERE run_id = ?
              AND lane_family IN ('market_design', 'settlement_resolution', 'participant_pathologies', 'state_graph')
              AND classification IN ('TRANSLATION_CANDIDATE', 'COMPOSITIONAL_CANDIDATE')
            ORDER BY shortlist_rank ASC, batch_item_id ASC
            """,
            (args.interpretation_run_id,),
        ).fetchall()
        connection.execute("DELETE FROM early_market_failure_modes_ledger WHERE run_id = ?", (args.run_id,))
        ledger_rows = []
        for rank, row in enumerate(rows, start=1):
            ledger_row = {
                "batch_item_id": row["batch_item_id"],
                "lane_family": row["lane_family"],
                "title": row["packet_title"],
                "failure_mode": row["result_summary"],
                "wrong_actor": WRONG_ACTOR[row["lane_family"]],
                "why_persists": row["why_stranded_or_unrealized"],
                "what_closes_it": row["gap_to_close"],
                "likely_market_stage": LIKELY_STAGE[row["lane_family"]],
                "first_test": row["first_test"],
                "modern_equivalent": row["modern_equivalent"],
                "gap_to_close": row["gap_to_close"],
                "confidence": row["confidence"],
                "ledger_rank": rank,
                "rationale": {"batch_item_id": row["batch_item_id"]},
            }
            connection.execute(
                """
                INSERT INTO early_market_failure_modes_ledger (
                  run_id, interpretation_run_id, batch_item_id, lane_family, title, failure_mode, wrong_actor,
                  why_persists, what_closes_it, likely_market_stage, first_test, modern_equivalent,
                  gap_to_close, confidence, ledger_rank, rationale_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.run_id,
                    args.interpretation_run_id,
                    ledger_row["batch_item_id"],
                    ledger_row["lane_family"],
                    ledger_row["title"],
                    ledger_row["failure_mode"],
                    ledger_row["wrong_actor"],
                    ledger_row["why_persists"],
                    ledger_row["what_closes_it"],
                    ledger_row["likely_market_stage"],
                    ledger_row["first_test"],
                    ledger_row["modern_equivalent"],
                    ledger_row["gap_to_close"],
                    ledger_row["confidence"],
                    ledger_row["ledger_rank"],
                    json.dumps(ledger_row["rationale"], sort_keys=True),
                ),
            )
            ledger_rows.append(ledger_row)

        jsonl_path = output_dir / "early_market_failure_modes_ledger.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in ledger_rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown_path = output_dir / "early_market_failure_modes_ledger.md"
        markdown_path.write_text(render_markdown(ledger_rows), encoding="utf-8")

        metrics = {
            "run_id": args.run_id,
            "interpretation_run_id": args.interpretation_run_id,
            "entry_count": len(ledger_rows),
            "counts_by_lane": {
                lane: sum(1 for row in ledger_rows if row["lane_family"] == lane)
                for lane in EARLY_MARKET_LANES
            },
            "top_ranked_batch_item_id": ledger_rows[0]["batch_item_id"] if ledger_rows else None,
        }
        metrics_path = output_dir / "early_market_failure_modes_ledger_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(connection, args.run_id, "early_market_failure_modes_ledger", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
