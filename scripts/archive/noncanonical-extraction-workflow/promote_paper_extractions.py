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


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Promote existing paper_extractions rows into canonical mechanism tables."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run id filter. Promote all valid rows when omitted.",
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


def main():
    args = parse_args()
    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    try:
        ensure_c05_store_contract(connection)
        connection.execute("BEGIN")
        promoted_rows = 0
        mechanism_inserted = 0
        mechanism_updated = 0
        evidence_spans_written = 0

        for extraction_id, paper_id, run_id, extraction_json in iter_rows(
            connection, args.run_id
        ):
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
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(
        json.dumps(
            {
                "promoted_rows": promoted_rows,
                "mechanism_inserted": mechanism_inserted,
                "mechanism_updated": mechanism_updated,
                "evidence_spans_written": evidence_spans_written,
                "run_id": args.run_id,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
