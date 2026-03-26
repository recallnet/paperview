#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from validate_schema_examples import SchemaValidationError, load_json, validate


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "extraction.schema.json"

BLOCKING_FLAGS = {
    "parse_not_ok",
    "generic_model_paper_fit_too_high",
    "generic_model_paper_prediction_portability_too_high",
    "generic_model_paper_novel_portability_too_high",
    "no_executor_mechanism_but_high_tradecore_fit",
    "prediction_market_domain_not_supported",
    "high_fit_without_specific_why_missed",
    "placeholder_mechanism_name",
    "candidate_missing_specific_blocker_context",
}

WARNING_FLAG_PREFIXES = {
    "domain_not_supported:",
}

BLOCKING_FLAG_PREFIXES = {
    "schema_invalid:",
}

GENERIC_MODEL_TERMS = [
    "prediction model",
    "predict",
    "forecast",
    "risk prediction",
    "portfolio risk",
    "portfolio optimization",
    "cnn",
    "neural network",
    "machine learning",
    "deep learning",
    "image processing",
]

TRADECORE_MECHANISM_TERMS = [
    "arbitrage",
    "market making",
    "limit order book",
    "liquidity",
    "order flow",
    "cross-venue",
    "parity",
    "pricing inconsistency",
    "basket",
    "implied probability",
    "settlement",
]

DOMAIN_KEYWORDS = {
    "decentralized_finance": [
        "defi",
        "decentralized finance",
        "dao",
        "decentralized autonomous organization",
        "blockchain",
        "amm",
        "on-chain",
        "onchain",
        "token",
        "smart contract",
        "liquidity pool",
    ],
    "prediction_markets": ["prediction market", "event market", "binary contract", "yes/no market"],
    "auction_design": ["auction", "bidding", "allocation mechanism"],
    "market_microstructure": ["order book", "bid-ask", "microstructure", "market maker"],
}

PROMISING_BANDS = {"medium", "high"}
SPECIFICITY_ARRAY_FIELDS = [
    "fragility_flags",
    "capacity_constraints",
    "failure_regimes",
    "negative_transfer_rationale",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Review extraction outputs for semantic quality issues."
    )
    parser.add_argument(
        "--responses-path",
        required=True,
        help="Path to responses JSONL from a model run.",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Optional explicit output report path. Defaults next to the responses file.",
    )
    parser.add_argument(
        "--fail-on-blocking",
        action="store_true",
        help="Exit non-zero when any blocking findings are present.",
    )
    parser.add_argument(
        "--schema-path",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to the extraction schema used for structural validation.",
    )
    return parser.parse_args()


