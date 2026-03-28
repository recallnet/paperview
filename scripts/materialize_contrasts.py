#!/usr/bin/env python3

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical paper-level contrast candidates from probe hits.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="contrast-materialization-20260328")
    parser.add_argument("--probe-run-id", default="probe-materialization-20260328")
    parser.add_argument("--stranding-run-id", default="stranding-score-materialization-20260328")
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


def fetch_stranding_scores(connection: sqlite3.Connection, stranding_run_id: str) -> dict[str, float]:
    rows = connection.execute(
        """
        SELECT paper_id, stranding_score
        FROM stranding_scores
        WHERE run_id = ?
        """,
        (stranding_run_id,),
    ).fetchall()
    return {row["paper_id"]: float(row["stranding_score"]) for row in rows}


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        log_run_event(
            connection,
            args.run_id,
            "contrast",
            "started",
            {
                "probe_run_id": args.probe_run_id,
                "stranding_run_id": args.stranding_run_id,
                "top_k": args.top_k,
            },
        )
        stranding_scores = fetch_stranding_scores(connection, args.stranding_run_id)
        connection.execute("DELETE FROM contrast_candidates WHERE run_id = ?", (args.run_id,))

        rows = connection.execute(
            """
            SELECT
              ph.pattern_id,
              ph.view_id,
              ph.score,
              ap.label AS pattern_label,
              ap.kind AS pattern_kind,
              ap.positive_tags_json,
              ap.negative_tags_json,
              tv.paper_id,
              p.primary_category,
              p.published_at
            FROM probe_hits ph
            JOIN agitator_patterns ap
              ON ap.pattern_id = ph.pattern_id
            JOIN text_views tv
              ON tv.view_id = ph.view_id
            JOIN papers p
              ON p.paper_id = tv.paper_id
            WHERE ph.run_id = ?
              AND ap.kind = 'contrast'
            ORDER BY ph.pattern_id, ph.score DESC, tv.paper_id
            """,
            (args.probe_run_id,),
        ).fetchall()

        grouped = defaultdict(list)
        for row in rows:
            grouped[row["pattern_id"]].append(row)

        contrast_rows = []
        preview_rows = []
        for pattern_id, pattern_rows in grouped.items():
            best_by_paper = {}
            for row in pattern_rows:
                current = best_by_paper.get(row["paper_id"])
                if current is None or float(row["score"]) > float(current["score"]):
                    best_by_paper[row["paper_id"]] = row

            ranked = sorted(
                best_by_paper.values(),
                key=lambda item: (-float(item["score"]), item["paper_id"]),
            )[: args.top_k]

            for rank, row in enumerate(ranked, start=1):
                rationale = {
                    "pattern_label": row["pattern_label"],
                    "pattern_kind": row["pattern_kind"],
                    "positive_tags": json.loads(row["positive_tags_json"]),
                    "negative_tags": json.loads(row["negative_tags_json"]),
                    "stranding_score": round(stranding_scores.get(row["paper_id"], 0.0), 6),
                    "primary_category": row["primary_category"],
                    "published_at": row["published_at"],
                }
                contrast_rows.append(
                    (
                        args.run_id,
                        pattern_id,
                        row["paper_id"],
                        row["view_id"],
                        float(row["score"]),
                        rank,
                        json.dumps(rationale, sort_keys=True),
                    )
                )
                preview_rows.append(
                    {
                        "run_id": args.run_id,
                        "pattern_id": pattern_id,
                        "paper_id": row["paper_id"],
                        "contrast_score": round(float(row["score"]), 6),
                        "contrast_rank": rank,
                    }
                )

        # @context requirement -- Contrast candidates are a paper-level projection of contrast-kind
        # probe hits, not a second hidden retrieval stack. Reusing probe output keeps S09 staged and
        # queryable while preserving the same near-A / far-B semantics already encoded in probes.
        connection.executemany(
            """
            INSERT INTO contrast_candidates (
              run_id,
              pattern_id,
              paper_id,
              representative_view_id,
              contrast_score,
              contrast_rank,
              rationale_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            contrast_rows,
        )

        metrics = {
            "run_id": args.run_id,
            "probe_run_id": args.probe_run_id,
            "stranding_run_id": args.stranding_run_id,
            "contrast_pattern_count": len(grouped),
            "contrast_candidate_count": len(contrast_rows),
            "patterns_with_candidates": sum(1 for rows in grouped.values() if rows),
            "top_k": args.top_k,
            "top_score": max((row["contrast_score"] for row in preview_rows), default=0.0),
        }
        metrics_path = output_dir / "contrast_metrics.json"
        preview_path = output_dir / "contrasts.jsonl"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        preview_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in preview_rows),
            encoding="utf-8",
        )
        log_run_event(
            connection,
            args.run_id,
            "contrast",
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
