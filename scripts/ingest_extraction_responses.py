#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from validate_schema_examples import SchemaValidationError, load_json, validate


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "extraction.schema.json"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate and ingest abstract extraction responses into SQLite."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Extraction run id created by scripts/create_extraction_run.py.",
    )
    parser.add_argument(
        "--responses-path",
        required=True,
        help="Path to JSONL responses. Each line must contain either an extraction object, {'paper_id', 'extraction': {...}}, or {'paper_id', 'mechanism_instances': [...]}",
    )
    parser.add_argument(
        "--schema-path",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to the extraction JSON schema.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def ensure_column(connection, table_name: str, column_name: str, ddl_fragment: str):
    columns = {
        row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")
    }
    if column_name in columns:
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_fragment}")


def ensure_c05_store_contract(connection, schema_sql_path: Path = DEFAULT_SCHEMA_SQL_PATH):
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if "papers" in tables:
        ensure_column(connection, "papers", "literature_family", "TEXT NOT NULL DEFAULT 'q_fin'")
        ensure_column(connection, "papers", "evaluation_split", "TEXT NOT NULL DEFAULT 'tuning'")
    if "paper_extractions" in tables:
        ensure_column(
            connection,
            "paper_extractions",
            "response_contract_version",
            "TEXT NOT NULL DEFAULT 'legacy-single-mechanism-v1'",
        )

    # @context requirement -- The checked-in SQL schema is the canonical source
    # of truth for the mechanism-first store. Live SQLite files can lag that
    # schema for many turns, so promotion and ingestion must materialize missing
    # tables before assuming column-level migrations are enough.
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))

    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(mechanism_instances)")
    }
    if "evidence_confidence" not in columns:
        connection.execute(
            """
            ALTER TABLE mechanism_instances
            ADD COLUMN evidence_confidence TEXT NOT NULL DEFAULT 'unscored'
            """
        )


def infer_legacy_insight_type(extraction):
    tradecore_fit = extraction.get("tradecore_fit", "low")
    prediction_portability = extraction.get("prediction_market_portability", "low")
    novel_portability = extraction.get("novel_market_portability", "low")
    if tradecore_fit == "high" and (
        prediction_portability in {"medium", "high"} or novel_portability in {"medium", "high"}
    ):
        return "executable_strategy_primitive"
    if tradecore_fit in {"medium", "high"}:
        return "missing_executor_primitive"
    return "research_dead_end_worth_excluding"


def upgrade_legacy_extraction_contract(extraction):
    upgraded = dict(extraction)
    defaults = {
        "insight_type": infer_legacy_insight_type(extraction),
        "required_assumptions": ["other"],
        "assumption_violations": ["other"],
        "fragility_flags": ["other"],
        "capacity_constraints": ["other"],
        "failure_regimes": ["other"],
        "negative_transfer_rationale": ["other"],
    }
    for field_name, fallback in defaults.items():
        if field_name not in upgraded or upgraded[field_name] in (None, [], ""):
            upgraded[field_name] = fallback
    return upgraded