def load_rows(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def contains_any(text: str, needles):
    haystack = text.lower()
    return any(needle in haystack for needle in needles)


def compact_schema_error(error: str):
    head = error.strip().replace("\n", " ")
    if len(head) > 120:
        head = head[:117] + "..."
    return f"schema_invalid:{head}"


def has_specific_non_other(values):
    if not isinstance(values, list):
        return False
    return any(str(value).strip().lower() not in {"", "other"} for value in values)


def assess_row(row, schema):
    extraction = dict(row.get("extraction") or {})
    if "paper_id" not in extraction and "paper_id" in row:
        extraction["paper_id"] = row["paper_id"]

    abstract_like = f"{row.get('prompt', '')}\n{row.get('raw_text', '')}".lower()
    flags = []

    if row.get("parse_status") != "ok":
        flags.append("parse_not_ok")
        return flags

    try:
        validate(schema, extraction)
    except SchemaValidationError as exc:
        flags.append(compact_schema_error(str(exc)))

    has_generic_terms = contains_any(abstract_like, GENERIC_MODEL_TERMS)
    has_tradecore_mechanism_terms = contains_any(abstract_like, TRADECORE_MECHANISM_TERMS)

    if has_generic_terms and not has_tradecore_mechanism_terms:
        if extraction.get("tradecore_fit") in {"high", "medium"}:
            flags.append("generic_model_paper_fit_too_high")
        if extraction.get("prediction_market_portability") in {"medium", "high"}:
            flags.append("generic_model_paper_prediction_portability_too_high")
        if extraction.get("novel_market_portability") == "high":
            flags.append("generic_model_paper_novel_portability_too_high")

    if not has_tradecore_mechanism_terms:
        if extraction.get("tradecore_fit") == "high":
            flags.append("no_executor_mechanism_but_high_tradecore_fit")

    domain = extraction.get("original_market_domain")
    if domain in DOMAIN_KEYWORDS:
        if not contains_any(abstract_like, DOMAIN_KEYWORDS[domain]):
            flags.append(f"domain_not_supported:{domain}")

    if domain == "prediction_markets" and not contains_any(
        abstract_like, DOMAIN_KEYWORDS["prediction_markets"]
    ):
        flags.append("prediction_market_domain_not_supported")

    if extraction.get("why_missed") == ["other"] and extraction.get("tradecore_fit") == "high":
        flags.append("high_fit_without_specific_why_missed")

    promising_candidate = (
        extraction.get("tradecore_fit") in PROMISING_BANDS
        or extraction.get("prediction_market_portability") in PROMISING_BANDS
        or extraction.get("novel_market_portability") in PROMISING_BANDS
    )
    # @context requirement -- C02 requires promising candidates to carry explicit blocker context.
    # Otherwise later ranking work can only promote "interesting" outputs without a falsifiable
    # anti-transfer surface, which breaks the candidate-queue gate the canonical plan depends on.
    if promising_candidate and not any(
        has_specific_non_other(extraction.get(field)) for field in SPECIFICITY_ARRAY_FIELDS
    ):
        flags.append("candidate_missing_specific_blocker_context")

    mechanism_name = str(extraction.get("mechanism_name") or "").strip().lower()
    if mechanism_name in {"", "none", "n/a", "unknown", "null"}:
        flags.append("placeholder_mechanism_name")

    return flags


def classify_flags(flags):
    blocking = []
    warnings = []

    for flag in flags:
        if flag in BLOCKING_FLAGS:
            blocking.append(flag)
            continue
        if any(flag.startswith(prefix) for prefix in BLOCKING_FLAG_PREFIXES):
            blocking.append(flag)
            continue
        if any(flag.startswith(prefix) for prefix in WARNING_FLAG_PREFIXES):
            warnings.append(flag)
            continue
        warnings.append(flag)

    return blocking, warnings


def build_report(rows, schema):
    reviewed = []
    flagged = 0
    blocking_items = 0
    warning_items = 0
    for row in rows:
        flags = assess_row(row, schema)
        blocking_flags, warning_flags = classify_flags(flags)
        payload = {
            "paper_id": row.get("paper_id"),
            "parse_status": row.get("parse_status"),
            "flags": flags,
            "blocking_flags": blocking_flags,
            "warning_flags": warning_flags,
            "gate_status": "blocking" if blocking_flags else ("warning" if warning_flags else "pass"),
            "extraction": row.get("extraction"),
        }
        if flags:
            flagged += 1
        if blocking_flags:
            blocking_items += 1
        elif warning_flags:
            warning_items += 1
        reviewed.append(payload)

    return {
        "reviewed_count": len(reviewed),
        "flagged_count": flagged,
        "flagged_ratio": (flagged / len(reviewed)) if reviewed else 0.0,
        "blocking_count": blocking_items,
        "warning_count": warning_items,
        "gate_status": "blocking" if blocking_items else ("warning" if warning_items else "pass"),
        "items": reviewed,
    }


def main():
    args = parse_args()
    responses_path = Path(args.responses_path).resolve()
    report_path = (
        Path(args.report_path).resolve()
        if args.report_path
        else responses_path.with_suffix(".quality.json")
    )
    schema = load_json(Path(args.schema_path).resolve())

    rows = load_rows(responses_path)
    report = build_report(rows, schema)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(report_path.read_text(encoding="utf-8").strip())

    if args.fail_on_blocking and report["blocking_count"] > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
