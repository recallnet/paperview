#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path

from ingest_extraction_responses import (
    ingest,
    load_run,
    write_ingest_artifacts,
)
from review_extraction_quality import build_report, load_rows
from validate_schema_examples import load_json


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "extraction.schema.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Apply the extraction quality gate and ingest only if the run passes."
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Extraction run id created by scripts/create_extraction_run.py.",
    )
    parser.add_argument(
        "--responses-path",
        required=True,
        help="Path to responses JSONL from a model run.",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-path",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to the extraction schema.",
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Permit ingestion when the gate status is warning. Blocking findings still stop ingestion.",
    )
    parser.add_argument(
        "--ingest-passing-subset-on-blocking",
        action="store_true",
        help=(
            "When the batch is blocking, write and ingest a pass-only subset instead "
            "of stopping the whole run."
        ),
    )
    return parser.parse_args()


def write_quality_report(run_dir: Path, responses_path: Path, report):
    report_path = responses_path.with_suffix(".quality.json")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    gate_summary_path = run_dir / "gate_summary.json"
    gate_summary = {
        "responses_path": str(responses_path.resolve()),
        "quality_report_path": str(report_path.resolve()),
        "gate_status": report["gate_status"],
        "mechanism_count": report.get("mechanism_count"),
        "semantic_pass_rate": report.get("semantic_pass_rate"),
        "unsupported_enum_ratio": report.get("unsupported_enum_ratio"),
        "ambiguous_normalization_ratio": report.get("ambiguous_normalization_ratio"),
        "accepted_with_evidence_and_blockers_ratio": report.get(
            "accepted_with_evidence_and_blockers_ratio"
        ),
        "blocking_count": report["blocking_count"],
        "warning_count": report["warning_count"],
        "reviewed_count": report["reviewed_count"],
    }
    gate_summary_path.write_text(
        json.dumps(gate_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path, gate_summary_path


def update_run_status(connection, run_id: str, status: str):
    connection.execute(
        "UPDATE extraction_runs SET run_status = ? WHERE run_id = ?",
        (status, run_id),
    )


def build_passing_subset(rows, report):
    accepted_rows = []
    blocked_paper_ids = []
    report_by_paper_id = {
        item["paper_id"]: item
        for item in report["items"]
    }

    for row in rows:
        paper_id = row.get("paper_id")
        item = report_by_paper_id.get(paper_id)
        if item is None:
            continue
        if item["gate_status"] == "pass":
            accepted_rows.append(row)
        else:
            blocked_paper_ids.append(paper_id)

    return accepted_rows, blocked_paper_ids


def write_rows(path: Path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    responses_path = Path(args.responses_path).resolve()
    schema = load_json(Path(args.schema_path).resolve())
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(responses_path)
    report = build_report(rows, schema)
    report_path, gate_summary_path = write_quality_report(run_dir, responses_path, report)

    if report["gate_status"] == "blocking":
        if args.ingest_passing_subset_on_blocking:
            accepted_rows, blocked_paper_ids = build_passing_subset(rows, report)
            if not accepted_rows:
                connection = sqlite3.connect(str(db_path))
                try:
                    load_run(connection, args.run_id)
                    update_run_status(connection, args.run_id, "blocked_by_quality_gate")
                    connection.commit()
                finally:
                    connection.close()

                print(
                    json.dumps(
                        {
                            "gate_status": report["gate_status"],
                            "quality_report_path": str(report_path.resolve()),
                            "gate_summary_path": str(gate_summary_path.resolve()),
                            "accepted_row_count": 0,
                            "blocked_row_count": len(blocked_paper_ids),
                            "ingested": False,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                raise SystemExit(2)

            filtered_responses_path = responses_path.with_name(
                f"{responses_path.stem}.accepted.jsonl"
            )
            write_rows(filtered_responses_path, accepted_rows)

            connection = sqlite3.connect(str(db_path))
            try:
                run = load_run(connection, args.run_id)
                # @context decision -- The live extraction backlog can contain mostly-usable
                # prepared batches with a few known-bad rows. In that case the critical-path
                # move is to preserve the reviewer decision boundary and ingest only the clean
                # subset, not to either poison `mechanism_instances` with blocked rows or stall
                # the entire downstream run on a handful of failures.
                summary = ingest(
                    connection=connection,
                    schema=schema,
                    run=run,
                    responses_path=filtered_responses_path,
                )
                update_run_status(connection, args.run_id, "partially_ingested_pass_subset")
                connection.commit()
            finally:
                connection.close()

            ingest_summary_path = write_ingest_artifacts(
                run_dir=run_dir,
                responses_path=filtered_responses_path,
                summary=summary,
            )

            print(
                json.dumps(
                    {
                        "gate_status": report["gate_status"],
                        "quality_report_path": str(report_path.resolve()),
                        "gate_summary_path": str(gate_summary_path.resolve()),
                        "filtered_responses_path": str(filtered_responses_path.resolve()),
                        "ingest_summary_path": str(ingest_summary_path.resolve()),
                        "accepted_row_count": len(accepted_rows),
                        "blocked_row_count": len(blocked_paper_ids),
                        "blocked_paper_ids": blocked_paper_ids,
                        "ingested": True,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return

        connection = sqlite3.connect(str(db_path))
        try:
            load_run(connection, args.run_id)
            update_run_status(connection, args.run_id, "blocked_by_quality_gate")
            connection.commit()
        finally:
            connection.close()

        print(
            json.dumps(
                {
                    "gate_status": report["gate_status"],
                    "quality_report_path": str(report_path.resolve()),
                    "gate_summary_path": str(gate_summary_path.resolve()),
                    "ingested": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(2)

    if report["gate_status"] == "warning" and not args.allow_warnings:
        connection = sqlite3.connect(str(db_path))
        try:
            load_run(connection, args.run_id)
            update_run_status(connection, args.run_id, "warning_requires_review")
            connection.commit()
        finally:
            connection.close()

        print(
            json.dumps(
                {
                    "gate_status": report["gate_status"],
                    "quality_report_path": str(report_path.resolve()),
                    "gate_summary_path": str(gate_summary_path.resolve()),
                    "ingested": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(3)

    connection = sqlite3.connect(str(db_path))
    try:
        run = load_run(connection, args.run_id)
        summary = ingest(
            connection=connection,
            schema=schema,
            run=run,
            responses_path=responses_path,
        )
        update_run_status(connection, args.run_id, "ingested")
        connection.commit()
    finally:
        connection.close()

    ingest_summary_path = write_ingest_artifacts(
        run_dir=run_dir,
        responses_path=responses_path,
        summary=summary,
    )

    print(
        json.dumps(
            {
                "gate_status": report["gate_status"],
                "quality_report_path": str(report_path.resolve()),
                "gate_summary_path": str(gate_summary_path.resolve()),
                "ingest_summary_path": str(ingest_summary_path.resolve()),
                "ingested": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