def load_run(connection, run_id: str):
    row = connection.execute(
        """
        SELECT run_id, prompt_version
        FROM extraction_runs
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        raise SystemExit(f"unknown run_id: {run_id}")
    return {"run_id": row[0], "prompt_version": row[1]}


def normalize_line(payload):
    if not isinstance(payload, dict):
        raise SchemaValidationError("$: expected object")

    if "extraction" in payload:
        extraction = payload["extraction"]
        if "paper_id" not in extraction and "paper_id" in payload:
            extraction = dict(extraction)
            extraction["paper_id"] = payload["paper_id"]
        extraction = upgrade_legacy_extraction_contract(extraction)
        return {
            "paper_id": extraction["paper_id"],
            "contract_version": "legacy-single-mechanism-v1",
            "mechanism_instances": [extraction],
            "staging_payload": extraction,
        }

    if "mechanism_instances" in payload:
        paper_id = payload.get("paper_id")
        if not isinstance(payload["mechanism_instances"], list):
            raise SchemaValidationError("$.mechanism_instances: expected array")

        normalized_instances = []
        for index, extraction in enumerate(payload["mechanism_instances"]):
            if not isinstance(extraction, dict):
                raise SchemaValidationError(
                    f"$.mechanism_instances[{index}]: expected object"
                )
            normalized = upgrade_legacy_extraction_contract(extraction)
            if "paper_id" not in normalized:
                if paper_id is None:
                    raise SchemaValidationError(
                        f"$.mechanism_instances[{index}]: missing paper_id"
                    )
                normalized["paper_id"] = paper_id
            normalized_instances.append(normalized)

        if paper_id is None:
            if normalized_instances:
                paper_id = normalized_instances[0]["paper_id"]
            else:
                raise SchemaValidationError("$.paper_id: missing required key 'paper_id'")

        return {
            "paper_id": paper_id,
            "contract_version": payload.get(
                "response_contract_version",
                "mechanism-instance-batch-v1",
            ),
            "mechanism_instances": normalized_instances,
            "staging_payload": {
                "paper_id": paper_id,
                "response_contract_version": payload.get(
                    "response_contract_version",
                    "mechanism-instance-batch-v1",
                ),
                "mechanism_instances": normalized_instances,
            },
        }

    if "paper_id" not in payload:
        raise SchemaValidationError("$.paper_id: missing required key 'paper_id'")

    payload = upgrade_legacy_extraction_contract(payload)
    return {
        "paper_id": payload["paper_id"],
        "contract_version": "legacy-single-mechanism-v1",
        "mechanism_instances": [payload],
        "staging_payload": payload,
    }


def fetch_paper_abstract(connection, paper_id: str):
    row = connection.execute(
        """
        SELECT abstract
        FROM papers
        WHERE paper_id = ?
        """,
        (paper_id,),
    ).fetchone()
    if row is None:
        raise SystemExit(f"unknown paper_id: {paper_id}")
    return row[0]


def persist_staging_extraction(connection, paper_id: str, run, normalized_payload):
    existed = connection.execute(
        """
        SELECT extraction_id
        FROM paper_extractions
        WHERE paper_id = ? AND run_id = ? AND extraction_version = ?
        """,
        (paper_id, run["run_id"], run["prompt_version"]),
    ).fetchone()

    connection.execute(
        """
        INSERT INTO paper_extractions (
          paper_id,
          run_id,
          extraction_version,
          extraction_json,
          response_contract_version,
          validation_status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(paper_id, run_id, extraction_version) DO UPDATE SET
          extraction_json = excluded.extraction_json,
          response_contract_version = excluded.response_contract_version,
          validation_status = excluded.validation_status
        """,
        (
            paper_id,
            run["run_id"],
            run["prompt_version"],
            json.dumps(normalized_payload["staging_payload"], sort_keys=True),
            normalized_payload["contract_version"],
            "valid",
        ),
    )

    extraction_id = connection.execute(
        """
        SELECT extraction_id
        FROM paper_extractions
        WHERE paper_id = ? AND run_id = ? AND extraction_version = ?
        """,
        (paper_id, run["run_id"], run["prompt_version"]),
    ).fetchone()[0]
    return extraction_id, existed is not None


def build_mechanism_json(extraction):
    return {
        "original_market_domain": extraction["original_market_domain"],
        "instrument_type": extraction["instrument_type"],
        "edge_source": extraction["edge_source"],
        "execution_style": extraction["execution_style"],
        "holding_horizon": extraction["holding_horizon"],
        "required_market_conditions": extraction["required_market_conditions"],
        "main_failure_modes": extraction["main_failure_modes"],
        "prediction_market_portability": extraction["prediction_market_portability"],
        "novel_market_portability": extraction["novel_market_portability"],
        "tradecore_fit": extraction["tradecore_fit"],
        "likely_crowding": extraction["likely_crowding"],
        "why_missed": extraction["why_missed"],
        "negative_transfer_rationale": extraction["negative_transfer_rationale"],
    }


def upsert_mechanism_instance(connection, extraction_id: int, run, extraction):
    mechanism_label = extraction["mechanism_name"]
    existing = connection.execute(
        """
        SELECT mechanism_instance_id
        FROM mechanism_instances
        WHERE paper_id = ? AND source_extraction_id = ? AND mechanism_label = ?
        """,
        (extraction["paper_id"], extraction_id, mechanism_label),
    ).fetchone()

    now = now_utc()
    mechanism_json = json.dumps(build_mechanism_json(extraction), sort_keys=True)
    shared_params = (
        extraction["paper_id"],
        extraction_id,
        run["run_id"],
        mechanism_label,
        extraction["mechanism_summary"],
        extraction["insight_type"],
        extraction["evidence_strength"],
        json.dumps(extraction["required_assumptions"], sort_keys=True),
        json.dumps(extraction["assumption_violations"], sort_keys=True),
        json.dumps(extraction["fragility_flags"], sort_keys=True),
        json.dumps(extraction["capacity_constraints"], sort_keys=True),
        json.dumps(extraction["failure_regimes"], sort_keys=True),
        mechanism_json,
        "active",
        now,
    )

    if existing is None:
        connection.execute(
            """
            INSERT INTO mechanism_instances (
              paper_id,
              source_extraction_id,
              run_id,
              mechanism_label,
              mechanism_summary,
              insight_type,
              evidence_confidence,
              required_assumptions_json,
              assumption_violations_json,
              fragility_flags_json,
              capacity_constraints_json,
              failure_regimes_json,
              mechanism_json,
              lifecycle_status,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            shared_params,
        )
        mechanism_instance_id = connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]
        was_inserted = True
    else:
        mechanism_instance_id = existing[0]
        connection.execute(
            """
            UPDATE mechanism_instances
            SET run_id = ?,
                mechanism_summary = ?,
                insight_type = ?,
                evidence_confidence = ?,
                required_assumptions_json = ?,
                assumption_violations_json = ?,
                fragility_flags_json = ?,
                capacity_constraints_json = ?,
                failure_regimes_json = ?,
                mechanism_json = ?,
                lifecycle_status = ?,
                updated_at = ?
            WHERE mechanism_instance_id = ?
            """,
            (
                run["run_id"],
                extraction["mechanism_summary"],
                extraction["insight_type"],
                extraction["evidence_strength"],
                json.dumps(extraction["required_assumptions"], sort_keys=True),
                json.dumps(extraction["assumption_violations"], sort_keys=True),
                json.dumps(extraction["fragility_flags"], sort_keys=True),
                json.dumps(extraction["capacity_constraints"], sort_keys=True),
                json.dumps(extraction["failure_regimes"], sort_keys=True),
                mechanism_json,
                "active",
                now,
                mechanism_instance_id,
            ),
        )
        was_inserted = False

    return mechanism_instance_id, was_inserted


def replace_evidence_spans(connection, mechanism_instance_id: int, paper_id: str, extraction, paper_abstract):
    connection.execute(
        """
        DELETE FROM mechanism_evidence_spans
        WHERE mechanism_instance_id = ?
        """,
        (mechanism_instance_id,),
    )
    evidence_text = paper_abstract or extraction["mechanism_summary"]
    # @context decision -- C05 persists one abstract-backed evidence span per mechanism instance even
    # before C07 section parsing exists. This keeps the canonical write path evidence-bearing now
    # while preserving a clean upgrade path to section-level spans later.
    provenance = {
        "source_stage": "abstract_extraction",
        "evidence_confidence": extraction["evidence_strength"],
        "mechanism_summary": extraction["mechanism_summary"],
        "negative_transfer_rationale": extraction["negative_transfer_rationale"],
    }
    connection.execute(
        """
        INSERT INTO mechanism_evidence_spans (
          mechanism_instance_id,
          paper_id,
          evidence_kind,
          evidence_text,
          provenance_json
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            mechanism_instance_id,
            paper_id,
            "abstract_text",
            evidence_text,
            json.dumps(provenance, sort_keys=True),
        ),
    )


def mark_missing_mechanisms_superseded(connection, extraction_id: int, seen_labels):
    now = now_utc()
    if seen_labels:
        placeholders = ", ".join("?" for _ in seen_labels)
        connection.execute(
            f"""
            UPDATE mechanism_instances
            SET lifecycle_status = 'superseded',
                updated_at = ?
            WHERE source_extraction_id = ?
              AND mechanism_label NOT IN ({placeholders})
            """,
            (now, extraction_id, *sorted(seen_labels)),
        )
        return

    connection.execute(
        """
        UPDATE mechanism_instances
        SET lifecycle_status = 'superseded',
            updated_at = ?
        WHERE source_extraction_id = ?
        """,
        (now, extraction_id),
    )


def reconcile_benchmark_pairs(connection, paper_id: str):
    # @context risk -- benchmark_pairs still carries paper-level anchors from C04. We only bridge those
    # anchors to mechanism ids when each paper currently resolves to exactly one active mechanism.
    # Anything looser would silently invent benchmark labels once papers start producing 0..N mechanisms.
    mechanism_rows = connection.execute(
        """
        SELECT mechanism_instance_id
        FROM mechanism_instances
        WHERE paper_id = ?
          AND lifecycle_status = 'active'
        ORDER BY mechanism_instance_id
        """,
        (paper_id,),
    ).fetchall()
    if len(mechanism_rows) != 1:
        return

    mechanism_instance_id = mechanism_rows[0][0]
    now = now_utc()
    connection.execute(
        """
        UPDATE benchmark_pairs
        SET source_mechanism_instance_id = COALESCE(source_mechanism_instance_id, ?),
            updated_at = ?
        WHERE source_paper_id = ?
        """,
        (mechanism_instance_id, now, paper_id),
    )
    connection.execute(
        """
        UPDATE benchmark_pairs
        SET candidate_mechanism_instance_id = COALESCE(candidate_mechanism_instance_id, ?),
            updated_at = ?
        WHERE candidate_paper_id = ?
        """,
        (mechanism_instance_id, now, paper_id),
    )


def promote_to_mechanism_store(connection, extraction_id: int, run, normalized_payload):
    paper_id = normalized_payload["paper_id"]
    paper_abstract = fetch_paper_abstract(connection, paper_id)
    seen_labels = set()
    mechanism_inserted = 0
    mechanism_updated = 0
    evidence_spans_written = 0

    for extraction in normalized_payload["mechanism_instances"]:
        mechanism_instance_id, was_inserted = upsert_mechanism_instance(
            connection=connection,
            extraction_id=extraction_id,
            run=run,
            extraction=extraction,
        )
        if was_inserted:
            mechanism_inserted += 1
        else:
            mechanism_updated += 1
        replace_evidence_spans(
            connection=connection,
            mechanism_instance_id=mechanism_instance_id,
            paper_id=paper_id,
            extraction=extraction,
            paper_abstract=paper_abstract,
        )
        evidence_spans_written += 1
        seen_labels.add(extraction["mechanism_name"])

    mark_missing_mechanisms_superseded(connection, extraction_id, seen_labels)
    reconcile_benchmark_pairs(connection, paper_id)

    return {
        "mechanism_inserted": mechanism_inserted,
        "mechanism_updated": mechanism_updated,
        "evidence_spans_written": evidence_spans_written,
    }


def ingest(connection, schema, run, responses_path: Path):
    inserted = 0
    updated = 0
    invalid = 0
    mechanism_inserted = 0
    mechanism_updated = 0
    evidence_spans_written = 0
    errors = []

    connection.execute("BEGIN")
    try:
        ensure_c05_store_contract(connection)
        with responses_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                raw_payload = json.loads(line)
                try:
                    normalized_payload = normalize_line(raw_payload)
                except SchemaValidationError as exc:
                    invalid += 1
                    errors.append(
                        {
                            "line_number": line_number,
                            "paper_id": raw_payload.get("paper_id"),
                            "error": str(exc),
                        }
                    )
                    continue

                is_valid = True
                for extraction in normalized_payload["mechanism_instances"]:
                    try:
                        validate(schema, extraction)
                    except SchemaValidationError as exc:
                        invalid += 1
                        errors.append(
                            {
                                "line_number": line_number,
                                "paper_id": extraction.get("paper_id"),
                                "error": str(exc),
                            }
                        )
                        is_valid = False
                        break
                if not is_valid:
                    continue

                paper_id = normalized_payload["paper_id"]
                extraction_id, existed = persist_staging_extraction(
                    connection=connection,
                    paper_id=paper_id,
                    run=run,
                    normalized_payload=normalized_payload,
                )
                promotion_summary = promote_to_mechanism_store(
                    connection=connection,
                    extraction_id=extraction_id,
                    run=run,
                    normalized_payload=normalized_payload,
                )

                if existed:
                    updated += 1
                else:
                    inserted += 1
                mechanism_inserted += promotion_summary["mechanism_inserted"]
                mechanism_updated += promotion_summary["mechanism_updated"]
                evidence_spans_written += promotion_summary["evidence_spans_written"]

        run_status = "ingested" if invalid == 0 else "ingested_with_errors"
        connection.execute(
            """
            UPDATE extraction_runs
            SET run_status = ?, completed_at = ?
            WHERE run_id = ?
            """,
            (run_status, now_utc(), run["run_id"]),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "inserted": inserted,
        "updated": updated,
        "invalid": invalid,
        "mechanism_inserted": mechanism_inserted,
        "mechanism_updated": mechanism_updated,
        "evidence_spans_written": evidence_spans_written,
        "errors": errors,
    }


def write_ingest_artifacts(run_dir: Path, responses_path: Path, summary):
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "ingest_summary.json"
    errors_path = run_dir / "ingest_errors.jsonl"

    payload = {
        "responses_path": str(responses_path.resolve()),
        "inserted": summary["inserted"],
        "updated": summary["updated"],
        "invalid": summary["invalid"],
        "mechanism_inserted": summary["mechanism_inserted"],
        "mechanism_updated": summary["mechanism_updated"],
        "evidence_spans_written": summary["evidence_spans_written"],
        "errors_path": str(errors_path.resolve()),
    }
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with errors_path.open("w", encoding="utf-8") as handle:
        for error in summary["errors"]:
            handle.write(json.dumps(error, sort_keys=True) + "\n")

    return summary_path


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    responses_path = Path(args.responses_path).resolve()
    schema = load_json(Path(args.schema_path).resolve())

    connection = sqlite3.connect(str(db_path))
    try:
        run = load_run(connection, args.run_id)
        summary = ingest(
            connection=connection,
            schema=schema,
            run=run,
            responses_path=responses_path,
        )
    finally:
        connection.close()

    run_dir = ROOT / "data" / "structural-analogy" / "runs" / args.run_id
    summary_path = write_ingest_artifacts(
        run_dir=run_dir,
        responses_path=responses_path,
        summary=summary,
    )
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
