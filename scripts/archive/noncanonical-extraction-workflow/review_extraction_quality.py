#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from ingest_extraction_responses import normalize_line
from validate_schema_examples import SchemaValidationError, load_json, validate


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "extraction.schema.json"

BLOCKING_FLAGS = {
    "parse_not_ok",
    "empty_mechanism_batch_for_market_signal",
    "generic_model_paper_fit_too_high",
    "generic_model_paper_prediction_portability_too_high",
    "generic_model_paper_novel_portability_too_high",
    "no_executor_mechanism_but_high_tradecore_fit",
    "off_domain_paper_not_collapsed",
    "prediction_market_domain_not_supported",
    "high_fit_without_specific_why_missed",
    "placeholder_mechanism_name",
    "candidate_missing_specific_blocker_context",
}
VALID_ABSTAIN_REASONS = {
    "no_edge_hypothesis",
    "paper_describes_general_market_property_only",
    "paper_describes_theory_without_tradeable_monitorable_implication",
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
    "sports_betting": ["sports betting", "sportsbook", "betting market", "odds"],
    "pari_mutuel": ["pari-mutuel", "parimutuel", "horse racing", "tote"],
    "electricity": ["electricity market", "power market", "grid", "balancing market"],
    "weather": ["weather derivative", "weather market", "temperature contract"],
}

OFF_DOMAIN_TERMS = [
    "facility location",
    "route planning",
    "supply chain",
    "transportation network",
    "medical resource",
    "moral philosophy",
    "moral agent",
    "regulatory barrier",
    "country-year",
    "ai ethics",
]

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


def build_abstract_like(row):
    request_payload = row.get("request_payload") or {}
    if not isinstance(request_payload, dict):
        request_payload = {}
    return (
        f"{row.get('prompt', '')}\n"
        f"{row.get('raw_text', '')}\n"
        f"{request_payload.get('title', '')}\n"
        f"{request_payload.get('abstract', '')}\n"
        f"{request_payload.get('literature_family', '')}\n"
        f"{request_payload.get('primary_category', '')}"
    ).lower()


def scalar_band(value, default="low"):
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


