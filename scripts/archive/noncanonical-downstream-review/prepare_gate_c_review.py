#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"
DEFAULT_RUN_KIND = "gate_c_review_prep"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare a Gate C analyst review packet and editable JSONL template from strategy briefs."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-sql-path",
        default=str(DEFAULT_SCHEMA_SQL_PATH),
        help="Path to the SQL schema to apply before preparing the review packet.",
    )
    parser.add_argument(
        "--brief-run-id",
        required=True,
        help="Strategy brief generation run id produced by generate_strategy_briefs.py.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit Gate C review-prep run id.",
    )
    parser.add_argument(
        "--max-briefs",
        type=int,
        default=25,
        help="Maximum number of briefs to include in the prepared review packet.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))


def ensure_run(connection, run_id: str | None, brief_run_id: str, max_briefs: int):
    resolved_run_id = run_id or (
        f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    config = {
        "brief_run_id": brief_run_id,
        "max_briefs": max_briefs,
    }
    existing = connection.execute(
        "SELECT run_id FROM extraction_runs WHERE run_id = ?",
        (resolved_run_id,),
    ).fetchone()
    if existing is None:
        connection.execute(
            """
            INSERT INTO extraction_runs (
              run_id,
              run_kind,
              model_name,
              prompt_version,
              config_json,
              started_at,
              run_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_run_id,
                DEFAULT_RUN_KIND,
                brief_run_id,
                "gate-c-review-prep-v1",
                json.dumps(config, sort_keys=True),
                now_utc(),
                "running",
            ),
        )
    else:
        connection.execute(
            """
            UPDATE extraction_runs
            SET run_kind = ?,
                model_name = ?,
                prompt_version = ?,
                config_json = ?,
                run_status = ?,
                completed_at = NULL
            WHERE run_id = ?
            """,
            (
                DEFAULT_RUN_KIND,
                brief_run_id,
                "gate-c-review-prep-v1",
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def parse_json_object(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {}


def load_briefs(connection, brief_run_id: str, max_briefs: int):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          strategy_brief_id,
          candidate_family_id,
          candidate_family_ranking_id,
          brief_name,
          brief_status,
          brief_rank,
          brief_markdown_path,
          brief_json
        FROM strategy_briefs
        WHERE run_id = ?
        ORDER BY brief_rank, strategy_brief_id
        LIMIT ?
        """,
        (brief_run_id, max_briefs),
    ).fetchall()
    return [{**dict(row), "brief_json": parse_json_object(row["brief_json"])} for row in rows]


def build_review_template_record(brief):
    payload = brief["brief_json"]
    # @context requirement -- Gate C review input must carry stable ids from
    # the persisted brief surface, not only human-readable names. Brief names
    # can be edited for readability later, but review ingestion must still map
    # back to the exact reviewed packet without ambiguous manual reconciliation.
    return {
        "strategy_brief_id": brief["strategy_brief_id"],
        "candidate_family_id": brief["candidate_family_id"],
        "brief_name": brief["brief_name"],
        "brief_rank": brief["brief_rank"],
        "target_domain": payload.get("target_domain"),
        "tradecore_mapping": payload.get("tradecore_mapping"),
        "representative_candidate_mechanism": payload.get("representative_candidate_mechanism"),
        "genuinely_new": "",
        "worth_validation": "",
        "new_executor_primitive": "",
        "new_regime_filter": "",
        "holdout_near_zero_overlap": "",
        "reviewer_decision": "",
        "novelty_reason": "",
        "validation_reason": "",
        "executor_reason": "",
        "regime_reason": "",
        "holdout_reason": "",
        "review_notes": "",
    }


def build_manifest(run_id: str, brief_run_id: str, briefs, template_path: Path):
    return {
        "run_id": run_id,
        "brief_run_id": brief_run_id,
        "prepared_brief_count": len(briefs),
        "template_path": str(template_path),
        "briefs": [
            {
                "strategy_brief_id": brief["strategy_brief_id"],
                "brief_name": brief["brief_name"],
                "brief_rank": brief["brief_rank"],
                "brief_status": brief["brief_status"],
                "brief_markdown_path": brief["brief_markdown_path"],
            }
            for brief in briefs
        ],
    }


def render_readme(run_id: str, brief_run_id: str, briefs, template_path: Path):
    lines = [
        "# Gate C Review Packet",
        "",
        f"- Review prep run: `{run_id}`",
        f"- Strategy brief run: `{brief_run_id}`",
        f"- Prepared briefs: `{len(briefs)}`",
        f"- Review template: `{template_path}`",
        "",
        "## Instructions",
        "",
        "1. Read each listed brief packet.",
        "2. Fill in the JSONL template one line per brief.",
        "3. Preserve `strategy_brief_id` and `candidate_family_id` exactly.",
        "4. Run `npm run gatec:review -- --brief-run-id <brief-run-id> --reviews-path <filled-template>` after review.",
        "",
        "## Briefs",
    ]
    for brief in briefs:
        lines.append(
            f"- rank `{brief['brief_rank']}`: `{brief['brief_name']}` -> `{brief['brief_markdown_path']}`"
        )
    lines.append("")
    return "\n".join(lines)


def write_packet(run_id: str, brief_run_id: str, briefs):
    packet_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id / "gate-c-review"
    packet_dir.mkdir(parents=True, exist_ok=True)
    template_path = packet_dir / "gate_c_review_template.jsonl"
    manifest_path = packet_dir / "gate_c_review_manifest.json"
    readme_path = packet_dir / "README.md"

    template_lines = [
        json.dumps(build_review_template_record(brief), sort_keys=True) for brief in briefs
    ]
    template_path.write_text("\n".join(template_lines) + "\n", encoding="utf-8")
    manifest = build_manifest(run_id, brief_run_id, briefs, template_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme_path.write_text(render_readme(run_id, brief_run_id, briefs, template_path) + "\n", encoding="utf-8")
    return template_path, manifest_path, readme_path


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    schema_sql_path = Path(args.schema_sql_path).resolve()

    connection = sqlite3.connect(str(db_path))
    try:
        ensure_store_contract(connection, schema_sql_path)
        run_id = ensure_run(connection, args.run_id, args.brief_run_id, args.max_briefs)
        connection.commit()

        briefs = load_briefs(connection, args.brief_run_id, args.max_briefs)
        if not briefs:
            raise SystemExit(
                "no strategy_briefs found for the requested brief run; complete C14 before preparing Gate C review"
            )
        template_path, manifest_path, readme_path = write_packet(run_id, args.brief_run_id, briefs)
        connection.execute(
            """
            UPDATE extraction_runs
            SET run_status = ?, completed_at = ?
            WHERE run_id = ?
            """,
            ("completed", now_utc(), run_id),
        )
        connection.commit()
    finally:
        connection.close()

    print(
        json.dumps(
            {
                "run_id": run_id,
                "brief_run_id": args.brief_run_id,
                "prepared_brief_count": len(briefs),
                "template_path": str(template_path),
                "manifest_path": str(manifest_path),
                "readme_path": str(readme_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
