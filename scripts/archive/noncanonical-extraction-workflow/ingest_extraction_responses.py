#!/usr/bin/env python3

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

EDGE_RESET_DIR = Path(__file__).resolve().parent.parent / "noncanonical-edge-reset"
if str(EDGE_RESET_DIR) not in sys.path:
    # @context requirement -- edge_semantic_validity moved with the archived
    # edge-reset workflow, so archived extraction ingestion has to import that
    # helper from the archive instead of the old root-level path.
    sys.path.insert(0, str(EDGE_RESET_DIR))

from edge_semantic_validity import semantic_validity
from validate_schema_examples import SchemaValidationError, load_json, validate


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "extraction.schema.json"
DEFAULT_EDGE_SCHEMA_PATH = ROOT / "schemas" / "edge_extraction.schema.json"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"
REQUIRED_EDGE_FIELDS = (
    "invariant_statement",
    "market_object",
    "wrong_actor",
    "why_persistence",
    "cheap_validation_step",
)
EDGE_SCHEMA_FIELDS = {
    "invariant_type",
    "invariant_statement",
    "market_object",
    "trigger_window",
    "market_lifecycle_phase",
    "wrong_actor",
    "why_wrong",
    "why_persistence",
    "closure_mechanism",
    "death_condition",
    "executor_gap",
    "cheap_validation_step",
    "fast_falsifier",
    "novelty_reason",
    "composition_opportunity",
    "edge_confidence",
}
MEANINGFUL_EXTRACTION_FIELDS = REQUIRED_EDGE_FIELDS + (
    "mechanism_name",
    "mechanism_summary",
)
ABSTAIN_REASONS = {
    "no_edge_hypothesis",
    "paper_describes_general_market_property_only",
    "paper_describes_theory_without_tradeable_monitorable_implication",
}


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
    parser.add_argument(
        "--edge-schema-path",
        default=str(DEFAULT_EDGE_SCHEMA_PATH),
        help="Path to the edge extraction JSON schema.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def has_explicit_value(value):
    if value is None:
        return False
    if isinstance(value, list):
        return any(has_explicit_value(item) for item in value)
    return bool(str(value).strip())


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
    required_columns = {
        "invariant_type": "TEXT NOT NULL DEFAULT 'other'",
        "invariant_statement": "TEXT",
        "market_object": "TEXT",
        "trigger_window": "TEXT",
        "market_lifecycle_phase": "TEXT NOT NULL DEFAULT 'unknown'",
        "wrong_actor": "TEXT",
        "why_wrong": "TEXT",
        "why_persistence": "TEXT",
        "closure_mechanism": "TEXT",
        "death_condition": "TEXT",
        "executor_gap": "TEXT",
        "cheap_validation_step": "TEXT",
        "fast_falsifier": "TEXT",
        "novelty_reason": "TEXT",
        "composition_opportunity": "TEXT",
        "edge_confidence": "TEXT NOT NULL DEFAULT 'speculative'",
        "evidence_confidence": "TEXT NOT NULL DEFAULT 'unscored'",
    }
    for column_name, ddl_fragment in required_columns.items():
        if column_name not in columns:
            connection.execute(
                f"ALTER TABLE mechanism_instances ADD COLUMN {column_name} {ddl_fragment}"
            )


def infer_legacy_insight_type(extraction):
    def scalarize(value, default="low"):
        if value is None:
            return default
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item.strip().lower()
            return default
        if isinstance(value, str):
            stripped = value.strip()
            return stripped.lower() if stripped else default
        return str(value).strip().lower() or default

    tradecore_fit = scalarize(extraction.get("tradecore_fit", "low"))
    prediction_portability = scalarize(
        extraction.get("prediction_market_portability", "low")
    )
    novel_portability = scalarize(extraction.get("novel_market_portability", "low"))
    if tradecore_fit == "high" and (
        prediction_portability in {"medium", "high"} or novel_portability in {"medium", "high"}
    ):
        return "executable_strategy_primitive"
    if tradecore_fit in {"medium", "high"}:
        return "missing_executor_primitive"
    return "research_dead_end_worth_excluding"


def extraction_completeness(extraction):
    meaningful_values = [
        field_name
        for field_name in MEANINGFUL_EXTRACTION_FIELDS
        if has_explicit_value(extraction.get(field_name))
    ]
    present_fields = [
        field_name
        for field_name in REQUIRED_EDGE_FIELDS
        if has_explicit_value(extraction.get(field_name))
    ]
    if not meaningful_values:
        return {
            "status": "extraction_empty",
            "present_fields": present_fields,
            "present_count": 0,
        }
    if len(present_fields) < 3:
        return {
            "status": "extraction_insufficient",
            "present_fields": present_fields,
            "present_count": len(present_fields),
        }
    return {
        "status": "complete",
        "present_fields": present_fields,
        "present_count": len(present_fields),
    }


def extraction_semantic_completeness(extraction):
    explicit_required = [
        field_name
        for field_name in REQUIRED_EDGE_FIELDS
        if has_explicit_value(extraction.get(field_name))
    ]
    if len(explicit_required) < len(REQUIRED_EDGE_FIELDS):
        return {
            "status": "extraction_semantic_insufficient",
            "present_fields": explicit_required,
            "failure_reasons": ["missing_required_edge_fields"],
        }
    semantic = semantic_validity(extraction)
    if not semantic["semantic_valid"]:
        return {
            "status": "extraction_semantic_insufficient",
            "present_fields": explicit_required,
            "failure_reasons": semantic["semantic_failure_reasons"],
        }
    return {
        "status": "complete",
        "present_fields": explicit_required,
        "failure_reasons": [],
    }


def upgrade_legacy_extraction_contract(extraction):
    upgraded = dict(extraction)
    defaults = {
        "insight_type": infer_legacy_insight_type(extraction),
        "invariant_type": "other",
        "trigger_window": "",
        "market_lifecycle_phase": "unknown",
        "edge_confidence": "speculative",
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
        completeness = extraction_completeness(extraction)
        if completeness["status"] == "complete":
            completeness = extraction_semantic_completeness(extraction)
        return {
            "paper_id": extraction["paper_id"],
            "contract_version": "legacy-single-mechanism-v1",
            "mechanism_instances": [extraction] if completeness["status"] == "complete" else [],
            "validation_status": completeness["status"],
            "staging_payload": extraction,
        }

    if "mechanism_instances" in payload:
        paper_id = payload.get("paper_id")
        abstain_reason = payload.get("abstain_reason")
        abstain_explanation = payload.get("abstain_explanation")
        if not isinstance(payload["mechanism_instances"], list):
            raise SchemaValidationError("$.mechanism_instances: expected array")

        normalized_instances = []
        statuses = []
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
            completeness = extraction_completeness(normalized)
            if completeness["status"] == "complete":
                semantic_completeness = extraction_semantic_completeness(normalized)
                statuses.append(semantic_completeness["status"])
                if semantic_completeness["status"] == "complete":
                    normalized_instances.append(normalized)
            else:
                statuses.append(completeness["status"])

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
            "validation_status": (
                "valid"
                if normalized_instances
                else abstain_reason
                if abstain_reason in ABSTAIN_REASONS
                else "extraction_empty"
                if statuses and all(status == "extraction_empty" for status in statuses)
                else "extraction_semantic_insufficient"
                if statuses and all(status == "extraction_semantic_insufficient" for status in statuses)
                else "extraction_insufficient"
            ),
            "staging_payload": {
                "paper_id": paper_id,
                "response_contract_version": payload.get(
                    "response_contract_version",
                    "mechanism-instance-batch-v1",
                ),
                "abstain_reason": abstain_reason,
                "abstain_explanation": abstain_explanation,
                "mechanism_instances": normalized_instances,
            },
        }

    if "paper_id" not in payload:
        raise SchemaValidationError("$.paper_id: missing required key 'paper_id'")

    payload = upgrade_legacy_extraction_contract(payload)
    completeness = extraction_completeness(payload)
    if completeness["status"] == "complete":
        completeness = extraction_semantic_completeness(payload)
    return {
        "paper_id": payload["paper_id"],
        "contract_version": "legacy-single-mechanism-v1",
        "mechanism_instances": [payload] if completeness["status"] == "complete" else [],
        "validation_status": completeness["status"],
        "staging_payload": payload,
    }


def choose_schema(extraction, base_schema, edge_schema):
    if any(key in extraction for key in EDGE_SCHEMA_FIELDS):
        return edge_schema
    return base_schema


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
            normalized_payload.get("validation_status", "valid"),
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
    field_provenance = {
        field_name: (
            "explicit_from_model" if has_explicit_value(extraction.get(field_name)) else "missing"
        )
        for field_name in (
            "invariant_statement",
            "market_object",
            "trigger_window",
            "wrong_actor",
            "why_wrong",
            "why_persistence",
            "closure_mechanism",
            "death_condition",
            "executor_gap",
            "cheap_validation_step",
            "fast_falsifier",
            "novelty_reason",
            "composition_opportunity",
        )
    }
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
        "invariant_type": extraction["invariant_type"],
        "invariant_statement": extraction["invariant_statement"],
        "market_object": extraction["market_object"],
        "trigger_window": extraction["trigger_window"],
        "market_lifecycle_phase": extraction["market_lifecycle_phase"],
        "wrong_actor": extraction["wrong_actor"],
        "why_wrong": extraction["why_wrong"],
        "why_persistence": extraction["why_persistence"],
        "closure_mechanism": extraction["closure_mechanism"],
        "death_condition": extraction["death_condition"],
        "executor_gap": extraction["executor_gap"],
        "cheap_validation_step": extraction["cheap_validation_step"],
        "fast_falsifier": extraction["fast_falsifier"],
        "novelty_reason": extraction["novelty_reason"],
        "composition_opportunity": extraction["composition_opportunity"],
        "edge_confidence": extraction["edge_confidence"],
        "field_provenance": field_provenance,
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
        extraction["invariant_type"],
        extraction["invariant_statement"],
        extraction["market_object"],
        extraction["trigger_window"],
        extraction["market_lifecycle_phase"],
        extraction["wrong_actor"],
        extraction["why_wrong"],
        extraction["why_persistence"],
        extraction["closure_mechanism"],
        extraction["death_condition"],
        extraction["executor_gap"],
        extraction["cheap_validation_step"],
        extraction["fast_falsifier"],
        extraction["novelty_reason"],
        extraction["composition_opportunity"],
        extraction["edge_confidence"],
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
              invariant_type,
              invariant_statement,
              market_object,
              trigger_window,
              market_lifecycle_phase,
              wrong_actor,
              why_wrong,
              why_persistence,
              closure_mechanism,
              death_condition,
              executor_gap,
              cheap_validation_step,
              fast_falsifier,
              novelty_reason,
              composition_opportunity,
              edge_confidence,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                invariant_type = ?,
                invariant_statement = ?,
                market_object = ?,
                trigger_window = ?,
                market_lifecycle_phase = ?,
                wrong_actor = ?,
                why_wrong = ?,
                why_persistence = ?,
                closure_mechanism = ?,
                death_condition = ?,
                executor_gap = ?,
                cheap_validation_step = ?,
                fast_falsifier = ?,
                novelty_reason = ?,
                composition_opportunity = ?,
                edge_confidence = ?,
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
                extraction["invariant_type"],
                extraction["invariant_statement"],
                extraction["market_object"],
                extraction["trigger_window"],
                extraction["market_lifecycle_phase"],
                extraction["wrong_actor"],
                extraction["why_wrong"],
                extraction["why_persistence"],
                extraction["closure_mechanism"],
                extraction["death_condition"],
                extraction["executor_gap"],
                extraction["cheap_validation_step"],
                extraction["fast_falsifier"],
                extraction["novelty_reason"],
                extraction["composition_opportunity"],
                extraction["edge_confidence"],
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


def supersede_active_mechanisms_for_paper(connection, paper_id: str):
    connection.execute(
        """
        UPDATE mechanism_instances
        SET lifecycle_status = 'superseded',
            updated_at = ?
        WHERE paper_id = ?
          AND lifecycle_status = 'active'
        """,
        (now_utc(), paper_id),
    )


def promote_to_mechanism_store(connection, extraction_id: int, run, normalized_payload):
    paper_id = normalized_payload["paper_id"]
    if not normalized_payload["mechanism_instances"]:
        # @context risk -- Fail-closed reruns must remove stale active
        # mechanisms for papers whose latest extraction is empty or
        # insufficient. Otherwise old junk survives downstream even though the
        # new contract explicitly rejected it.
        supersede_active_mechanisms_for_paper(connection, paper_id)
        reconcile_benchmark_pairs(connection, paper_id)
        return {
            "mechanism_inserted": 0,
            "mechanism_updated": 0,
            "evidence_spans_written": 0,
        }
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
    extraction_empty = 0
    extraction_insufficient = 0
    mechanism_inserted = 0
    mechanism_updated = 0
    evidence_spans_written = 0
    errors = []
    edge_schema = load_json(DEFAULT_EDGE_SCHEMA_PATH)

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
                    paper_id = raw_payload.get("paper_id")
                    if paper_id:
                        supersede_active_mechanisms_for_paper(connection, paper_id)
                    errors.append(
                        {
                            "line_number": line_number,
                            "paper_id": paper_id,
                            "error": str(exc),
                        }
                    )
                    continue

                is_valid = True
                for extraction in normalized_payload["mechanism_instances"]:
                    chosen_schema = choose_schema(extraction, schema, edge_schema)
                    try:
                        validate(chosen_schema, extraction)
                    except SchemaValidationError as exc:
                        invalid += 1
                        if extraction.get("paper_id"):
                            supersede_active_mechanisms_for_paper(
                                connection, extraction.get("paper_id")
                            )
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

                if normalized_payload.get("validation_status") == "extraction_empty":
                    extraction_empty += 1
                elif normalized_payload.get("validation_status") == "extraction_insufficient":
                    extraction_insufficient += 1

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
        "extraction_empty": extraction_empty,
        "extraction_insufficient": extraction_insufficient,
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
