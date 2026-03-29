#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_PROMPT_PATH = ROOT / "prompts" / "diamond-interpretation-v2.md"
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "diamond_interpretation.schema.json"

CANONICAL_LANES = (
    "market_design",
    "settlement_resolution",
    "participant_pathologies",
    "state_graph",
    "stranded_qfin",
    "transition_state",
)
LANE_ANCHOR_IDS = {
    "market_design": "market_design_seams",
    "settlement_resolution": "settlement_resolution_seams",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize a shortlist-gated diamond interpretation batch.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="diamond-interpretation-batch-20260329")
    parser.add_argument("--diamond-score-run-id", default="diamond-score-materialization-20260329")
    parser.add_argument("--bridge-run-id", default="bridge-materialization-20260328-broadened")
    parser.add_argument("--composition-run-id", default="composition-materialization-20260328-broadened")
    parser.add_argument("--stranded-run-id", default="stranded-resurfacing-materialization-20260328")
    parser.add_argument("--transition-run-id", default="transition-state-candidate-materialization-20260328-broadened")
    parser.add_argument("--state-graph-run-id", default="state-graph-candidate-materialization-20260329")
    parser.add_argument("--participant-run-id", default="participant-pathology-candidate-materialization-20260329")
    parser.add_argument("--prompt-path", default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument("--schema-path", default=str(DEFAULT_SCHEMA_PATH))
    parser.add_argument("--lane-quota", type=int, default=5)
    parser.add_argument("--overall-limit", type=int, default=40)
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


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_pair_lane_items(
    connection: sqlite3.Connection,
    lane_family: str,
    anchor_id: str,
    table_name: str,
    score_column: str,
    rank_column: str,
    run_id: str,
) -> list[dict]:
    rows = connection.execute(
        f"""
        SELECT
          source_anchor_id,
          target_anchor_id,
          MAX({score_column}) AS max_score,
          AVG({score_column}) AS avg_score,
          COUNT(*) AS candidate_count
        FROM {table_name}
        WHERE run_id = ?
          AND (? IN (source_anchor_id, target_anchor_id))
        GROUP BY source_anchor_id, target_anchor_id
        ORDER BY max_score DESC, avg_score DESC, source_anchor_id ASC, target_anchor_id ASC
        """,
        (run_id, anchor_id),
    ).fetchall()
    items = []
    for row in rows:
        source_anchor_id = row["source_anchor_id"]
        target_anchor_id = row["target_anchor_id"]
        item_ref = f"{source_anchor_id}__{target_anchor_id}"
        representative_rows = connection.execute(
            f"""
            SELECT
              c.paper_id,
              COALESCE(p.title, c.paper_id) AS title,
              c.{score_column} AS operator_score,
              COALESCE(ds.diamond_score, 0.0) AS diamond_score,
              ds.top_lane AS top_lane
            FROM {table_name} c
            JOIN papers p
              ON p.paper_id = c.paper_id
            LEFT JOIN diamond_scores ds
              ON ds.run_id = ?
             AND ds.paper_id = c.paper_id
            WHERE c.run_id = ?
              AND c.source_anchor_id = ?
              AND c.target_anchor_id = ?
            ORDER BY ds.diamond_score DESC, c.{score_column} DESC, c.{rank_column} ASC, c.paper_id ASC
            LIMIT 5
            """,
            (
                args_global["diamond_score_run_id"],
                run_id,
                source_anchor_id,
                target_anchor_id,
            ),
        ).fetchall()
        if not representative_rows:
            continue
        best_row = representative_rows[0]
        batch_item_id = f"{lane_family}:{table_name.replace('_candidates', '')}:{item_ref}"
        packet_summary = {
            "lane_family": lane_family,
            "packet_kind": table_name.replace("_candidates", ""),
            "source_anchor_id": source_anchor_id,
            "target_anchor_id": target_anchor_id,
            "candidate_count": int(row["candidate_count"]),
            "max_operator_score": round(float(row["max_score"] or 0.0), 6),
            "avg_operator_score": round(float(row["avg_score"] or 0.0), 6),
            "representative_papers": [rep["paper_id"] for rep in representative_rows],
        }
        packet_markdown = "\n".join(
            [
                f"# {lane_family.replace('_', ' ').title()} packet: {source_anchor_id} x {target_anchor_id}",
                "",
                f"- lane family: `{lane_family}`",
                f"- packet kind: `{packet_summary['packet_kind']}`",
                f"- source anchor: `{source_anchor_id}`",
                f"- target anchor: `{target_anchor_id}`",
                f"- candidate count: `{packet_summary['candidate_count']}`",
                f"- max operator score: `{packet_summary['max_operator_score']}`",
                "",
                "## Representative Papers",
            ]
            + [
                f"- `{rep['paper_id']}` | {rep['title']} | diamond `{round(float(rep['diamond_score'] or 0.0), 6)}` | operator `{round(float(rep['operator_score'] or 0.0), 6)}`"
                for rep in representative_rows
            ]
        ) + "\n"
        items.append(
            {
                "batch_item_id": batch_item_id,
                "lane_family": lane_family,
                "operator_family": packet_summary["packet_kind"],
                "source_kind": f"{packet_summary['packet_kind']}_candidate_pair",
                "source_run_id": run_id,
                "source_ref": item_ref,
                "family_rank": 0,
                "source_score": round(float(row["max_score"] or 0.0), 6),
                "diamond_score": round(float(best_row["diamond_score"] or 0.0), 6),
                "packet_title": f"{lane_family.replace('_', ' ').title()} packet: {source_anchor_id} x {target_anchor_id}",
                "packet_summary": packet_summary,
                "packet_markdown": packet_markdown,
            }
        )
    return items


def fetch_transition_items(connection: sqlite3.Connection, run_id: str) -> list[dict]:
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
          COALESCE(ds.diamond_score, 0.0) AS diamond_score
        FROM transition_state_candidates tc
        JOIN papers p
          ON p.paper_id = tc.paper_id
        LEFT JOIN agitator_patterns ap
          ON ap.pattern_id = tc.pattern_id
        LEFT JOIN diamond_scores ds
          ON ds.run_id = ?
         AND ds.paper_id = tc.paper_id
        WHERE tc.run_id = ?
        ORDER BY ds.diamond_score DESC, tc.transition_state_candidate_score DESC, tc.transition_state_rank ASC, tc.paper_id ASC
        """,
        (args_global["diamond_score_run_id"], run_id),
    ).fetchall()
    items = []
    for row in rows:
        rationale = json.loads(row["rationale_json"] or "{}")
        items.append(
            {
                "batch_item_id": f"transition_state:{row['pattern_id']}:{row['paper_id']}",
                "lane_family": "transition_state",
                "operator_family": "transition_state",
                "source_kind": "transition_state_candidate",
                "source_run_id": run_id,
                "source_ref": row["paper_id"],
                "family_rank": int(row["transition_state_rank"]),
                "source_score": round(float(row["transition_state_candidate_score"] or 0.0), 6),
                "diamond_score": round(float(row["diamond_score"] or 0.0), 6),
                "packet_title": f"Transition-state packet: {row['label'] or row['pattern_id']}",
                "packet_summary": {
                    "pattern_id": row["pattern_id"],
                    "pattern_label": row["label"] or row["pattern_id"],
                    "paper_id": row["paper_id"],
                    "rationale": rationale,
                },
                "packet_markdown": "\n".join(
                    [
                        f"# Transition-state packet: {row['label'] or row['pattern_id']}",
                        "",
                        f"- paper id: `{row['paper_id']}`",
                        f"- pattern id: `{row['pattern_id']}`",
                        f"- transition-state score: `{round(float(row['transition_state_candidate_score'] or 0.0), 6)}`",
                        "",
                        row["abstract"] or "",
                    ]
                ).strip()
                + "\n",
            }
        )
    return items


def fetch_paper_operator_items(connection: sqlite3.Connection, lane_family: str, operator_family: str, table_name: str, score_column: str, rank_column: str, run_id: str) -> list[dict]:
    rows = connection.execute(
        f"""
        SELECT
          c.paper_id,
          c.{score_column} AS source_score,
          c.{rank_column} AS family_rank,
          c.rationale_json,
          p.title,
          p.abstract,
          COALESCE(ds.diamond_score, 0.0) AS diamond_score
        FROM {table_name} c
        JOIN papers p
          ON p.paper_id = c.paper_id
        LEFT JOIN diamond_scores ds
          ON ds.run_id = ?
         AND ds.paper_id = c.paper_id
        WHERE c.run_id = ?
        ORDER BY ds.diamond_score DESC, c.{score_column} DESC, c.{rank_column} ASC, c.paper_id ASC
        """,
        (args_global["diamond_score_run_id"], run_id),
    ).fetchall()
    items = []
    for row in rows:
        rationale = json.loads(row["rationale_json"] or "{}")
        items.append(
            {
                "batch_item_id": f"{lane_family}:{row['paper_id']}",
                "lane_family": lane_family,
                "operator_family": operator_family,
                "source_kind": table_name.replace("_candidates", "_candidate"),
                "source_run_id": run_id,
                "source_ref": row["paper_id"],
                "family_rank": int(row["family_rank"]),
                "source_score": round(float(row["source_score"] or 0.0), 6),
                "diamond_score": round(float(row["diamond_score"] or 0.0), 6),
                "packet_title": f"{lane_family.replace('_', ' ').title()} packet: {row['title']}",
                "packet_summary": {
                    "paper_id": row["paper_id"],
                    "rationale": rationale,
                },
                "packet_markdown": "\n".join(
                    [
                        f"# {lane_family.replace('_', ' ').title()} packet: {row['title']}",
                        "",
                        f"- paper id: `{row['paper_id']}`",
                        f"- operator score: `{round(float(row['source_score'] or 0.0), 6)}`",
                        "",
                        row["abstract"] or "",
                    ]
                ).strip()
                + "\n",
            }
        )
    return items


def fetch_stranded_items(connection: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          c.paper_id,
          c.resurfacing_score,
          c.resurfacing_rank,
          c.rationale_json,
          p.title,
          p.abstract,
          COALESCE(ds.diamond_score, 0.0) AS diamond_score
        FROM stranded_resurfacing_candidates c
        JOIN papers p
          ON p.paper_id = c.paper_id
        LEFT JOIN diamond_scores ds
          ON ds.run_id = ?
         AND ds.paper_id = c.paper_id
        WHERE c.run_id = ?
        ORDER BY ds.diamond_score DESC, c.resurfacing_score DESC, c.resurfacing_rank ASC, c.paper_id ASC
        """,
        (args_global["diamond_score_run_id"], run_id),
    ).fetchall()
    items = []
    for row in rows:
        rationale = json.loads(row["rationale_json"] or "{}")
        items.append(
            {
                "batch_item_id": f"stranded_qfin:{row['paper_id']}",
                "lane_family": "stranded_qfin",
                "operator_family": "stranded_qfin",
                "source_kind": "stranded_resurfacing_candidate",
                "source_run_id": run_id,
                "source_ref": row["paper_id"],
                "family_rank": int(row["resurfacing_rank"]),
                "source_score": round(float(row["resurfacing_score"] or 0.0), 6),
                "diamond_score": round(float(row["diamond_score"] or 0.0), 6),
                "packet_title": f"Stranded q-fin packet: {row['title']}",
                "packet_summary": {
                    "paper_id": row["paper_id"],
                    "rationale": rationale,
                },
                "packet_markdown": "\n".join(
                    [
                        f"# Stranded q-fin packet: {row['title']}",
                        "",
                        f"- paper id: `{row['paper_id']}`",
                        f"- resurfacing score: `{round(float(row['resurfacing_score'] or 0.0), 6)}`",
                        "",
                        row["abstract"] or "",
                    ]
                ).strip()
                + "\n",
            }
        )
    return items


