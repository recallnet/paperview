#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"
DEFAULT_RUN_KIND = "gate_c_review"
POSITIVE_VALUES = {"yes", "true", "1", "pass", "accepted", "high"}
NEGATIVE_VALUES = {"no", "false", "0", "fail", "rejected", "low"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Persist analyst Gate C reviews and summarize whether the brief surface passes."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-sql-path",
        default=str(DEFAULT_SCHEMA_SQL_PATH),
        help="Path to the SQL schema to apply before review.",
    )
    parser.add_argument(
        "--brief-run-id",
        required=True,
        help="Strategy brief generation run id produced by generate_strategy_briefs.py.",
    )
    parser.add_argument(
        "--reviews-path",
        required=True,
        help="Path to a JSONL file of Gate C analyst reviews.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit Gate C review run id.",
    )
    parser.add_argument(
        "--created-by",
        default="analyst",
        help="Name or handle to persist as the review author.",
    )
    parser.add_argument(
        "--required-new-briefs",
        type=int,
        default=5,
        help="Minimum count of genuinely new and worth-validation briefs required to pass Gate C.",
    )
    parser.add_argument(
        "--required-executor-or-regime",
        type=int,
        default=2,
        help="Minimum count of briefs implying a new executor primitive or regime filter.",
    )
    parser.add_argument(
        "--required-holdout",
        type=int,
        default=1,
        help="Minimum count of holdout candidates with near-zero seed overlap.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def parse_json_lines(path: Path):
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        materialized = line.strip()
        if not materialized:
            continue
        try:
            records.append(json.loads(materialized))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
    return records


def normalize_bool(value):
    if isinstance(value, bool):
        return 1 if value else 0
    normalized = str(value or "").strip().lower()
    if normalized in POSITIVE_VALUES:
        return 1
    if normalized in NEGATIVE_VALUES:
        return 0
    if normalized == "":
        return None
    raise SystemExit(f"unrecognized boolean-style Gate C label: {value!r}")


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))


