#!/usr/bin/env python3

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Assess whether a live brief queue is ready for analyst time or should wait for richer extraction output."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--run-prefix",
        required=True,
        help="Run prefix used by materialize_live_downstream_run.py.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory for the assessment report.",
    )
    return parser.parse_args()


def parse_json_object(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {}


def load_briefs(connection, brief_run_id: str):
    connection.row_factory = sqlite3.Row
    return connection.execute(
        """
        SELECT strategy_brief_id, brief_name, brief_status, brief_rank, brief_json
        FROM strategy_briefs
        WHERE run_id = ?
        ORDER BY brief_rank
        """,
        (brief_run_id,),
    ).fetchall()


def load_ranking_summary(connection, ranking_run_id: str):
    connection.row_factory = sqlite3.Row
    return connection.execute(
        """
        SELECT family_rank, gate_status, final_priority_score, rationale_json
        FROM candidate_family_rankings
        WHERE run_id = ?
        ORDER BY family_rank
        """,
        (ranking_run_id,),
    ).fetchall()


def load_queryless_summary(connection, queryless_run_id: str):
    connection.row_factory = sqlite3.Row
    return connection.execute(
        """
        SELECT
          count(*) AS hit_count,
          sum(is_cross_family) AS cross_family_hit_count,
          sum(case when candidate_evaluation_split = 'holdout' then 1 else 0 end) AS holdout_hit_count,
          avg(lexical_distance_score) AS avg_lexical_distance_score,
          avg(structural_similarity_score) AS avg_structural_similarity_score
        FROM queryless_candidate_hits
        WHERE run_id = ?
        """,
        (queryless_run_id,),
    ).fetchone()


def load_target_domain_counts(connection, brief_run_id: str):
    rows = connection.execute(
        """
        SELECT json_extract(brief_json, '$.target_domain') AS target_domain, count(*)
        FROM strategy_briefs
        WHERE run_id = ?
        GROUP BY json_extract(brief_json, '$.target_domain')
        ORDER BY count(*) DESC, target_domain
        """,
        (brief_run_id,),
    ).fetchall()
    return {row[0] or "unknown": row[1] for row in rows}


def derive_recommendation(summary):
    reasons = []
    if summary["brief_count"] == 0:
        return "wait_for_richer_extractions", ["no live briefs exist"]
    if summary["passed_family_count"] == 0:
        reasons.append("no candidate families passed C13 hard gates")
    if summary["provisional_brief_count"] == summary["brief_count"]:
        reasons.append("all available briefs are provisional analyst-triage packets")
    if summary["distinct_target_domain_count"] <= 1:
        reasons.append("queue is concentrated in a single target domain")
    if summary["cross_family_hit_count"] == 0:
        reasons.append("queryless mining produced no cross-family hits in the live slice")
    if summary["holdout_hit_count"] == 0:
        reasons.append("queryless mining produced no holdout hits in the live slice")
    if summary["dominant_dead_end_family"]:
        reasons.append("top-ranked family is still a research-dead-end bucket")

    # @context decision -- The first live legacy slice should only consume real
    # analyst time when it shows at least one sign of genuine transfer promise:
    # a passed family, cross-family evidence, or holdout coverage. Otherwise the
    # right call is to wait for richer mixed-family extraction output instead of
    # burning review cycles on same-family provisional packets.
    if (
        summary["passed_family_count"] == 0
        and summary["cross_family_hit_count"] == 0
        and summary["holdout_hit_count"] == 0
    ):
        return "wait_for_richer_extractions", reasons
    return "review_now", reasons


def build_summary(run_prefix: str, briefs, ranking_rows, queryless_row, target_domain_counts):
    provisional_brief_count = sum(
        1 for brief in briefs if brief["brief_status"] == "provisional_drafted"
    )
    passed_family_count = sum(1 for row in ranking_rows if row["gate_status"] == "passed")
    dominant_dead_end_family = False
    if ranking_rows:
        top_rationale = parse_json_object(ranking_rows[0]["rationale_json"])
        dominant_dead_end_family = (
            ranking_rows[0]["gate_status"] != "passed"
            and bool(top_rationale)
            and ranking_rows[0]["family_rank"] == 1
        )

    summary = {
        "run_prefix": run_prefix,
        "brief_count": len(briefs),
        "provisional_brief_count": provisional_brief_count,
        "passed_family_count": passed_family_count,
        "cross_family_hit_count": int(queryless_row["cross_family_hit_count"] or 0),
        "holdout_hit_count": int(queryless_row["holdout_hit_count"] or 0),
        "avg_lexical_distance_score": round(queryless_row["avg_lexical_distance_score"] or 0.0, 6),
        "avg_structural_similarity_score": round(queryless_row["avg_structural_similarity_score"] or 0.0, 6),
        "target_domain_counts": target_domain_counts,
        "distinct_target_domain_count": len(target_domain_counts),
        "dominant_dead_end_family": dominant_dead_end_family,
        "top_briefs": [
            {
                "brief_rank": brief["brief_rank"],
                "brief_name": brief["brief_name"],
                "brief_status": brief["brief_status"],
            }
            for brief in briefs[:5]
        ],
    }
    recommendation, reasons = derive_recommendation(summary)
    summary["recommendation"] = recommendation
    summary["recommendation_reasons"] = reasons
    return summary


def render_markdown(summary, output_dir: Path):
    lines = [
        "# Live Brief Queue Assessment",
        "",
        f"- Run prefix: `{summary['run_prefix']}`",
        f"- Recommendation: `{summary['recommendation']}`",
        f"- Brief count: `{summary['brief_count']}`",
        f"- Provisional brief count: `{summary['provisional_brief_count']}`",
        f"- Passed family count: `{summary['passed_family_count']}`",
        f"- Cross-family hit count: `{summary['cross_family_hit_count']}`",
        f"- Holdout hit count: `{summary['holdout_hit_count']}`",
        "",
        "## Why",
    ]
    for reason in summary["recommendation_reasons"]:
        lines.append(f"- {reason}")
    lines.extend(["", "## Top Briefs"])
    for item in summary["top_briefs"]:
        lines.append(
            f"- rank `{item['brief_rank']}`: `{item['brief_name']}` (`{item['brief_status']}`)"
        )
    lines.extend(["", "## Output"])
    lines.append(f"- Assessment directory: `{output_dir}`")
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    brief_run_id = f"{args.run_prefix}-c14"
    ranking_run_id = f"{args.run_prefix}-c13"
    queryless_run_id = f"{args.run_prefix}-c11"
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else ROOT / "data" / "structural-analogy" / "runs" / f"{args.run_prefix}-assessment"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    try:
        briefs = load_briefs(connection, brief_run_id)
        ranking_rows = load_ranking_summary(connection, ranking_run_id)
        queryless_row = load_queryless_summary(connection, queryless_run_id)
        target_domain_counts = load_target_domain_counts(connection, brief_run_id)
    finally:
        connection.close()

    if not briefs:
        raise SystemExit(f"no strategy_briefs found for run {brief_run_id}")

    summary = build_summary(
        args.run_prefix,
        briefs,
        ranking_rows,
        queryless_row,
        target_domain_counts,
    )
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()

    json_path = output_dir / "live_brief_queue_assessment.json"
    md_path = output_dir / "README.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(summary, output_dir) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), **summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
