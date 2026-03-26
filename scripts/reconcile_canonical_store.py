#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path

from ingest_extraction_responses import (
    ensure_c05_store_contract,
    load_run,
    normalize_line,
    promote_to_mechanism_store,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Upgrade the local SQLite store to the canonical schema and backfill legacy paper extractions."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional extraction run id filter. Reconcile all valid rows when omitted.",
    )
    return parser.parse_args()


def iter_rows(connection, run_id=None):
    query = """
        SELECT extraction_id, paper_id, run_id, extraction_json
        FROM paper_extractions
        WHERE validation_status = 'valid'
    """
    params = ()
    if run_id is not None:
        query += " AND run_id = ?"
        params = (run_id,)
    query += " ORDER BY extraction_id"
    return connection.execute(query, params).fetchall()


def count_rows(connection, table_name):
    return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    connection = sqlite3.connect(str(db_path))
    try:
        ensure_c05_store_contract(connection)
        connection.execute("BEGIN")
        promoted_rows = 0
        mechanism_inserted = 0
        mechanism_updated = 0
        evidence_spans_written = 0

        for extraction_id, paper_id, run_id, extraction_json in iter_rows(connection, args.run_id):
            run = load_run(connection, run_id)
            normalized_payload = normalize_line(json.loads(extraction_json))
            normalized_payload["paper_id"] = paper_id
            summary = promote_to_mechanism_store(
                connection=connection,
                extraction_id=extraction_id,
                run=run,
                normalized_payload=normalized_payload,
            )
            promoted_rows += 1
            mechanism_inserted += summary["mechanism_inserted"]
            mechanism_updated += summary["mechanism_updated"]
            evidence_spans_written += summary["evidence_spans_written"]

        connection.commit()

        summary = {
            "db_path": str(db_path),
            "run_id": args.run_id,
            "promoted_rows": promoted_rows,
            "mechanism_inserted": mechanism_inserted,
            "mechanism_updated": mechanism_updated,
            "evidence_spans_written": evidence_spans_written,
            "mechanism_instance_count": count_rows(connection, "mechanism_instances"),
            "mechanism_evidence_span_count": count_rows(connection, "mechanism_evidence_spans"),
            "paper_extraction_count": count_rows(connection, "paper_extractions"),
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
