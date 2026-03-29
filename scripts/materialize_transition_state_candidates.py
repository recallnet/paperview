#!/usr/bin/env python3

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"

TRANSITION_PATTERN_IDS = (
    "near_transition_queue_refill",
    "near_transition_auction_refill",
    "near_transition_auction_queue",
    "near_transition_maker_queue",
    "near_transition_parity_repair",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical transition-state candidates from live scores and probe hits.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="transition-state-candidate-materialization-20260328")
    parser.add_argument("--score-run-id", default="transition-state-score-materialization-20260328")
    parser.add_argument("--probe-run-id", default="probe-materialization-20260328-transition-state")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--top-k", type=int, default=20)
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def ensure_transition_state_candidates_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS transition_state_candidates (
          run_id TEXT NOT NULL,
          pattern_id TEXT NOT NULL,
          paper_id TEXT NOT NULL,
          representative_view_id INTEGER,
          transition_state_candidate_score REAL NOT NULL,
          transition_state_rank INTEGER NOT NULL,
          rationale_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, pattern_id, paper_id),
          FOREIGN KEY (pattern_id) REFERENCES agitator_patterns(pattern_id) ON DELETE CASCADE,
          FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
          FOREIGN KEY (representative_view_id) REFERENCES text_views(view_id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_transition_state_candidates_run_pattern_rank
        ON transition_state_candidates(run_id, pattern_id, transition_state_rank)
        """
    )


def fetch_pattern_rows(connection: sqlite3.Connection, score_run_id: str, probe_run_id: str) -> dict[str, list[sqlite3.Row]]:
    placeholders = ",".join("?" for _ in TRANSITION_PATTERN_IDS)
    rows = connection.execute(
        f"""
        SELECT
          ph.pattern_id,
          ph.view_id,
          ph.score AS probe_score,
          ph.rank AS probe_rank,
          ap.label AS pattern_label,
          tv.paper_id,
          ts.transition_state_score,
          ts.family_count,
          ts.feature_json,
          p.primary_category,
          p.published_at
        FROM probe_hits ph
        JOIN agitator_patterns ap
          ON ap.pattern_id = ph.pattern_id
        JOIN text_views tv
          ON tv.view_id = ph.view_id
        JOIN transition_state_scores ts
          ON ts.paper_id = tv.paper_id
         AND ts.run_id = ?
        JOIN papers p
          ON p.paper_id = tv.paper_id
        WHERE ph.run_id = ?
          AND ph.pattern_id IN ({placeholders})
        ORDER BY ph.pattern_id, ph.score DESC, ts.transition_state_score DESC, tv.paper_id
        """,
        (score_run_id, probe_run_id, *TRANSITION_PATTERN_IDS),
    ).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["pattern_id"]].append(row)
    return grouped


def candidate_score(transition_state_score: float, probe_score: float, family_count: int) -> float:
    family_bonus = min(0.15, 0.03 * max(0, family_count - 1))
    return (0.65 * float(transition_state_score)) + (0.35 * (float(probe_score) / (1.0 + float(probe_score)))) + family_bonus


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_transition_state_candidates_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "transition_state_candidate",
            "started",
            {
                "score_run_id": args.score_run_id,
                "probe_run_id": args.probe_run_id,
                "top_k": args.top_k,
            },
        )
        connection.execute("DELETE FROM transition_state_candidates WHERE run_id = ?", (args.run_id,))

        grouped = fetch_pattern_rows(connection, args.score_run_id, args.probe_run_id)
        candidate_rows = []
        preview_rows = []
        for pattern_id, rows in grouped.items():
            best_by_paper = {}
            for row in rows:
                score = candidate_score(row["transition_state_score"], row["probe_score"], row["family_count"])
                current = best_by_paper.get(row["paper_id"])
                payload = {
                    "pattern_id": pattern_id,
                    "paper_id": row["paper_id"],
                    "view_id": row["view_id"],
                    "candidate_score": score,
                    "probe_score": float(row["probe_score"]),
                    "probe_rank": int(row["probe_rank"]),
                    "transition_state_score": float(row["transition_state_score"]),
                    "family_count": int(row["family_count"]),
                    "pattern_label": row["pattern_label"],
                    "primary_category": row["primary_category"],
                    "published_at": row["published_at"],
                    "feature_json": json.loads(row["feature_json"]),
                }
                if current is None or payload["candidate_score"] > current["candidate_score"]:
                    best_by_paper[row["paper_id"]] = payload

            ranked = sorted(
                best_by_paper.values(),
                key=lambda item: (-item["candidate_score"], -item["transition_state_score"], item["paper_id"]),
            )[: args.top_k]

            for rank, item in enumerate(ranked, start=1):
                rationale = {
                    "pattern_label": item["pattern_label"],
                    "probe_score": round(item["probe_score"], 6),
                    "probe_rank": item["probe_rank"],
                    "transition_state_score": round(item["transition_state_score"], 6),
                    "family_count": item["family_count"],
                    "primary_category": item["primary_category"],
                    "published_at": item["published_at"],
                    "feature_snapshot": item["feature_json"],
                }
                # @context requirement -- S19 must stay grounded in the live S17/S18 map surfaces.
                # The operator therefore ranks only papers with transition-state probe support and
                # uses the paper-level S18 score as a reusable prior, rather than falling back to a
                # new keyword-only search path that would violate the plan's map-first contract.
                candidate_rows.append(
                    (
                        args.run_id,
                        pattern_id,
                        item["paper_id"],
                        item["view_id"],
                        item["candidate_score"],
                        rank,
                        json.dumps(rationale, sort_keys=True),
                    )
                )
                preview_rows.append(
                    {
                        "run_id": args.run_id,
                        "pattern_id": pattern_id,
                        "paper_id": item["paper_id"],
                        "transition_state_candidate_score": round(item["candidate_score"], 6),
                        "transition_state_rank": rank,
                    }
                )

        connection.executemany(
            """
            INSERT INTO transition_state_candidates (
              run_id,
              pattern_id,
              paper_id,
              representative_view_id,
              transition_state_candidate_score,
              transition_state_rank,
              rationale_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            candidate_rows,
        )

        metrics = {
            "run_id": args.run_id,
            "score_run_id": args.score_run_id,
            "probe_run_id": args.probe_run_id,
            "transition_pattern_count": len(grouped),
            "transition_candidate_count": len(candidate_rows),
            "patterns_with_candidates": sum(1 for rows in grouped.values() if rows),
            "top_k": args.top_k,
            "top_score": max((row["transition_state_candidate_score"] for row in preview_rows), default=0.0),
        }
        metrics_path = output_dir / "transition_state_candidate_metrics.json"
        preview_path = output_dir / "transition_state_candidates.jsonl"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        preview_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in preview_rows),
            encoding="utf-8",
        )
        log_run_event(
            connection,
            args.run_id,
            "transition_state_candidate",
            "completed",
            {
                **metrics,
                "metrics_path": str(metrics_path),
                "preview_path": str(preview_path),
            },
        )
        connection.commit()
    finally:
        connection.close()

    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
