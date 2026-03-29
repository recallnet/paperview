#!/usr/bin/env python3

import re


GENERIC_WRONG_ACTORS = {
    "agent",
    "agents",
    "trader",
    "traders",
    "arbitrageur",
    "arbitrageurs",
    "market participants",
    "participant",
    "participants",
    "investor",
    "investors",
    "none",
    "not applicable",
    "not explicit in provided text",
    "external shocks",
    "unspecified_actor",
    "institutions",
    "constant activity",
}

GENERIC_MARKET_OBJECTS = {
    "stock",
    "stocks",
    "price",
    "prices",
    "asset",
    "assets",
    "asset prices",
    "stock price",
    "stock prices",
    "market portfolio",
    "portfolio",
    "futures",
    "unspecified_market_object",
    "not applicable",
    "not explicit in provided text",
    "price and volume",
    "foreign exchange rates",
}

GENERIC_FILLERS = {
    "",
    "none",
    "none explicit",
    "not applicable",
    "not explicit in provided text",
    "unspecified_trigger_window",
    "unspecified_market_object",
    "unspecified_actor",
    "other",
}

SUMMARY_LIKE_PATTERNS = [
    r"\bthe paper\b",
    r"\bthe model\b",
    r"\bthe study\b",
    r"\bthis paper\b",
    r"\bthis model\b",
    r"\bmarket is complete\b",
    r"\bno arbitrage\b",
    r"\bpredicts simple laws\b",
    r"\bpower law\b",
    r"\bautocorrelation function\b",
    r"\blong[- ]memory\b",
    r"\bcorrelation properties\b",
    r"\bwell described by\b",
]

CHEAP_TEST_ACTION_PATTERNS = [
    r"\bmeasure\b",
    r"\bcompare\b",
    r"\bcondition\b",
    r"\bevent study\b",
    r"\breplay\b",
    r"\bbacktest\b",
    r"\bmonitor\b",
    r"\bregression\b",
    r"\bscan\b",
]

NON_ACTIONABLE_EXECUTOR_GAP_PATTERNS = [
    r"\bnot intelligent\b",
    r"\bmodel adjustments?\b",
    r"\bmissing primitive for immediate deployment\b",
    r"\baccount for arbitrage opportunities\b",
]

NON_ACTIONABLE_CHEAP_TEST_PATTERNS = [
    r"\bnon-dimensional coordinates\b",
    r"\bsimulation of the model\b",
    r"\bbacktest the model\b",
    r"\bstudy of\b",
    r"\bobservation of\b",
    r"\bnot applicable\b",
    r"\bnot explicit\b",
]

GENERAL_PROPERTY_PATTERNS = [
    r"\bpower law\b",
    r"\blong[- ]memory\b",
    r"\bcorrelation properties\b",
    r"\bstatistical properties of prices\b",
    r"\bmarket is complete with no arbitrage\b",
]


def normalize_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value if str(item).strip())
    return re.sub(r"\s+", " ", str(value)).strip()


def text_in(value, options):
    return normalize_text(value).lower() in options


def looks_summary_like(text):
    lowered = normalize_text(text).lower()
    return any(re.search(pattern, lowered) for pattern in SUMMARY_LIKE_PATTERNS)


def is_filler(text):
    return normalize_text(text).lower() in GENERIC_FILLERS


def cheap_test_is_actionable(text):
    lowered = normalize_text(text).lower()
    if lowered in GENERIC_FILLERS:
        return False
    if any(re.search(pattern, lowered) for pattern in NON_ACTIONABLE_CHEAP_TEST_PATTERNS):
        return False
    has_action = any(re.search(pattern, lowered) for pattern in CHEAP_TEST_ACTION_PATTERNS)
    has_market_detail = any(
        token in lowered
        for token in (
            "spread",
            "depth",
            "queue",
            "fill",
            "lag",
            "venue",
            "order flow",
            "slippage",
            "markout",
            "seconds",
            "milliseconds",
            "replay",
            "book",
        )
    )
    return has_action and has_market_detail


def executor_gap_is_actionable(text, why_persistence, death_condition):
    lowered = normalize_text(text).lower()
    if lowered in GENERIC_FILLERS:
        return False, "non_actionable_executor_gap"
    if lowered == normalize_text(why_persistence).lower() or lowered == normalize_text(death_condition).lower():
        return False, "executor_gap_tautology"
    if any(re.search(pattern, lowered) for pattern in NON_ACTIONABLE_EXECUTOR_GAP_PATTERNS):
        return False, "non_actionable_executor_gap"
    return True, None


def persistence_is_actionable(text):
    lowered = normalize_text(text).lower()
    if lowered in GENERIC_FILLERS:
        return False
    if lowered in {"market efficiency restored", "none", "not applicable"}:
        return False
    if "not explicit" in lowered or "not applicable" in lowered:
        return False
    return True


def looks_like_general_market_property(text):
    lowered = normalize_text(text).lower()
    return any(re.search(pattern, lowered) for pattern in GENERAL_PROPERTY_PATTERNS)


def semantic_failure_reasons(doc):
    reasons = []
    wrong_actor = normalize_text(doc.get("wrong_actor"))
    market_object = normalize_text(doc.get("market_object"))
    invariant_statement = normalize_text(doc.get("invariant_statement"))
    executor_gap = normalize_text(doc.get("executor_gap"))
    cheap_test = normalize_text(doc.get("cheap_validation_step"))
    why_persistence = normalize_text(doc.get("why_persistence"))
    death_condition = normalize_text(doc.get("death_condition"))
    fast_falsifier = normalize_text(doc.get("fast_falsifier"))

    filler_fields = sum(
        1
        for value in (
            wrong_actor,
            market_object,
            invariant_statement,
            why_persistence,
            executor_gap,
            cheap_test,
            fast_falsifier,
        )
        if is_filler(value)
    )

    if text_in(wrong_actor, GENERIC_WRONG_ACTORS):
        reasons.append("generic_wrong_actor")
    if text_in(market_object, GENERIC_MARKET_OBJECTS):
        reasons.append("generic_market_object")
    if invariant_statement.lower() in GENERIC_FILLERS or looks_summary_like(invariant_statement):
        reasons.append("theorem_summary_masquerading_as_edge")
    if looks_like_general_market_property(invariant_statement):
        reasons.append("general_market_property_not_game")
    if not persistence_is_actionable(why_persistence):
        reasons.append("tautological_persistence")
    executor_gap_ok, executor_gap_reason = executor_gap_is_actionable(
        executor_gap,
        why_persistence,
        death_condition,
    )
    if not executor_gap_ok and executor_gap_reason:
        reasons.append(executor_gap_reason)
    if not cheap_test_is_actionable(cheap_test):
        reasons.append("non_test_cheap_test")
    if not cheap_test_is_actionable(fast_falsifier):
        reasons.append("non_test_fast_falsifier")
    if filler_fields >= 2:
        reasons.append("filler_field_overload")
    # @context decision -- Semantic validity is the hard stop that keeps
    # schema-shaped paper summaries out of ranking. Two or more filler fields
    # means the row is too underspecified to promote, even if one field happens
    # to look concrete in isolation.
    return sorted(set(reasons))


def semantic_validity(doc):
    reasons = semantic_failure_reasons(doc)
    return {
        "semantic_valid": not reasons,
        "semantic_failure_reasons": reasons,
    }
