#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical stranded q-fin resurfacing candidates.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="stranded-resurfacing-materialization-20260328")
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--stranding-run-id", default="stranding-score-materialization-20260328")
    parser.add_argument("--transition-score-run-id", default="transition-state-score-materialization-20260328")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--top-k", type=int, default=50)
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def ensure_stranded_resurfacing_candidates_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS stranded_resurfacing_candidates (
          run_id TEXT NOT NULL,
          paper_id TEXT NOT NULL,
          resurfacing_score REAL NOT NULL,
          resurfacing_rank INTEGER NOT NULL,
          membership_run_id TEXT NOT NULL,
          stranding_run_id TEXT NOT NULL,
          transition_score_run_id TEXT NOT NULL,
          rationale_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, paper_id),
          FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_stranded_resurfacing_candidates_run_rank
        ON stranded_resurfacing_candidates(run_id, resurfacing_rank)
        """
    )


def year_fraction(published_at: str | None) -> float:
    if not published_at:
        return 0.0
    try:
        year = int(str(published_at)[:4])
    except ValueError:
        return 0.0
    if year < 2015 or year > 2023:
        return 0.0
    return (year - 2015) / 8.0


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_stranded_resurfacing_candidates_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "stranded_resurfacing",
            "started",
            {
                "membership_run_id": args.membership_run_id,
                "stranding_run_id": args.stranding_run_id,
                "transition_score_run_id": args.transition_score_run_id,
                "top_k": args.top_k,
            },
        )
        connection.execute("DELETE FROM stranded_resurfacing_candidates WHERE run_id = ?", (args.run_id,))

        rows = connection.execute(
            """
            SELECT
              s.paper_id,
              s.stranding_score,
              s.result_specificity_score,
              s.survey_penalty_score,
              s.empirical_only_penalty_score,
              s.feature_json AS stranding_feature_json,
              p.primary_category,
              p.published_at,
              COALESCE(ts.transition_state_score, 0.0) AS transition_state_score,
              MAX(CASE WHEN cm.corpus_id = 'realized_market' THEN 1 ELSE 0 END) AS realized_market_flag,
              MAX(CASE WHEN cm.corpus_id = 'stranded_alpha' THEN 1 ELSE 0 END) AS stranded_alpha_flag
            FROM stranding_scores s
            JOIN papers p
              ON p.paper_id = s.paper_id
            JOIN corpus_memberships cm
              ON cm.paper_id = s.paper_id
             AND cm.run_id = ?
            LEFT JOIN transition_state_scores ts
              ON ts.paper_id = s.paper_id
             AND ts.run_id = ?
            WHERE s.run_id = ?
            GROUP BY
              s.paper_id,
              s.stranding_score,
              s.result_specificity_score,
              s.survey_penalty_score,
              s.empirical_only_penalty_score,
              s.feature_json,
              p.primary_category,
              p.published_at,
              ts.transition_state_score
            ORDER BY s.stranding_score DESC, p.published_at ASC, s.paper_id ASC
            """,
            (args.membership_run_id, args.transition_score_run_id, args.stranding_run_id),
        ).fetchall()

        ranked_rows = []
        for row in rows:
            if not row["stranded_alpha_flag"]:
                continue
            if not str(row["primary_category"] or "").startswith("q-fin"):
                continue
            recency_score = year_fraction(row["published_at"])
            if recency_score == 0.0:
                continue
            realized_leakage_penalty = 1.0 if row["realized_market_flag"] else 0.0
            venue_closeness_score = min(1.0, 0.7 * float(row["transition_state_score"]) + 0.3 * recency_score)
            penalty_relief_score = max(
                0.0,
                1.0 - (0.5 * float(row["survey_penalty_score"]) + 0.5 * float(row["empirical_only_penalty_score"])),
            )
            # @context decision -- S20 must be distinct from the general stranding scorer. It only
            # ranks the time-firewalled stranded-alpha q-fin slice and adds operator-specific terms
            # for modern-venue closeness, penalty relief, and realized-market leakage so the output
            # is a practical resurfacing queue rather than a copy of the S08 sparse prior.
            resurfacing_score = max(
                0.0,
                (0.5 * float(row["stranding_score"]))
                + (0.2 * float(row["result_specificity_score"]))
                + (0.2 * venue_closeness_score)
                + (0.1 * penalty_relief_score)
                - (0.2 * realized_leakage_penalty),
            )
            ranked_rows.append(
                {
                    "paper_id": row["paper_id"],
                    "resurfacing_score": resurfacing_score,
                    "stranding_score": float(row["stranding_score"]),
                    "result_specificity_score": float(row["result_specificity_score"]),
                    "survey_penalty_score": float(row["survey_penalty_score"]),
                    "empirical_only_penalty_score": float(row["empirical_only_penalty_score"]),
                    "transition_state_score": float(row["transition_state_score"]),
                    "venue_closeness_score": venue_closeness_score,
                    "recency_score": recency_score,
                    "realized_market_flag": int(realized_leakage_penalty),
                    "primary_category": row["primary_category"],
                    "published_at": row["published_at"],
                    "stranding_feature_json": json.loads(row["stranding_feature_json"]),
                }
            )

        ranked_rows.sort(key=lambda item: (-item["resurfacing_score"], -item["stranding_score"], item["paper_id"]))
        ranked_rows = ranked_rows[: args.top_k]

        jsonl_rows = []
        for rank, row in enumerate(ranked_rows, start=1):
            rationale = {
                "stranding_score": round(row["stranding_score"], 6),
                "result_specificity_score": round(row["result_specificity_score"], 6),
                "transition_state_score": round(row["transition_state_score"], 6),
                "venue_closeness_score": round(row["venue_closeness_score"], 6),
                "recency_score": round(row["recency_score"], 6),
                "realized_market_flag": row["realized_market_flag"],
                "survey_penalty_score": round(row["survey_penalty_score"], 6),
                "empirical_only_penalty_score": round(row["empirical_only_penalty_score"], 6),
                "primary_category": row["primary_category"],
                "published_at": row["published_at"],
                "stranding_feature_snapshot": row["stranding_feature_json"],
            }
            connection.execute(
                """
                INSERT INTO stranded_resurfacing_candidates (
                  run_id,
                  paper_id,
                  resurfacing_score,
                  resurfacing_rank,
                  membership_run_id,
                  stranding_run_id,
                  transition_score_run_id,
                  rationale_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.run_id,
                    row["paper_id"],
                    row["resurfacing_score"],
                    rank,
                    args.membership_run_id,
                    args.stranding_run_id,
                    args.transition_score_run_id,
                    json.dumps(rationale, sort_keys=True),
                ),
            )
            jsonl_rows.append(
                {
                    "paper_id": row["paper_id"],
                    "resurfacing_score": round(row["resurfacing_score"], 6),
                    "resurfacing_rank": rank,
                    "rationale": rationale,
                }
            )

        preview_path = output_dir / "stranded_resurfacing_candidates.jsonl"
        preview_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in jsonl_rows),
            encoding="utf-8",
        )
        metrics = {
            "run_id": args.run_id,
            "membership_run_id": args.membership_run_id,
            "stranding_run_id": args.stranding_run_id,
            "transition_score_run_id": args.transition_score_run_id,
            "candidate_count": len(jsonl_rows),
            "top_score": max((row["resurfacing_score"] for row in jsonl_rows), default=0.0),
            "top_ranked_paper_id": jsonl_rows[0]["paper_id"] if jsonl_rows else None,
        }
        metrics_path = output_dir / "stranded_resurfacing_candidate_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(
            connection,
            args.run_id,
            "stranded_resurfacing",
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