def ensure_run(connection, run_id: str | None, args):
    resolved_run_id = run_id or (
        f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    config = {
        "brief_run_id": args.brief_run_id,
        "reviews_path": str(Path(args.reviews_path).resolve()),
        "required_new_briefs": args.required_new_briefs,
        "required_executor_or_regime": args.required_executor_or_regime,
        "required_holdout": args.required_holdout,
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
                args.brief_run_id,
                "gate-c-review-v1",
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
                args.brief_run_id,
                "gate-c-review-v1",
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def load_briefs(connection, brief_run_id: str):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          strategy_brief_id,
          candidate_family_id,
          brief_name,
          brief_rank,
          brief_json
        FROM strategy_briefs
        WHERE run_id = ?
        ORDER BY brief_rank, strategy_brief_id
        """,
        (brief_run_id,),
    ).fetchall()
    by_id = {}
    by_name = {}
    by_family = {}
    for row in rows:
        record = dict(row)
        by_id[row["strategy_brief_id"]] = record
        by_name[row["brief_name"]] = record
        by_family[row["candidate_family_id"]] = record
    return by_id, by_name, by_family


def resolve_brief(record, briefs_by_id, briefs_by_name, briefs_by_family):
    if record.get("strategy_brief_id") is not None:
        brief = briefs_by_id.get(int(record["strategy_brief_id"]))
        if brief is None:
            raise SystemExit(f"unknown strategy_brief_id in review record: {record['strategy_brief_id']}")
        return brief
    if record.get("candidate_family_id") is not None:
        brief = briefs_by_family.get(int(record["candidate_family_id"]))
        if brief is None:
            raise SystemExit(f"unknown candidate_family_id in review record: {record['candidate_family_id']}")
        return brief
    if record.get("brief_name"):
        brief = briefs_by_name.get(str(record["brief_name"]))
        if brief is None:
            raise SystemExit(f"unknown brief_name in review record: {record['brief_name']}")
        return brief
    raise SystemExit(
        "each Gate C review record must include strategy_brief_id, candidate_family_id, or brief_name"
    )


def persist_review(connection, run_id: str, reviewer: str, brief, record):
    notes = str(record.get("review_notes") or record.get("notes") or "").strip()
    evidence_payload = {
        "reviewer_decision": record.get("reviewer_decision"),
        "novelty_reason": record.get("novelty_reason"),
        "validation_reason": record.get("validation_reason"),
        "executor_reason": record.get("executor_reason"),
        "regime_reason": record.get("regime_reason"),
        "holdout_reason": record.get("holdout_reason"),
    }
    connection.execute(
        """
        INSERT INTO gate_c_brief_reviews (
          run_id,
          strategy_brief_id,
          candidate_family_id,
          reviewed_by,
          genuinely_new,
          worth_validation,
          new_executor_primitive,
          new_regime_filter,
          holdout_near_zero_overlap,
          review_notes,
          evidence_json,
          updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, strategy_brief_id) DO UPDATE SET
          reviewed_by = excluded.reviewed_by,
          genuinely_new = excluded.genuinely_new,
          worth_validation = excluded.worth_validation,
          new_executor_primitive = excluded.new_executor_primitive,
          new_regime_filter = excluded.new_regime_filter,
          holdout_near_zero_overlap = excluded.holdout_near_zero_overlap,
          review_notes = excluded.review_notes,
          evidence_json = excluded.evidence_json,
          updated_at = excluded.updated_at
        """,
        (
            run_id,
            brief["strategy_brief_id"],
            brief["candidate_family_id"],
            reviewer,
            normalize_bool(record.get("genuinely_new")),
            normalize_bool(record.get("worth_validation")),
            normalize_bool(record.get("new_executor_primitive")),
            normalize_bool(record.get("new_regime_filter")),
            normalize_bool(record.get("holdout_near_zero_overlap")),
            notes,
            json.dumps({k: v for k, v in evidence_payload.items() if v}, sort_keys=True),
            now_utc(),
        ),
    )


def update_brief_status(connection, brief):
    connection.execute(
        """
        UPDATE strategy_briefs
        SET brief_status = ?, updated_at = ?
        WHERE strategy_brief_id = ?
        """,
        ("reviewed", now_utc(), brief["strategy_brief_id"]),
    )


def summarize(connection, run_id: str, brief_run_id: str, thresholds):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          strategy_brief_id,
          genuinely_new,
          worth_validation,
          new_executor_primitive,
          new_regime_filter,
          holdout_near_zero_overlap
        FROM gate_c_brief_reviews
        WHERE run_id = ?
        ORDER BY strategy_brief_id
        """,
        (run_id,),
    ).fetchall()
    reviewed_count = len(rows)
    # @context requirement -- Gate C only counts a brief toward the main
    # novelty threshold when the reviewer marks it as both genuinely new and
    # worth validation. Treating either flag alone as sufficient would inflate
    # success claims and break the plan's final acceptance contract.
    new_and_worth = sum(
        1 for row in rows if row["genuinely_new"] == 1 and row["worth_validation"] == 1
    )
    executor_or_regime = sum(
        1
        for row in rows
        if row["new_executor_primitive"] == 1 or row["new_regime_filter"] == 1
    )
    holdout = sum(1 for row in rows if row["holdout_near_zero_overlap"] == 1)
    gate_c_passed = int(
        new_and_worth >= thresholds["required_new_briefs"]
        and executor_or_regime >= thresholds["required_executor_or_regime"]
        and holdout >= thresholds["required_holdout"]
    )
    summary = {
        "run_id": run_id,
        "brief_run_id": brief_run_id,
        "reviewed_count": reviewed_count,
        "genuinely_new_and_worth_validation_count": new_and_worth,
        "new_executor_or_regime_count": executor_or_regime,
        "holdout_near_zero_overlap_count": holdout,
        "thresholds": thresholds,
        "gate_c_passed": bool(gate_c_passed),
    }
    connection.execute(
        """
        INSERT INTO gate_c_review_summaries (
          run_id,
          brief_run_id,
          reviewed_count,
          genuinely_new_and_worth_validation_count,
          new_executor_or_regime_count,
          holdout_near_zero_overlap_count,
          gate_c_passed,
          summary_json,
          updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
          brief_run_id = excluded.brief_run_id,
          reviewed_count = excluded.reviewed_count,
          genuinely_new_and_worth_validation_count = excluded.genuinely_new_and_worth_validation_count,
          new_executor_or_regime_count = excluded.new_executor_or_regime_count,
          holdout_near_zero_overlap_count = excluded.holdout_near_zero_overlap_count,
          gate_c_passed = excluded.gate_c_passed,
          summary_json = excluded.summary_json,
          updated_at = excluded.updated_at
        """,
        (
            run_id,
            brief_run_id,
            reviewed_count,
            new_and_worth,
            executor_or_regime,
            holdout,
            gate_c_passed,
            json.dumps(summary, sort_keys=True),
            now_utc(),
        ),
    )
    return summary


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    schema_sql_path = Path(args.schema_sql_path).resolve()
    review_records = parse_json_lines(Path(args.reviews_path).resolve())

    connection = sqlite3.connect(str(db_path))
    try:
        ensure_store_contract(connection, schema_sql_path)
        run_id = ensure_run(connection, args.run_id, args)
        connection.commit()

        briefs_by_id, briefs_by_name, briefs_by_family = load_briefs(connection, args.brief_run_id)
        if not briefs_by_id:
            raise SystemExit(
                "no strategy_briefs found for the requested brief run; complete C14 before Gate C review"
            )

        connection.execute("BEGIN")
        try:
            for record in review_records:
                brief = resolve_brief(record, briefs_by_id, briefs_by_name, briefs_by_family)
                persist_review(connection, run_id, args.created_by, brief, record)
                update_brief_status(connection, brief)

            summary = summarize(
                connection,
                run_id,
                args.brief_run_id,
                {
                    "required_new_briefs": args.required_new_briefs,
                    "required_executor_or_regime": args.required_executor_or_regime,
                    "required_holdout": args.required_holdout,
                },
            )
            connection.execute(
                """
                UPDATE extraction_runs
                SET run_status = ?, completed_at = ?
                WHERE run_id = ?
                """,
                ("completed", now_utc(), run_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
