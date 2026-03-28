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
    parser = argparse.ArgumentParser(description="Ingest shortlist-gated selective interpretations with strict JSON validation.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="selective-interpretation-ingestion-20260328")
    parser.add_argument("--shortlist-run-id", default="shortlist-materialization-20260328")
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


def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_response_line(line: str) -> tuple[str | None, dict | None, str | None]:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        return None, None, f"invalid_json:{exc}"
    if not isinstance(payload, dict):
        return None, None, "payload_not_object"
    shortlist_id = payload.get("shortlist_id")
    if not shortlist_id or not isinstance(shortlist_id, str):
        return None, None, "missing_shortlist_id"
    interpretation = payload.get("interpretation", payload)
    if not isinstance(interpretation, dict):
        return shortlist_id, None, "interpretation_not_object"
    interpretation = {key: value for key, value in interpretation.items() if key != "shortlist_id"}
    return shortlist_id, interpretation, None


def validate_interpretation(schema: dict, interpretation: dict) -> str | None:
    # @context decision -- The ingestion surface enforces the checked-in schema directly so later
    # model runners cannot sneak in prose, extra fields, or unsupported classes without creating a
    # rejection artifact. This keeps the negative class and allowed outputs canonical.
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


def shortlist_exists(connection: sqlite3.Connection, shortlist_run_id: str, shortlist_id: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM shortlist_items
        WHERE run_id = ?
          AND shortlist_id = ?
        """,
        (shortlist_run_id, shortlist_id),
    ).fetchone()
    return row is not None


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    responses_path = Path(args.responses_path).resolve()
    schema_path = Path(args.schema_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    schema = load_schema(schema_path)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        log_run_event(
            connection,
            args.run_id,
            "selective_interpretation",
            "started",
            {
                "shortlist_run_id": args.shortlist_run_id,
                "responses_path": str(responses_path),
                "schema_path": str(schema_path),
            },
        )
        connection.execute("DELETE FROM selective_interpretations WHERE run_id = ?", (args.run_id,))

        accepted = 0
        rejected = 0
        counts_by_classification: dict[str, int] = {}
        rejection_path = output_dir / "interpretation_rejections.jsonl"
        with responses_path.open("r", encoding="utf-8") as handle, rejection_path.open("w", encoding="utf-8") as rejection_handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                shortlist_id, interpretation, parse_error = parse_response_line(line)
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
                if not shortlist_exists(connection, args.shortlist_run_id, shortlist_id):
                    rejected += 1
                    rejection_handle.write(
                        json.dumps(
                            {
                                "line_number": line_number,
                                "shortlist_id": shortlist_id,
                                "reason": "unknown_shortlist_id",
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
                                "shortlist_id": shortlist_id,
                                "reason": validation_error,
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    continue

                classification = interpretation["classification"]
                # @context requirement -- Only shortlist-linked rows may be stored. Even valid JSON
                # must be rejected if it is not tied to an existing shortlist id for the target run.
                counts_by_classification[classification] = counts_by_classification.get(classification, 0) + 1
                connection.execute(
                    """
                    INSERT INTO selective_interpretations (
                      run_id,
                      shortlist_run_id,
                      shortlist_id,
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        args.run_id,
                        args.shortlist_run_id,
                        shortlist_id,
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
            "shortlist_run_id": args.shortlist_run_id,
            "accepted_count": accepted,
            "rejected_count": rejected,
            "counts_by_classification": counts_by_classification,
            "responses_path": str(responses_path),
            "schema_path": str(schema_path),
        }
        metrics_path = output_dir / "interpretation_ingestion_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "selective_interpretation", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
