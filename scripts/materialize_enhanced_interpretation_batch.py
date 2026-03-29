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
    parser = argparse.ArgumentParser(description="Materialize an expanded interpretation batch across bridge, stranded, and transition families.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="enhanced-interpretation-batch-20260328")
    parser.add_argument("--packet-run-id", default="review-packet-materialization-20260328")
    parser.add_argument("--resurfacing-run-id", default="stranded-resurfacing-materialization-20260328")
    parser.add_argument("--transition-run-id", default="transition-state-candidate-materialization-20260328")
    parser.add_argument("--prompt-path", default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument("--schema-path", default=str(DEFAULT_SCHEMA_PATH))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--bridge-limit", type=int, default=12)
    parser.add_argument("--stranded-limit", type=int, default=12)
    parser.add_argument("--transition-per-pattern", type=int, default=3)
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


def fetch_bridge_items(connection: sqlite3.Connection, packet_run_id: str, limit: int) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          packet_kind,
          item_ref,
          title,
          summary_json,
          packet_markdown
        FROM review_packets
        WHERE run_id = ?
          AND packet_kind = 'bridge'
        ORDER BY json_extract(summary_json, '$.max_score') DESC, item_ref ASC
        LIMIT ?
        """,
        (packet_run_id, limit),
    ).fetchall()
    items = []
    for rank, row in enumerate(rows, start=1):
        items.append(
            {
                "batch_item_id": f"bridge:{row['item_ref']}",
                "operator_family": "bridge",
                "source_kind": "review_packet",
                "source_run_id": packet_run_id,
                "source_ref": row["item_ref"],
                "family_rank": rank,
                "score": round(float(json.loads(row["summary_json"]).get("max_score") or 0.0), 6),
                "packet_title": row["title"],
                "packet_summary": json.loads(row["summary_json"]),
                "packet_markdown": row["packet_markdown"],
            }
        )
    return items


def fetch_stranded_items(connection: sqlite3.Connection, resurfacing_run_id: str, limit: int) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          src.paper_id,
          src.resurfacing_score,
          src.resurfacing_rank,
          src.rationale_json,
          p.title,
          p.abstract,
          p.primary_category,
          p.published_at
        FROM stranded_resurfacing_candidates src
        JOIN papers p
          ON p.paper_id = src.paper_id
        WHERE src.run_id = ?
        ORDER BY src.resurfacing_rank ASC, src.paper_id ASC
        LIMIT ?
        """,
        (resurfacing_run_id, limit),
    ).fetchall()
    items = []
    for row in rows:
        rationale = json.loads(row["rationale_json"] or "{}")
        items.append(
            {
                "batch_item_id": f"stranded_qfin:{row['paper_id']}",
                "operator_family": "stranded_qfin",
                "source_kind": "stranded_resurfacing_candidate",
                "source_run_id": resurfacing_run_id,
                "source_ref": row["paper_id"],
                "family_rank": int(row["resurfacing_rank"]),
                "score": round(float(row["resurfacing_score"] or 0.0), 6),
                "packet_title": f"Stranded resurfacing packet: {row['title']}",
                "packet_summary": {
                    "paper_id": row["paper_id"],
                    "primary_category": row["primary_category"],
                    "published_at": row["published_at"],
                    "resurfacing_score": round(float(row["resurfacing_score"] or 0.0), 6),
                    "rationale": rationale,
                },
                "packet_markdown": "\n".join(
                    [
                        f"# Stranded resurfacing packet: {row['title']}",
                        "",
                        f"- paper id: `{row['paper_id']}`",
                        f"- category: `{row['primary_category']}`",
                        f"- published at: `{row['published_at']}`",
                        f"- resurfacing score: `{round(float(row['resurfacing_score'] or 0.0), 6)}`",
                        f"- venue closeness: `{rationale.get('venue_closeness_score', 0.0)}`",
                        f"- result specificity: `{rationale.get('result_specificity_score', 0.0)}`",
                        "",
                        row["abstract"] or "",
                    ]
                ).strip()
                + "\n",
            }
        )
    return items


def fetch_transition_items(connection: sqlite3.Connection, transition_run_id: str, per_pattern: int) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          tc.pattern_id,
          tc.paper_id,
          tc.transition_state_candidate_score,
          tc.transition_state_rank,
          tc.rationale_json,
          ap.label,
          p.title,
          p.abstract,
          p.primary_category,
          p.published_at
        FROM transition_state_candidates tc
        JOIN agitator_patterns ap
          ON ap.pattern_id = tc.pattern_id
        JOIN papers p
          ON p.paper_id = tc.paper_id
        WHERE tc.run_id = ?
          AND tc.transition_state_rank <= ?
        ORDER BY tc.pattern_id ASC, tc.transition_state_rank ASC, tc.paper_id ASC
        """,
        (transition_run_id, per_pattern),
    ).fetchall()
    items = []
    for row in rows:
        rationale = json.loads(row["rationale_json"] or "{}")
        items.append(
            {
                "batch_item_id": f"transition_state:{row['pattern_id']}:{row['paper_id']}",
                "operator_family": "transition_state",
                "source_kind": "transition_state_candidate",
                "source_run_id": transition_run_id,
                "source_ref": row["pattern_id"],
                "family_rank": int(row["transition_state_rank"]),
                "score": round(float(row["transition_state_candidate_score"] or 0.0), 6),
                "packet_title": f"Transition-state packet: {row['label']}",
                "packet_summary": {
                    "pattern_id": row["pattern_id"],
                    "pattern_label": row["label"],
                    "paper_id": row["paper_id"],
                    "primary_category": row["primary_category"],
                    "published_at": row["published_at"],
                    "transition_state_score": round(float(row["transition_state_candidate_score"] or 0.0), 6),
                    "rationale": rationale,
                },
                "packet_markdown": "\n".join(
                    [
                        f"# Transition-state packet: {row['label']}",
                        "",
                        f"- pattern id: `{row['pattern_id']}`",
                        f"- paper id: `{row['paper_id']}`",
                        f"- category: `{row['primary_category']}`",
                        f"- published at: `{row['published_at']}`",
                        f"- transition-state score: `{round(float(row['transition_state_candidate_score'] or 0.0), 6)}`",
                        f"- probe rank: `{rationale.get('probe_rank', 0)}`",
                        f"- family count: `{rationale.get('family_count', 0)}`",
                        "",
                        row["abstract"] or "",
                    ]
                ).strip()
                + "\n",
            }
        )
    return items


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
            "enhanced_interpretation_batch",
            "started",
            {
                "packet_run_id": args.packet_run_id,
                "resurfacing_run_id": args.resurfacing_run_id,
                "transition_run_id": args.transition_run_id,
                "bridge_limit": args.bridge_limit,
                "stranded_limit": args.stranded_limit,
                "transition_per_pattern": args.transition_per_pattern,
                "prompt_path": str(prompt_path),
                "schema_path": str(schema_path),
            },
        )

        bridge_items = fetch_bridge_items(connection, args.packet_run_id, args.bridge_limit)
        stranded_items = fetch_stranded_items(connection, args.resurfacing_run_id, args.stranded_limit)
        transition_items = fetch_transition_items(connection, args.transition_run_id, args.transition_per_pattern)

        batch_items = []
        for item in bridge_items + stranded_items + transition_items:
            # @context decision -- S23 expands beyond the shortlist pilot, but it must still stay
            # contract-first and map-first. The batch therefore packages only canonical stage outputs
            # from bridge packets, stranded resurfacing candidates, and transition-state candidates,
            # and reuses the same prompt/schema references from S12 instead of inventing a looser
            # second interpretation contract.
            batch_items.append(
                {
                    **item,
                    "prompt_path": str(prompt_path),
                    "schema_path": str(schema_path),
                    "schema_required_fields": schema.get("required", []),
                    "prompt_text": prompt_text,
                }
            )

        batch_path = output_dir / "enhanced_interpretation_batch.jsonl"
        with batch_path.open("w", encoding="utf-8") as handle:
            for item in batch_items:
                handle.write(json.dumps(item, sort_keys=True) + "\n")

        metrics = {
            "run_id": args.run_id,
            "packet_run_id": args.packet_run_id,
            "resurfacing_run_id": args.resurfacing_run_id,
            "transition_run_id": args.transition_run_id,
            "prepared_count": len(batch_items),
            "counts_by_operator_family": {
                "bridge": len(bridge_items),
                "stranded_qfin": len(stranded_items),
                "transition_state": len(transition_items),
            },
            "bridge_limit": args.bridge_limit,
            "stranded_limit": args.stranded_limit,
            "transition_per_pattern": args.transition_per_pattern,
            "prompt_path": str(prompt_path),
            "schema_path": str(schema_path),
        }
        metrics_path = output_dir / "enhanced_interpretation_batch_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "enhanced_interpretation_batch", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