def build_lane_candidates(connection: sqlite3.Connection, args) -> dict[str, list[dict]]:
    lane_candidates = {
        "market_design": [],
        "settlement_resolution": [],
        "participant_pathologies": fetch_paper_operator_items(
            connection,
            "participant_pathologies",
            "participant_pathology",
            "participant_pathology_candidates",
            "participant_pathology_candidate_score",
            "participant_pathology_rank",
            args.participant_run_id,
        ),
        "state_graph": fetch_paper_operator_items(
            connection,
            "state_graph",
            "state_graph",
            "state_graph_candidates",
            "state_graph_candidate_score",
            "state_graph_rank",
            args.state_graph_run_id,
        ),
        "stranded_qfin": fetch_stranded_items(connection, args.stranded_run_id),
        "transition_state": fetch_transition_items(connection, args.transition_run_id),
    }
    for lane_family, anchor_id in LANE_ANCHOR_IDS.items():
        lane_candidates[lane_family].extend(
            fetch_pair_lane_items(
                connection,
                lane_family,
                anchor_id,
                "bridge_candidates",
                "bridge_score",
                "bridge_rank",
                args.bridge_run_id,
            )
        )
        lane_candidates[lane_family].extend(
            fetch_pair_lane_items(
                connection,
                lane_family,
                anchor_id,
                "composition_candidates",
                "composition_score",
                "composition_rank",
                args.composition_run_id,
            )
        )
    for lane_family, items in lane_candidates.items():
        items.sort(
            key=lambda item: (
                -float(item["diamond_score"]),
                -float(item["source_score"]),
                item["batch_item_id"],
            )
        )
    return lane_candidates


