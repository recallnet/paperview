#!/usr/bin/env python3

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"

STATE_GRAPH_PATTERN_IDS = (
    "near_state_graph_far_realized",
    "near_transition_parity_repair",
)
STATE_GRAPH_ANCHOR_IDS = {
    "state_graph_inconsistencies",
    "parity_propagation",
    "parity_propagation_delayed_repair",
    "settlement_resolution_seams",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical state-graph candidates from unified diamond scores.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="state-graph-candidate-materialization-20260329")
    parser.add_argument("--diamond-score-run-id", default="diamond-score-materialization-20260329")
    parser.add_argument("--probe-run-id", default="probe-materialization-20260328-broadened")
    parser.add_argument("--bridge-run-id", default="bridge-materialization-20260328-broadened")
    parser.add_argument("--composition-run-id", default="composition-materialization-20260328-broadened")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--top-k", type=int, default=25)
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def ensure_state_graph_candidates_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS state_graph_candidates (
          run_id TEXT NOT NULL,
          paper_id TEXT NOT NULL,
          representative_view_id INTEGER,
          state_graph_candidate_score REAL NOT NULL,
          state_graph_rank INTEGER NOT NULL,
          diamond_score_run_id TEXT NOT NULL,
          probe_run_id TEXT NOT NULL,
          bridge_run_id TEXT NOT NULL,
          composition_run_id TEXT NOT NULL,
          rationale_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, paper_id),
          FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
          FOREIGN KEY (representative_view_id) REFERENCES text_views(view_id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_state_graph_candidates_run_rank
        ON state_graph_candidates(run_id, state_graph_rank)
        """
    )


def fetch_probe_support(connection: sqlite3.Connection, probe_run_id: str) -> dict[str, dict]:
    placeholders = ",".join("?" for _ in STATE_GRAPH_PATTERN_IDS)
    rows = connection.execute(
        f"""
        SELECT
          tv.paper_id,
          ph.view_id,
          ph.pattern_id,
          ph.score,
          ph.rank,
          ap.label AS pattern_label
        FROM probe_hits ph
        JOIN text_views tv
          ON tv.view_id = ph.view_id
        JOIN agitator_patterns ap
          ON ap.pattern_id = ph.pattern_id
        WHERE ph.run_id = ?
          AND ph.pattern_id IN ({placeholders})
        ORDER BY tv.paper_id, ph.score DESC, ph.rank ASC
        """,
        (probe_run_id, *STATE_GRAPH_PATTERN_IDS),
    ).fetchall()
    best_by_paper = {}
    for row in rows:
        current = best_by_paper.get(row["paper_id"])
        payload = {
            "view_id": row["view_id"],
            "pattern_id": row["pattern_id"],
            "pattern_label": row["pattern_label"],
            "probe_score": float(row["score"]),
            "probe_rank": int(row["rank"]),
        }
        if current is None or payload["probe_score"] > current["probe_score"]:
            best_by_paper[row["paper_id"]] = payload
    return best_by_paper


def fetch_operator_support(
    connection: sqlite3.Connection,
    table_name: str,
    run_id: str,
    score_column: str,
) -> dict[str, dict]:
    rows = connection.execute(
        f"""
        SELECT source_anchor_id, target_anchor_id, paper_id, {score_column} AS score
        FROM {table_name}
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    support = {}
    for row in rows:
        anchor_pair = {row["source_anchor_id"], row["target_anchor_id"]}
        if not anchor_pair.intersection(STATE_GRAPH_ANCHOR_IDS):
            continue
        payload = {
            "score": float(row["score"] or 0.0),
            "anchor_pair": sorted(anchor_pair),
        }
        current = support.get(row["paper_id"])
        if current is None or payload["score"] > current["score"]:
            support[row["paper_id"]] = payload
    return support


def normalized_probe_score(raw_score: float) -> float:
    raw_score = max(0.0, raw_score)
    if raw_score == 0:
        return 0.0
    return raw_score / (1.0 + raw_score)


def normalized_operator_score(raw_score: float, source_kind: str) -> float:
    scale = 2.5 if source_kind == "bridge" else 3.0
    return min(1.0, max(0.0, raw_score) / scale)


def candidate_score(diamond_score: float, probe_score: float, bridge_score: float, composition_score: float) -> float:
    support_count = sum(1 for value in (probe_score, bridge_score, composition_score) if value > 0)
    support_bonus = min(0.12, 0.04 * max(0, support_count - 1))
    # @context requirement -- The dedicated state-graph operator must remain map-first. It ranks
    # only papers that already have unified diamond support and lane-relevant probe or
    # bridge/composition evidence, so later stages consume a stable operator surface instead of
    # reopening raw lexical search for linked-market inconsistency ideas.
    return (0.55 * diamond_score) + (0.20 * probe_score) + (0.15 * bridge_score) + (0.10 * composition_score) + support_bonus


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_state_graph_candidates_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "state_graph_candidate",
            "started",
            {
                "diamond_score_run_id": args.diamond_score_run_id,
                "probe_run_id": args.probe_run_id,
                "bridge_run_id": args.bridge_run_id,
                "composition_run_id": args.composition_run_id,
                "top_k": args.top_k,
            },
        )
        connection.execute("DELETE FROM state_graph_candidates WHERE run_id = ?", (args.run_id,))

        probe_support = fetch_probe_support(connection, args.probe_run_id)
        bridge_support = fetch_operator_support(connection, "bridge_candidates", args.bridge_run_id, "bridge_score")
        composition_support = fetch_operator_support(
            connection, "composition_candidates", args.composition_run_id, "composition_score"
        )
        rows = connection.execute(
            """
            SELECT paper_id, diamond_score, top_lane, top_lane_score, feature_json
            FROM diamond_scores
            WHERE run_id = ?
            ORDER BY diamond_score DESC, paper_id
            """,
            (args.diamond_score_run_id,),
        ).fetchall()

        ranked = []
        for row in rows:
            paper_id = row["paper_id"]
            probe_payload = probe_support.get(paper_id)
            bridge_payload = bridge_support.get(paper_id)
            composition_payload = composition_support.get(paper_id)
            if probe_payload is None and bridge_payload is None and composition_payload is None:
                continue
            state_graph_lane_score = json.loads(row["feature_json"] or "{}").get("lane_scores", {}).get("state_graph", 0.0)
            if row["top_lane"] != "state_graph" and state_graph_lane_score <= 0.05:
                continue
            ranked.append(
                {
                    "paper_id": paper_id,
                    "diamond_score": float(row["diamond_score"]),
                    "top_lane": row["top_lane"],
                    "top_lane_score": float(row["top_lane_score"]),
                    "state_graph_lane_score": float(state_graph_lane_score),
                    "probe_payload": probe_payload,
                    "bridge_payload": bridge_payload,
                    "composition_payload": composition_payload,
                    "candidate_score": candidate_score(
                        float(row["diamond_score"]),
                        normalized_probe_score(float((probe_payload or {}).get("probe_score", 0.0))),
                        normalized_operator_score(float((bridge_payload or {}).get("score", 0.0)), "bridge"),
                        normalized_operator_score(float((composition_payload or {}).get("score", 0.0)), "composition"),
                    ),
                }
            )

        ranked.sort(key=lambda item: (-item["candidate_score"], -item["diamond_score"], item["paper_id"]))
        ranked = ranked[: args.top_k]

        jsonl_rows = []
        for rank, item in enumerate(ranked, start=1):
            representative_view_id = (item["probe_payload"] or {}).get("view_id")
            rationale = {
                "diamond_score": round(item["diamond_score"], 6),
                "top_lane": item["top_lane"],
                "top_lane_score": round(item["top_lane_score"], 6),
                "state_graph_lane_score": round(item["state_graph_lane_score"], 6),
                "probe_support": item["probe_payload"],
                "bridge_support": item["bridge_payload"],
                "composition_support": item["composition_payload"],
            }
            connection.execute(
                """
                INSERT INTO state_graph_candidates (
                  run_id, paper_id, representative_view_id, state_graph_candidate_score, state_graph_rank,
                  diamond_score_run_id, probe_run_id, bridge_run_id, composition_run_id, rationale_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.run_id,
                    item["paper_id"],
                    representative_view_id,
                    item["candidate_score"],
                    rank,
                    args.diamond_score_run_id,
                    args.probe_run_id,
                    args.bridge_run_id,
                    args.composition_run_id,
                    json.dumps(rationale, sort_keys=True),
                ),
            )
            jsonl_rows.append(
                {
                    "paper_id": item["paper_id"],
                    "state_graph_candidate_score": round(item["candidate_score"], 6),
                    "state_graph_rank": rank,
                    "rationale": rationale,
                }
            )

        preview_path = output_dir / "state_graph_candidates.jsonl"
        preview_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in jsonl_rows), encoding="utf-8")
        metrics = {
            "run_id": args.run_id,
            "candidate_count": len(jsonl_rows),
            "top_score": max((row["state_graph_candidate_score"] for row in jsonl_rows), default=0.0),
            "top_ranked_paper_id": jsonl_rows[0]["paper_id"] if jsonl_rows else None,
            "probe_supported_count": sum(1 for row in ranked if row["probe_payload"] is not None),
            "bridge_supported_count": sum(1 for row in ranked if row["bridge_payload"] is not None),
            "composition_supported_count": sum(1 for row in ranked if row["composition_payload"] is not None),
        }
        metrics_path = output_dir / "state_graph_candidate_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(
            connection,
            args.run_id,
            "state_graph_candidate",
            "completed",
            {**metrics, "metrics_path": str(metrics_path), "preview_path": str(preview_path)},
        )
        connection.commit()
    finally:
        connection.close()

    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
