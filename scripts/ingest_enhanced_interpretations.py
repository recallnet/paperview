#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "selective_interpretation.schema.json"


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest enhanced S23 interpretations with strict JSON validation.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="enhanced-interpretation-ingestion-20260328")
    parser.add_argument("--batch-run-id", default="enhanced-interpretation-batch-20260328")
    parser.add_argument("--batch-path", default=None)
    parser.add_argument("--responses-path", required=True)
    parser.add_argument("--schema-path", default=str(DEFAULT_SCHEMA_PATH))
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def ensure_enhanced_interpretations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS enhanced_interpretations (
          run_id TEXT NOT NULL,
          batch_run_id TEXT NOT NULL,
          batch_item_id TEXT NOT NULL,
          operator_family TEXT NOT NULL,
          source_kind TEXT NOT NULL,
          source_run_id TEXT NOT NULL,
          source_ref TEXT NOT NULL,
          family_rank INTEGER NOT NULL,
          source_score REAL NOT NULL,
          packet_title TEXT NOT NULL,
          classification TEXT NOT NULL,
          result_summary TEXT NOT NULL,
          first_step TEXT NOT NULL,
          instrument_assumed TEXT NOT NULL,
          modern_equivalent TEXT NOT NULL,
          why_stranded_or_unrealized TEXT NOT NULL,
          gap_to_close TEXT NOT NULL,
          confidence TEXT NOT NULL,
          raw_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, batch_item_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_enhanced_interpretations_run_classification
        ON enhanced_interpretations (run_id, classification)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_enhanced_interpretations_run_family
        ON enhanced_interpretations (run_id, operator_family, family_rank)
        """
    )


def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_batch_lookup(path: Path) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            batch_item_id = payload.get("batch_item_id")
            if not isinstance(batch_item_id, str) or not batch_item_id:
                raise ValueError(f"missing_batch_item_id_in_batch:{line_number}")
            if batch_item_id in lookup:
                raise ValueError(f"duplicate_batch_item_id_in_batch:{batch_item_id}")
            lookup[batch_item_id] = payload
    return lookup


def parse_response_line(line: str) -> tuple[str | None, dict | None, str | None]:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        return None, None, f"invalid_json:{exc}"
    if not isinstance(payload, dict):
        return None, None, "payload_not_object"
    batch_item_id = payload.get("batch_item_id")
    if not batch_item_id or not isinstance(batch_item_id, str):
        return None, None, "missing_batch_item_id"
    interpretation = payload.get("interpretation", payload)
    if not isinstance(interpretation, dict):
        return batch_item_id, None, "interpretation_not_object"
    interpretation = {key: value for key, value in interpretation.items() if key != "batch_item_id"}
    return batch_item_id, interpretation, None


def validate_interpretation(schema: dict, interpretation: dict) -> str | None:
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        extras = set(interpretation.keys()) - set(properties.keys())
        if extras:
            return f"unexpected_fields:{','.join(sorted(extras))}"
    missing = [field for field in schema.get("required", []) if field not in interpretation]
    if missing:
        return f"missing_fields:{','.join(missing)}"
    for field in required:
        value = interpretation.get(field)
        rule = properties.get(field, {})
        if not isinstance(value, str):
            return f"field_not_string:{field}"
        if len(value) < int(rule.get("minLength", 0)):
            return f"field_too_short:{field}"
        if "enum" in rule and value not in rule["enum"]:
            return f"invalid_enum:{field}:{value}"
    return None


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    responses_path = Path(args.responses_path).resolve()
    schema_path = Path(args.schema_path).resolve()
    batch_path = (
        Path(args.batch_path).resolve()
        if args.batch_path
        else DEFAULT_OUTPUT_ROOT / args.batch_run_id / "enhanced_interpretation_batch.jsonl"
    )
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    schema = load_schema(schema_path)
    batch_lookup = load_batch_lookup(batch_path)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_enhanced_interpretations_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "enhanced_interpretation",
            "started",
            {
                "batch_run_id": args.batch_run_id,
                "batch_path": str(batch_path),
                "responses_path": str(responses_path),
                "schema_path": str(schema_path),
            },
        )
        connection.execute("DELETE FROM enhanced_interpretations WHERE run_id = ?", (args.run_id,))

        accepted = 0
        rejected = 0
        counts_by_classification: dict[str, int] = {}
        counts_by_operator_family: dict[str, int] = {}
        rejection_path = output_dir / "enhanced_interpretation_rejections.jsonl"
        with responses_path.open("r", encoding="utf-8") as handle, rejection_path.open("w", encoding="utf-8") as rejection_handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                batch_item_id, interpretation, parse_error = parse_response_line(line)
                if parse_error is not None:
                    rejected += 1
                    rejection_handle.write(
                        json.dumps(
                            {
                                "line_number": line_number,
                                "reason": parse_error,
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    continue
                batch_item = batch_lookup.get(batch_item_id)
                if batch_item is None:
                    rejected += 1
                    rejection_handle.write(
                        json.dumps(
                            {
                                "line_number": line_number,
                                "batch_item_id": batch_item_id,
                                "reason": "unknown_batch_item_id",
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    continue
                validation_error = validate_interpretation(schema, interpretation)
                if validation_error is not None:
                    rejected += 1
                    rejection_handle.write(
                        json.dumps(
                            {
                                "line_number": line_number,
                                "batch_item_id": batch_item_id,
                                "reason": validation_error,
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    continue

                # @context decision -- S23 must widen interpretation coverage without weakening the
                # S12 shortlist gate. The enhanced ingestion path therefore validates against the
                # checked-in expanded batch artifact and stores accepted rows in a parallel table
                # keyed by batch ids, so later publication stages can opt in explicitly instead of
                # silently widening the original shortlist-backed surfaces.
                classification = interpretation["classification"]
                operator_family = str(batch_item["operator_family"])
                counts_by_classification[classification] = counts_by_classification.get(classification, 0) + 1
                counts_by_operator_family[operator_family] = counts_by_operator_family.get(operator_family, 0) + 1
                connection.execute(
                    """
                    INSERT INTO enhanced_interpretations (
                      run_id,
                      batch_run_id,
                      batch_item_id,
                      operator_family,
                      source_kind,
                      source_run_id,
                      source_ref,
                      family_rank,
                      source_score,
                      packet_title,
                      classification,
                      result_summary,
                      first_step,
                      instrument_assumed,
                      modern_equivalent,
                      why_stranded_or_unrealized,
                      gap_to_close,
                      confidence,
                      raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        args.run_id,
                        args.batch_run_id,
                        batch_item_id,
                        operator_family,
                        str(batch_item["source_kind"]),
                        str(batch_item["source_run_id"]),
                        str(batch_item["source_ref"]),
                        int(batch_item["family_rank"]),
                        float(batch_item["score"]),
                        str(batch_item["packet_title"]),
                        classification,
                        interpretation["result_summary"],
                        interpretation["first_step"],
                        interpretation["instrument_assumed"],
                        interpretation["modern_equivalent"],
                        interpretation["why_stranded_or_unrealized"],
                        interpretation["gap_to_close"],
                        interpretation["confidence"],
                        json.dumps(interpretation, sort_keys=True),
                    ),
                )
                accepted += 1

        metrics = {
            "run_id": args.run_id,
            "batch_run_id": args.batch_run_id,
            "accepted_count": accepted,
            "rejected_count": rejected,
            "counts_by_classification": counts_by_classification,
            "counts_by_operator_family": counts_by_operator_family,
            "responses_path": str(responses_path),
            "batch_path": str(batch_path),
            "schema_path": str(schema_path),
        }
        metrics_path = output_dir / "enhanced_interpretation_ingestion_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "enhanced_interpretation", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