def select_items(lane_candidates: dict[str, list[dict]], lane_quota: int, overall_limit: int) -> list[dict]:
    selected: list[dict] = []
    selected_ids: set[str] = set()
    # @context decision -- S32 must not let the transition-state-heavy global score collapse the
    # shortlist back into one dominant workstream. The lane quota is the actual shortlist gate: it
    # guarantees six-lane coverage first, then fills remaining slots by unified rank.
    for lane_family in CANONICAL_LANES:
        lane_selected = 0
        for candidate in lane_candidates.get(lane_family, []):
            if candidate["batch_item_id"] in selected_ids:
                continue
            selected.append({**candidate, "selection_bucket": "lane_quota"})
            selected_ids.add(candidate["batch_item_id"])
            lane_selected += 1
            if lane_selected >= lane_quota:
                break
    overflow = sorted(
        [item for lane in CANONICAL_LANES for item in lane_candidates.get(lane, []) if item["batch_item_id"] not in selected_ids],
        key=lambda item: (
            -float(item["diamond_score"]),
            -float(item["source_score"]),
            item["batch_item_id"],
        ),
    )
    for candidate in overflow:
        if len(selected) >= overall_limit:
            break
        selected.append({**candidate, "selection_bucket": "overall_topup"})
        selected_ids.add(candidate["batch_item_id"])
    selected.sort(
        key=lambda item: (
            0 if item["selection_bucket"] == "lane_quota" else 1,
            CANONICAL_LANES.index(item["lane_family"]) if item["lane_family"] in CANONICAL_LANES else 99,
            -float(item["diamond_score"]),
            -float(item["source_score"]),
            item["batch_item_id"],
        )
    )
    for rank, item in enumerate(selected, start=1):
        item["shortlist_rank"] = rank
    return selected