def assess_extraction(extraction, abstract_like: str, schema):
    flags = []

    try:
        validate(schema, extraction)
    except SchemaValidationError as exc:
        flags.append(compact_schema_error(str(exc)))

    has_generic_terms = contains_any(abstract_like, GENERIC_MODEL_TERMS)
    has_tradecore_mechanism_terms = contains_any(abstract_like, TRADECORE_MECHANISM_TERMS)
    tradecore_fit = scalar_band(extraction.get("tradecore_fit"))
    prediction_portability = scalar_band(extraction.get("prediction_market_portability"))
    novel_portability = scalar_band(extraction.get("novel_market_portability"))

    if has_generic_terms and not has_tradecore_mechanism_terms:
        if tradecore_fit in {"high", "medium"}:
            flags.append("generic_model_paper_fit_too_high")
        if prediction_portability in {"medium", "high"}:
            flags.append("generic_model_paper_prediction_portability_too_high")
        if novel_portability == "high":
            flags.append("generic_model_paper_novel_portability_too_high")

    if not has_tradecore_mechanism_terms:
        if tradecore_fit == "high":
            flags.append("no_executor_mechanism_but_high_tradecore_fit")

    domain = extraction.get("original_market_domain")
    if domain in DOMAIN_KEYWORDS:
        if not contains_any(abstract_like, DOMAIN_KEYWORDS[domain]):
            flags.append(f"domain_not_supported:{domain}")

    if domain == "prediction_markets" and not contains_any(
        abstract_like, DOMAIN_KEYWORDS["prediction_markets"]
    ):
        flags.append("prediction_market_domain_not_supported")

    if extraction.get("why_missed") == ["other"] and tradecore_fit == "high":
        flags.append("high_fit_without_specific_why_missed")

    promising_candidate = (
        tradecore_fit in PROMISING_BANDS
        or prediction_portability in PROMISING_BANDS
        or novel_portability in PROMISING_BANDS
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


def has_market_signal(text: str):
    if contains_any(text, TRADECORE_MECHANISM_TERMS):
        return True
    for needles in DOMAIN_KEYWORDS.values():
        if contains_any(text, needles):
            return True
    return False


def assess_row(row, schema):
    abstract_like = build_abstract_like(row)
    if row.get("parse_status") != "ok":
        return {
            "paper_id": row.get("paper_id"),
            "mechanism_count": 0,
            "flags": ["parse_not_ok"],
            "mechanism_reviews": [],
        }

    try:
        normalized_payload = normalize_line(row)
    except (SchemaValidationError, KeyError) as exc:
        return {
            "paper_id": row.get("paper_id"),
            "mechanism_count": 0,
            "flags": [compact_schema_error(str(exc))],
            "mechanism_reviews": [],
        }

    paper_flags = []
    if (
        not normalized_payload["mechanism_instances"]
        and has_market_signal(abstract_like)
        and normalized_payload.get("staging_payload", {}).get("abstain_reason") not in VALID_ABSTAIN_REASONS
    ):
        # @context decision -- C06 allows `0..N` mechanism instances per paper, but an empty batch is
        # only acceptable when the abstract truly lacks transferable mechanism cues. Otherwise the
        # mixed-family runtime can hide retrieval-relevant mechanisms by collapsing them to nothing.
        paper_flags.append("empty_mechanism_batch_for_market_signal")

    mechanism_reviews = []
    for extraction in normalized_payload["mechanism_instances"]:
        flags = assess_extraction(extraction, abstract_like, schema)
        if contains_any(abstract_like, OFF_DOMAIN_TERMS) and (
            extraction.get("tradecore_fit") in PROMISING_BANDS
            or extraction.get("prediction_market_portability") in PROMISING_BANDS
            or extraction.get("novel_market_portability") in PROMISING_BANDS
        ):
            flags.append("off_domain_paper_not_collapsed")

        mechanism_reviews.append(
            {
                "paper_id": extraction.get("paper_id"),
                "mechanism_name": extraction.get("mechanism_name"),
                "flags": flags,
                "blocking_flags": classify_flags(flags)[0],
                "warning_flags": classify_flags(flags)[1],
                "gate_status": (
                    "blocking"
                    if classify_flags(flags)[0]
                    else ("warning" if classify_flags(flags)[1] else "pass")
                ),
                "extraction": extraction,
            }
        )

    return {
        "paper_id": normalized_payload["paper_id"],
        "mechanism_count": len(normalized_payload["mechanism_instances"]),
        "flags": paper_flags,
        "mechanism_reviews": mechanism_reviews,
    }


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
    mechanism_count = 0
    accepted_mechanism_count = 0
    accepted_with_evidence_and_blockers = 0
    unsupported_enum_count = 0
    ambiguous_normalization_count = 0
    for row in rows:
        assessment = assess_row(row, schema)
        blocking_flags, warning_flags = classify_flags(assessment["flags"])
        mechanism_has_blocking = any(
            review["blocking_flags"] for review in assessment["mechanism_reviews"]
        )
        mechanism_has_warning = any(
            review["warning_flags"] for review in assessment["mechanism_reviews"]
        )
        mechanism_count += assessment["mechanism_count"]
        for mechanism_review in assessment["mechanism_reviews"]:
            if any(
                flag.startswith("schema_invalid:") and "invalid enum value" in flag
                for flag in mechanism_review["flags"]
            ):
                unsupported_enum_count += 1
            if any(
                flag.startswith("domain_not_supported:")
                for flag in mechanism_review["flags"]
            ):
                ambiguous_normalization_count += 1
            if not mechanism_review["blocking_flags"] and not mechanism_review["warning_flags"]:
                accepted_mechanism_count += 1
                accepted_with_evidence_and_blockers += 1 if any(
                    has_specific_non_other(
                        mechanism_review["extraction"].get(field)
                    )
                    for field in SPECIFICITY_ARRAY_FIELDS
                ) else 0
        payload = {
            "paper_id": assessment["paper_id"],
            "parse_status": row.get("parse_status"),
            "flags": assessment["flags"],
            "blocking_flags": blocking_flags,
            "warning_flags": warning_flags,
            "gate_status": (
                "blocking"
                if blocking_flags or mechanism_has_blocking
                else (
                    "warning"
                    if warning_flags or mechanism_has_warning
                    else "pass"
                )
            ),
            "mechanism_count": assessment["mechanism_count"],
            "mechanism_reviews": assessment["mechanism_reviews"],
        }
        if assessment["flags"] or any(
            review["flags"] for review in assessment["mechanism_reviews"]
        ):
            flagged += 1
        if blocking_flags or mechanism_has_blocking:
            blocking_items += 1
        elif warning_flags or mechanism_has_warning:
            warning_items += 1
        reviewed.append(payload)

    return {
        "reviewed_count": len(reviewed),
        "mechanism_count": mechanism_count,
        "flagged_count": flagged,
        "flagged_ratio": (flagged / len(reviewed)) if reviewed else 0.0,
        "blocking_count": blocking_items,
        "warning_count": warning_items,
        "accepted_mechanism_count": accepted_mechanism_count,
        "semantic_pass_rate": (
            accepted_mechanism_count / mechanism_count
            if mechanism_count
            else 1.0
        ),
        "unsupported_enum_count": unsupported_enum_count,
        "unsupported_enum_ratio": (
            unsupported_enum_count / mechanism_count
            if mechanism_count
            else 0.0
        ),
        "ambiguous_normalization_count": ambiguous_normalization_count,
        "ambiguous_normalization_ratio": (
            ambiguous_normalization_count / mechanism_count
            if mechanism_count
            else 0.0
        ),
        "accepted_with_evidence_and_blockers_ratio": (
            accepted_with_evidence_and_blockers / accepted_mechanism_count
            if accepted_mechanism_count
            else 1.0
        ),
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
