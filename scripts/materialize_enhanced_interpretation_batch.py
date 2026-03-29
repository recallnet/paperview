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
LANE_ANCHOR_IDS = {
    "market_design": "market_design_seams",
    "settlement_resolution": "settlement_resolution_seams",
    "participant_pathologies": "participant_pathologies",
    "state_graph": "state_graph_inconsistencies",
    "lifecycle": "lifecycle_professionalization",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize an expanded interpretation batch across lane, stranded, and transition families.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="enhanced-interpretation-batch-20260328")
    parser.add_argument("--packet-run-id", default="review-packet-materialization-20260328")
    parser.add_argument("--bridge-run-id", default="bridge-materialization-20260328")
    parser.add_argument("--composition-run-id", default="composition-materialization-20260328")
    parser.add_argument("--resurfacing-run-id", default="stranded-resurfacing-materialization-20260328")
    parser.add_argument("--transition-run-id", default="transition-state-candidate-materialization-20260328")
    parser.add_argument("--prompt-path", default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument("--schema-path", default=str(DEFAULT_SCHEMA_PATH))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--lane-limit", type=int, default=10)
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


def load_packet_lookup(connection: sqlite3.Connection, packet_run_id: str) -> dict[tuple[str, str], dict]:
    rows = connection.execute(
        """
        SELECT packet_kind, item_ref, title, summary_json, packet_markdown
        FROM review_packets
        WHERE run_id = ?
          AND packet_kind IN ('bridge', 'composition')
        """,
        (packet_run_id,),
    ).fetchall()
    lookup: dict[tuple[str, str], dict] = {}
    for row in rows:
        lookup[(row["packet_kind"], row["item_ref"])] = {
            "title": row["title"],
            "summary": json.loads(row["summary_json"]),
            "markdown": row["packet_markdown"],
        }
    return lookup


def render_lane_packet(packet_kind: str, source_anchor_id: str, target_anchor_id: str, candidate_count: int, avg_score: float, max_score: float, representative_rows: list[sqlite3.Row]) -> str:
    lines = [
        f"# {packet_kind.capitalize()} Packet: {source_anchor_id} x {target_anchor_id}",
        "",
        f"- source anchor: `{source_anchor_id}`",
        f"- target anchor: `{target_anchor_id}`",
        f"- candidate count: `{candidate_count}`",
        f"- avg score: `{round(avg_score, 6)}`",
        f"- max score: `{round(max_score, 6)}`",
        "",
        "## Representative Papers",
    ]
    for item in representative_rows:
        lines.append(f"- `{item['paper_id']}` | {item['title']} | score `{round(float(item['score'] or 0.0), 6)}`")
    return "\n".join(lines) + "\n"


def fetch_lane_items(
    connection: sqlite3.Connection,
    packet_run_id: str,
    bridge_run_id: str,
    composition_run_id: str,
    lane_limit: int,
) -> list[dict]:
    packet_lookup = load_packet_lookup(connection, packet_run_id)
    lane_ranked: dict[str, list[dict]] = {lane: [] for lane in LANE_ANCHOR_IDS}
    pair_specs = [
        ("bridge", "bridge_candidates", "bridge_score", "bridge_rank", bridge_run_id),
        ("composition", "composition_candidates", "composition_score", "composition_rank", composition_run_id),
    ]
    for packet_kind, table_name, score_column, rank_column, run_id in pair_specs:
        rows = connection.execute(
            f"""
            SELECT
              source_anchor_id,
              target_anchor_id,
              AVG({score_column}) AS avg_score,
              MAX({score_column}) AS max_score,
              COUNT(*) AS candidate_count
            FROM {table_name}
            WHERE run_id = ?
            GROUP BY source_anchor_id, target_anchor_id
            ORDER BY max_score DESC, avg_score DESC, candidate_count DESC, source_anchor_id ASC, target_anchor_id ASC
            """,
            (run_id,),
        ).fetchall()
        for row in rows:
            source_anchor_id = row["source_anchor_id"]
            target_anchor_id = row["target_anchor_id"]
            item_ref = f"{source_anchor_id}__{target_anchor_id}"
            representative_rows = connection.execute(
                f"""
                SELECT
                  c.paper_id,
                  COALESCE(p.title, c.paper_id) AS title,
                  c.{score_column} AS score
                FROM {table_name} c
                JOIN papers p
                  ON p.paper_id = c.paper_id
                WHERE c.run_id = ?
                  AND c.source_anchor_id = ?
                  AND c.target_anchor_id = ?
                ORDER BY c.{score_column} DESC, c.{rank_column} ASC, p.title ASC, c.paper_id ASC
                LIMIT 5
                """,
                (run_id, source_anchor_id, target_anchor_id),
            ).fetchall()
            packet_payload = packet_lookup.get((packet_kind, item_ref))
            for lane_family, anchor_id in LANE_ANCHOR_IDS.items():
                if anchor_id not in (source_anchor_id, target_anchor_id):
                    continue
                other_anchor_id = target_anchor_id if source_anchor_id == anchor_id else source_anchor_id
                lane_ranked[lane_family].append(
                    {
                        "batch_item_id": f"{lane_family}:{packet_kind}:{item_ref}",
                        "operator_family": lane_family,
                        "lane_family": lane_family,
                        "source_kind": f"{packet_kind}_candidate_pair",
                        "source_run_id": run_id,
                        "source_ref": item_ref,
                        "family_rank": 0,
                        "score": round(float(row["max_score"] or 0.0), 6),
                        "packet_title": packet_payload["title"] if packet_payload else f"{packet_kind.capitalize()} packet: {source_anchor_id} x {target_anchor_id}",
                        "packet_summary": {
                            **(packet_payload["summary"] if packet_payload else {}),
                            "lane_family": lane_family,
                            "lane_anchor_id": anchor_id,
                            "other_anchor_id": other_anchor_id,
                            "packet_kind": packet_kind,
                            "source_anchor_id": source_anchor_id,
                            "target_anchor_id": target_anchor_id,
                            "avg_score": round(float(row["avg_score"] or 0.0), 6),
                            "max_score": round(float(row["max_score"] or 0.0), 6),
                            "candidate_count": int(row["candidate_count"]),
                            "representative_papers": [item["paper_id"] for item in representative_rows],
                        },
                        "packet_markdown": packet_payload["markdown"] if packet_payload else render_lane_packet(
                            packet_kind,
                            source_anchor_id,
                            target_anchor_id,
                            int(row["candidate_count"]),
                            float(row["avg_score"] or 0.0),
                            float(row["max_score"] or 0.0),
                            representative_rows,
                        ),
                    }
                )

    items: list[dict] = []
    for lane_family, candidates in lane_ranked.items():
        candidates.sort(
            key=lambda item: (
                -item["score"],
                item["packet_summary"]["packet_kind"],
                item["source_ref"],
            )
        )
        for rank, item in enumerate(candidates[:lane_limit], start=1):
            # @context decision -- S27 broadening must not collapse back into a generic bridge queue.
            # The batch is lane-first here: each new failure-mode lane gets its own top-k packet slice,
            # even when the same packet would also rank highly in another lane, so later interpretation
            # and publication can measure whether the broadened discovery space survives downstream.
            items.append({**item, "family_rank": rank})
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
                "lane_family": "stranded_qfin",
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
                    "lane_family": "stranded_qfin",
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
                "lane_family": "transition_state",
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
                    "lane_family": "transition_state",
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
                "bridge_run_id": args.bridge_run_id,
                "composition_run_id": args.composition_run_id,
                "resurfacing_run_id": args.resurfacing_run_id,
                "transition_run_id": args.transition_run_id,
                "lane_limit": args.lane_limit,
                "stranded_limit": args.stranded_limit,
                "transition_per_pattern": args.transition_per_pattern,
                "prompt_path": str(prompt_path),
                "schema_path": str(schema_path),
            },
        )

        lane_items = fetch_lane_items(
            connection,
            args.packet_run_id,
            args.bridge_run_id,
            args.composition_run_id,
            args.lane_limit,
        )
        stranded_items = fetch_stranded_items(connection, args.resurfacing_run_id, args.stranded_limit)
        transition_items = fetch_transition_items(connection, args.transition_run_id, args.transition_per_pattern)

        batch_items = []
        for item in lane_items + stranded_items + transition_items:
            # @context decision -- S23 expands beyond the shortlist pilot, but it must still stay
            # contract-first and map-first. The batch therefore packages only canonical stage outputs
            # from broadened packet lanes, stranded resurfacing candidates, and transition-state
            # candidates, and reuses the same prompt/schema references from S12 instead of
            # inventing a looser second interpretation contract.
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
            "bridge_run_id": args.bridge_run_id,
            "composition_run_id": args.composition_run_id,
            "resurfacing_run_id": args.resurfacing_run_id,
            "transition_run_id": args.transition_run_id,
            "prepared_count": len(batch_items),
            "counts_by_operator_family": {
                **{lane: len([item for item in lane_items if item["operator_family"] == lane]) for lane in LANE_ANCHOR_IDS},
                "stranded_qfin": len(stranded_items),
                "transition_state": len(transition_items),
            },
            "lane_limit": args.lane_limit,
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