args_global: dict[str, str] = {}


def main():
    args = parse_args()
    global args_global
    args_global = {"diamond_score_run_id": args.diamond_score_run_id}
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
            "diamond_interpretation",
            "started",
            {
                "diamond_score_run_id": args.diamond_score_run_id,
                "bridge_run_id": args.bridge_run_id,
                "composition_run_id": args.composition_run_id,
                "stranded_run_id": args.stranded_run_id,
                "transition_run_id": args.transition_run_id,
                "state_graph_run_id": args.state_graph_run_id,
                "participant_run_id": args.participant_run_id,
                "lane_quota": args.lane_quota,
                "overall_limit": args.overall_limit,
                "prompt_path": str(prompt_path),
                "schema_path": str(schema_path),
            },
        )
        lane_candidates = build_lane_candidates(connection, args)
        selected = select_items(lane_candidates, args.lane_quota, args.overall_limit)

        batch_items = []
        counts_by_lane: dict[str, int] = {}
        counts_by_operator_family: dict[str, int] = {}
        counts_by_bucket: dict[str, int] = {}
        for item in selected:
            counts_by_lane[item["lane_family"]] = counts_by_lane.get(item["lane_family"], 0) + 1
            counts_by_operator_family[item["operator_family"]] = counts_by_operator_family.get(item["operator_family"], 0) + 1
            counts_by_bucket[item["selection_bucket"]] = counts_by_bucket.get(item["selection_bucket"], 0) + 1
            batch_items.append(
                {
                    **item,
                    "schema_required_fields": schema.get("required", []),
                    "prompt_path": str(prompt_path),
                    "schema_path": str(schema_path),
                    "prompt_text": prompt_text,
                }
            )

        batch_path = output_dir / "diamond_interpretation_batch.jsonl"
        with batch_path.open("w", encoding="utf-8") as handle:
            for item in batch_items:
                handle.write(json.dumps(item, sort_keys=True) + "\n")

        metrics = {
            "run_id": args.run_id,
            "diamond_score_run_id": args.diamond_score_run_id,
            "prepared_count": len(batch_items),
            "counts_by_lane": counts_by_lane,
            "counts_by_operator_family": counts_by_operator_family,
            "counts_by_selection_bucket": counts_by_bucket,
            "lane_quota": args.lane_quota,
            "overall_limit": args.overall_limit,
            "prompt_path": str(prompt_path),
            "schema_path": str(schema_path),
        }
        metrics_path = output_dir / "diamond_interpretation_batch_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(connection, args.run_id, "diamond_interpretation", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
