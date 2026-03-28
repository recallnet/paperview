#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_PROMPT_PATH = ROOT / "prompts" / "selective-interpretation-v1.md"
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "selective_interpretation.schema.json"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize a shortlist-gated selective interpretation batch.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="selective-interpretation-batch-20260328")
    parser.add_argument("--shortlist-run-id", default="shortlist-materialization-20260328")
    parser.add_argument("--prompt-path", default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument("--schema-path", default=str(DEFAULT_SCHEMA_PATH))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_shortlist_rows(connection: sqlite3.Connection, shortlist_run_id: str, limit: int | None):
    # @context decision -- Selective interpretation must be shortlist-gated. Joining through
    # shortlist_items and review_packets ensures this stage cannot silently expand back into
    # full-corpus extraction or bypass the reviewed packet contract.
    query = """
        SELECT
          si.shortlist_id,
          si.item_type,
          si.item_ref,
          si.packet_run_id,
          si.packet_kind,
          si.packet_item_ref,
          si.score,
          si.shortlist_rank,
          si.rationale_json,
          rp.title AS packet_title,
          rp.packet_markdown,
          rp.summary_json
        FROM shortlist_items si
        JOIN review_packets rp
          ON rp.run_id = si.packet_run_id
         AND rp.packet_kind = si.packet_kind
         AND rp.item_ref = si.packet_item_ref
        WHERE si.run_id = ?
        ORDER BY si.shortlist_rank ASC
    """
    params: list[object] = [shortlist_run_id]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    return connection.execute(query, params).fetchall()


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = Path(args.prompt_path).resolve()
    schema_path = Path(args.schema_path).resolve()
    prompt_text = load_prompt(prompt_path)
    schema = load_schema(schema_path)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        log_run_event(
            connection,
            args.run_id,
            "selective_interpretation",
            "started",
            {
                "shortlist_run_id": args.shortlist_run_id,
                "prompt_path": str(prompt_path),
                "schema_path": str(schema_path),
                "limit": args.limit,
            },
        )

        rows = fetch_shortlist_rows(connection, args.shortlist_run_id, args.limit)
        batch_items = []
        counts_by_item_type = {}
        for row in rows:
            counts_by_item_type[row["item_type"]] = counts_by_item_type.get(row["item_type"], 0) + 1
            batch_items.append(
                {
                    "shortlist_run_id": args.shortlist_run_id,
                    "shortlist_id": row["shortlist_id"],
                    "shortlist_rank": row["shortlist_rank"],
                    "item_type": row["item_type"],
                    "item_ref": row["item_ref"],
                    "packet_kind": row["packet_kind"],
                    "packet_item_ref": row["packet_item_ref"],
                    "score": row["score"],
                    "prompt_path": str(prompt_path),
                    "schema_path": str(schema_path),
                    "schema_required_fields": schema.get("required", []),
                    "packet_title": row["packet_title"],
                    "packet_summary": json.loads(row["summary_json"]),
                    "packet_markdown": row["packet_markdown"],
                    "shortlist_rationale": json.loads(row["rationale_json"]),
                    # @context requirement -- The model-facing batch carries the exact prompt and
                    # schema references so later execution and ingestion can validate against the
                    # same contract the batch was prepared with.
                    "prompt_text": prompt_text,
                }
            )

        batch_path = output_dir / "interpretation_batch.jsonl"
        with batch_path.open("w", encoding="utf-8") as handle:
            for item in batch_items:
                handle.write(json.dumps(item, sort_keys=True) + "\n")

        metrics = {
            "run_id": args.run_id,
            "shortlist_run_id": args.shortlist_run_id,
            "prepared_count": len(batch_items),
            "counts_by_item_type": counts_by_item_type,
            "prompt_path": str(prompt_path),
            "schema_path": str(schema_path),
        }
        metrics_path = output_dir / "interpretation_batch_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "selective_interpretation", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
