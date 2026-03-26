#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from validate_schema_examples import load_json, validate


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "fingerprint.schema.json"
DEFAULT_FINGERPRINT_VERSION = "mechanism-fingerprint-v1"
SERIALIZER_VERSION = "c08-rule-based-v1"
DEFAULT_RUN_KIND = "normalization_fingerprint"
DEFAULT_MODEL_NAME = "rule-based-normalizer"

TRIGGER_MAP = {
    "logical_inconsistency": ["parity_break"],
    "stale_quotes": ["stale_update_window"],
    "inventory_pressure": ["inventory_dislocation"],
    "reward_incentives": ["subsidy_window"],
    "flow_imbalance": ["order_flow_shock"],
    "settlement_friction": ["settlement_reset"],
    "delayed_information_diffusion": ["information_diffusion_lag"],
    "term_structure_dislocation": ["term_structure_kink"],
    "auction_design": ["allocation_rule_edge"],
    "queue_position_value": ["queue_priority_shift"],
    "cross_venue_basis": ["parity_break"],
    "other": ["other"],
}

STATE_VARIABLE_MAP = {
    "logical_inconsistency": ["relative_price_spread", "implied_probability"],
    "stale_quotes": ["venue_latency_state", "relative_price_spread"],
    "inventory_pressure": ["inventory_position"],
    "reward_incentives": ["reward_schedule"],
    "flow_imbalance": ["order_flow_imbalance"],
    "settlement_friction": ["resolution_state"],
    "delayed_information_diffusion": ["venue_latency_state"],
    "term_structure_dislocation": ["term_curve_state"],
    "queue_position_value": ["queue_rank"],
    "cross_venue_basis": ["relative_price_spread"],
}

INSTRUMENT_STATE_VARIABLE_MAP = {
    "binary_contract": ["implied_probability", "resolution_state"],
    "multi_outcome_contract": ["implied_probability", "resolution_state"],
    "limit_order_book_claim": ["queue_rank", "order_flow_imbalance"],
    "option": ["hedge_ratio", "term_curve_state"],
    "future": ["relative_price_spread", "hedge_ratio"],
    "spread": ["relative_price_spread"],
    "basket": ["relative_price_spread", "implied_probability"],
    "auction_allocation": ["relative_price_spread"],
    "amm_lp_position": ["inventory_position", "reward_schedule"],
}

EXECUTION_SHAPE_MAP = {
    "maker_anchor": ["maker_anchor"],
    "parallel_fok": ["parallel_fok"],
    "sequential_fok": ["sequential_fok"],
    "passive_market_making": ["quote_ladder"],
    "inventory_rebalancing": ["inventory_rebalance"],
    "latency_arb": ["latency_arb"],
    "auction_sniping": ["auction_take"],
    "batch_basket_completion": ["parallel_fok", "recovery_gtc"],
    "other": ["other"],
}

PRICING_PATH_MAP = {
    "logical_inconsistency": ["parity_reversion"],
    "cross_venue_basis": ["parity_reversion"],
    "stale_quotes": ["quote_refresh_capture"],
    "inventory_pressure": ["inventory_mean_reversion"],
    "reward_incentives": ["reward_harvest"],
    "term_structure_dislocation": ["curve_relinking"],
    "queue_position_value": ["queue_capture"],
    "auction_design": ["auction_price_discovery"],
    "delayed_information_diffusion": ["information_catchup"],
    "other": ["other"],
}

LIQUIDITY_CONDITION_MAP = {
    "thin_book": ["thin_book"],
    "fragmented_venues": ["fragmented_venues"],
    "discrete_ticks": ["discrete_ticks"],
    "asynchronous_updates": ["asynchronous_updates"],
    "reward_program": ["reward_subsidized"],
    "forced_flow": ["forced_flow"],
    "hedgeable_exposure": ["hedgeable_exposure"],
    "observable_order_book": ["observable_order_book"],
    "low_latency_access": ["low_latency_race"],
    "other": ["other"],
}

FRAGILITY_LIQUIDITY_MAP = {
    "depends_on_thin_liquidity": ["thin_book"],
    "depends_on_fast_execution": ["low_latency_race"],
    "depends_on_exogenous_subsidy": ["reward_subsidized"],
    "sensitive_to_data_latency": ["asynchronous_updates"],
    "sensitive_to_inventory_constraints": ["hedgeable_exposure"],
}

CAPACITY_LIMIT_MAP = {
    "thin_resting_liquidity": ["thin_resting_liquidity"],
    "limited_hedge_capacity": ["limited_hedge_capacity"],
    "venue_rate_limits": ["venue_rate_limits"],
    "inventory_budget_limits": ["inventory_budget_limits"],
    "capital_intensity": ["capital_intensity"],
    "crowding_sensitive_edge": ["crowding_sensitive_edge"],
    "manual_market_specific_ops": ["manual_market_specific_ops"],
    "compliance_or_rule_overhead": ["compliance_or_rule_overhead"],
    "limited_event_frequency": ["limited_event_frequency"],
    "other": ["other"],
}

BOUNDARY_CONDITION_MAP = {
    "linked_market_structure_is_stable": ["linked_structure_stable"],
    "hedge_leg_is_tradeable": ["hedge_leg_tradeable"],
    "mispricing_window_exceeds_latency_budget": ["hedge_leg_tradeable"],
    "fees_remain_below_edge": ["fees_bounded"],
    "resolution_rules_remain_stationary": ["resolution_rules_stable"],
    "order_book_state_is_observable": ["order_book_observable"],
    "inventory_can_be_rebalanced": ["inventory_rebalance_available"],
    "reward_schedule_persists_long_enough": ["reward_schedule_persistent"],
    "capital_can_be_recycled_fast_enough": ["capital_recycling_fast_enough"],
    "resolution_rules_shift": ["rule_change_tolerant"],
    "reward_program_ends": ["reward_schedule_persistent"],
    "linked_markets_decouple": ["linked_structure_stable"],
    "capital_recycling_slows": ["capital_recycling_fast_enough"],
    "liquidity_crunch": ["inventory_rebalance_available"],
    "rule_change_window": ["rule_change_tolerant"],
    "other": ["other"],
}

PORTABILITY_BLOCKER_MAP = {
    "depends_on_market_structure_not_present_in_target": ["missing_market_structure"],
    "depends_on_latency_edge_unavailable_in_target": ["missing_latency_edge"],
    "depends_on_inventory_tools_missing_in_target": ["missing_inventory_tools"],
    "depends_on_regulatory_or_rule_surface_not_present": ["missing_rule_surface"],
    "depends_on_reward_subsidies_not_present": ["missing_reward_subsidy"],
    "depends_on_dense_liquidity_not_present": ["missing_dense_liquidity"],
    "depends_on_observability_not_present": ["missing_observability"],
    "fails_under_sparse_event_frequency": ["sparse_event_frequency"],
    "target_market_already_prices_this_logic": ["already_priced_in_target"],
    "other": ["other"],
}

MARKET_TOPOLOGY_KEYWORDS = [
    ("term structure", ["term_structure"]),
    ("curve", ["term_structure"]),
    ("basket", ["n_leg_basket"]),
    ("multi-leg", ["n_leg_basket"]),
    ("cross-venue", ["fragmented_cross_venue"]),
    ("linked market", ["fragmented_cross_venue"]),
    ("queue", ["queue_value_mm"]),
    ("auction", ["auction_allocation"]),
    ("inventory", ["inventory_recycling"]),
    ("implied probability", ["implication_graph"]),
    ("parity", ["two_leg_parity"]),
]

ACTOR_KEYWORDS = [
    ("market maker", ["market_makers"]),
    ("maker", ["market_makers"]),
    ("retail", ["retail_flow"]),
    ("hedger", ["forced_hedgers"]),
    ("forced flow", ["forced_hedgers"]),
    ("auction", ["auction_bidders"]),
    ("latency", ["latency_sensitive_arbitrageurs"]),
    ("arb", ["cross_venue_arbitrageurs"]),
    ("arbitrage", ["cross_venue_arbitrageurs"]),
    ("rule-constrained", ["rule_constrained_arbitrageurs"]),
    ("amm", ["amm_rebalancers"]),
    ("index", ["passive_index_flow"]),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Normalize active mechanism instances into structural fingerprints."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-path",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to the fingerprint schema.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit normalization run id.",
    )
    parser.add_argument(
        "--fingerprint-version",
        default=DEFAULT_FINGERPRINT_VERSION,
        help="Fingerprint contract version to write.",
    )
    parser.add_argument(
        "--paper-id",
        action="append",
        default=[],
        help="Restrict normalization to one or more paper ids.",
    )
    parser.add_argument(
        "--mechanism-instance-id",
        action="append",
        type=int,
        default=[],
        help="Restrict normalization to one or more mechanism instance ids.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of active mechanisms to normalize.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def dedupe(items: Iterable[str]):
    seen = set()
    ordered = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def parse_json_array(value):
    if not value:
        return []
    decoded = json.loads(value)
    return decoded if isinstance(decoded, list) else []


def parse_json_object(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {}


def append_mapped(target, source_values, mapping):
    for value in source_values:
        target.extend(mapping.get(value, []))


def append_keyword_hits(target, text, mapping):
    lowered = text.lower()
    for needle, values in mapping:
        if needle in lowered:
            target.extend(values)


def non_empty_or_other(values):
    normalized = [value for value in dedupe(values) if value]
    return normalized if normalized else ["other"]


def build_market_topology(mechanism_summary: str, evidence_text: str, edge_source, instrument_type):
    topology = []
    combined = f"{mechanism_summary}\n{evidence_text}"
    append_keyword_hits(topology, combined, MARKET_TOPOLOGY_KEYWORDS)
    if "cross_venue_basis" in edge_source:
        topology.extend(["two_leg_parity", "fragmented_cross_venue"])
    if "term_structure_dislocation" in edge_source:
        topology.append("term_structure")
    if "queue_position_value" in edge_source:
        topology.append("queue_value_mm")
    if "auction_design" in edge_source:
        topology.append("auction_allocation")
    if "inventory_pressure" in edge_source:
        topology.append("inventory_recycling")
    if "basket" in instrument_type:
        topology.append("n_leg_basket")
    if "multi_outcome_contract" in instrument_type:
        topology.append("implication_graph")
    return non_empty_or_other(topology)


def build_actor_structure(
    evidence_text: str,
    mechanism_summary: str,
    original_market_domain: str,
    required_conditions,
):
    actors = []
    append_keyword_hits(actors, f"{mechanism_summary}\n{evidence_text}", ACTOR_KEYWORDS)
    if "fragmented_venues" in required_conditions:
        actors.append("cross_venue_arbitrageurs")
    if "forced_flow" in required_conditions:
        actors.append("forced_hedgers")
    if "reward_program" in required_conditions:
        actors.append("market_makers")
    if original_market_domain == "decentralized_finance":
        actors.append("amm_rebalancers")
    if original_market_domain == "auction_design":
        actors.append("auction_bidders")
    if original_market_domain in {"market_microstructure", "options"}:
        actors.append("market_makers")
    return non_empty_or_other(actors)


def classify_ambiguity_flags(fingerprint, evidence_confidence: str, section_labels):
    flags = []
    # @context decision -- C08 writes a queued normalization review whenever the
    # structural object is weak or lossy rather than pretending the mapper was
    # decisive. Retrieval gets a stable fingerprint surface, and operators get a
    # visible review queue for the unresolved cases.
    mapped_fields = [
        "trigger",
        "state_variables",
        "actor_structure",
        "market_topology",
        "pricing_path",
        "execution_shape",
        "liquidity_regime",
        "capacity_limit",
        "boundary_conditions",
        "portability_blockers",
    ]
    if any("other" in fingerprint[field] for field in mapped_fields):
        flags.append("contains_other_mapping")
    if len(fingerprint["market_topology"]) > 1:
        flags.append("multiple_topology_candidates")
    if evidence_confidence == "weak":
        flags.append("weak_evidence_support")
    if not section_labels:
        flags.append("no_section_backing")
    if fingerprint["state_variables"] == ["other"]:
        flags.append("sparse_state_variables")
    if fingerprint["actor_structure"] == ["other"]:
        flags.append("sparse_actor_structure")
    if fingerprint["boundary_conditions"] == ["other"]:
        flags.append("sparse_boundary_conditions")
    return dedupe(flags)


def serialize_fingerprint(fingerprint):
    fields = [
        "trigger",
        "state_variables",
        "actor_structure",
        "market_topology",
        "pricing_path",
        "execution_shape",
        "liquidity_regime",
        "capacity_limit",
        "boundary_conditions",
        "portability_blockers",
    ]
    return " | ".join(f"{field}={','.join(fingerprint[field])}" for field in fields)


def build_fingerprint(mechanism_row, evidence_bundle, fingerprint_version: str):
    mechanism_json = parse_json_object(mechanism_row["mechanism_json"])
    edge_source = mechanism_json.get("edge_source") or []
    instrument_type = mechanism_json.get("instrument_type") or []
    execution_style = mechanism_json.get("execution_style") or []
    required_conditions = mechanism_json.get("required_market_conditions") or []
    negative_transfer = mechanism_json.get("negative_transfer_rationale") or []
    fragility_flags = parse_json_array(mechanism_row["fragility_flags_json"])
    capacity_constraints = parse_json_array(mechanism_row["capacity_constraints_json"])
    required_assumptions = parse_json_array(mechanism_row["required_assumptions_json"])
    assumption_violations = parse_json_array(mechanism_row["assumption_violations_json"])
    failure_regimes = parse_json_array(mechanism_row["failure_regimes_json"])
    evidence_text = evidence_bundle["evidence_text"]
    mechanism_summary = mechanism_row["mechanism_summary"] or ""

    trigger = []
    append_mapped(trigger, edge_source, TRIGGER_MAP)

    state_variables = []
    append_mapped(state_variables, edge_source, STATE_VARIABLE_MAP)
    append_mapped(state_variables, instrument_type, INSTRUMENT_STATE_VARIABLE_MAP)
    append_keyword_hits(
        state_variables,
        f"{mechanism_summary}\n{evidence_text}",
        [
            ("inventory", ["inventory_position"]),
            ("queue", ["queue_rank"]),
            ("order flow", ["order_flow_imbalance"]),
            ("reward", ["reward_schedule"]),
            ("term structure", ["term_curve_state"]),
            ("resolution", ["resolution_state"]),
            ("hedge", ["hedge_ratio"]),
        ],
    )

    pricing_path = []
    append_mapped(pricing_path, edge_source, PRICING_PATH_MAP)
    if "parallel_fok" in execution_style or "batch_basket_completion" in execution_style:
        pricing_path.append("parity_reversion")
    if "inventory_rebalancing" in execution_style:
        pricing_path.append("inventory_mean_reversion")

    execution_shape = []
    append_mapped(execution_shape, execution_style, EXECUTION_SHAPE_MAP)

    liquidity_regime = []
    append_mapped(liquidity_regime, required_conditions, LIQUIDITY_CONDITION_MAP)
    append_mapped(liquidity_regime, fragility_flags, FRAGILITY_LIQUIDITY_MAP)
    if any(label == "Results" for label in evidence_bundle["section_labels"]):
        liquidity_regime.append("observable_order_book")

    capacity_limit = []
    append_mapped(capacity_limit, capacity_constraints, CAPACITY_LIMIT_MAP)

    boundary_conditions = []
    append_mapped(boundary_conditions, required_assumptions, BOUNDARY_CONDITION_MAP)
    append_mapped(boundary_conditions, assumption_violations, BOUNDARY_CONDITION_MAP)
    append_mapped(boundary_conditions, failure_regimes, BOUNDARY_CONDITION_MAP)

    portability_blockers = []
    append_mapped(portability_blockers, negative_transfer, PORTABILITY_BLOCKER_MAP)

    fingerprint = {
        "fingerprint_version": fingerprint_version,
        "trigger": non_empty_or_other(trigger),
        "state_variables": non_empty_or_other(state_variables),
        "actor_structure": build_actor_structure(
            evidence_text=evidence_text,
            mechanism_summary=mechanism_summary,
            original_market_domain=mechanism_json.get("original_market_domain", "other"),
            required_conditions=required_conditions,
        ),
        "market_topology": build_market_topology(
            mechanism_summary=mechanism_summary,
            evidence_text=evidence_text,
            edge_source=edge_source,
            instrument_type=instrument_type,
        ),
        "pricing_path": non_empty_or_other(pricing_path),
        "execution_shape": non_empty_or_other(execution_shape),
        "liquidity_regime": non_empty_or_other(liquidity_regime),
        "capacity_limit": non_empty_or_other(capacity_limit),
        "boundary_conditions": non_empty_or_other(boundary_conditions),
        "portability_blockers": non_empty_or_other(portability_blockers),
        "ambiguity_flags": [],
    }
    fingerprint["ambiguity_flags"] = classify_ambiguity_flags(
        fingerprint=fingerprint,
        evidence_confidence=mechanism_row["evidence_confidence"],
        section_labels=evidence_bundle["section_labels"],
    )
    fingerprint["fingerprint_text"] = serialize_fingerprint(fingerprint)
    return fingerprint


def ensure_c08_store_contract(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mechanism_fingerprints (
          mechanism_fingerprint_id INTEGER PRIMARY KEY AUTOINCREMENT,
          mechanism_instance_id INTEGER NOT NULL,
          paper_id TEXT NOT NULL,
          run_id TEXT NOT NULL,
          fingerprint_version TEXT NOT NULL,
          trigger_json TEXT NOT NULL,
          state_variables_json TEXT NOT NULL,
          actor_structure_json TEXT NOT NULL,
          market_topology_json TEXT NOT NULL,
          pricing_path_json TEXT NOT NULL,
          execution_shape_json TEXT NOT NULL,
          liquidity_regime_json TEXT NOT NULL,
          capacity_limit_json TEXT NOT NULL,
          boundary_conditions_json TEXT NOT NULL,
          portability_blockers_json TEXT NOT NULL,
          ambiguity_flags_json TEXT NOT NULL DEFAULT '[]',
          serializer_version TEXT NOT NULL,
          fingerprint_text TEXT NOT NULL,
          fingerprint_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (mechanism_instance_id, run_id, fingerprint_version)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS normalization_reviews (
          normalization_review_id INTEGER PRIMARY KEY AUTOINCREMENT,
          mechanism_instance_id INTEGER NOT NULL,
          paper_id TEXT NOT NULL,
          run_id TEXT NOT NULL,
          fingerprint_version TEXT NOT NULL,
          review_status TEXT NOT NULL DEFAULT 'queued',
          ambiguity_flags_json TEXT NOT NULL DEFAULT '[]',
          candidate_mappings_json TEXT NOT NULL DEFAULT '{}',
          review_notes TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (mechanism_instance_id, run_id, fingerprint_version)
        )
        """
    )


def ensure_run(connection, run_id: str | None, fingerprint_version: str):
    resolved_run_id = run_id or f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    config = {
        "fingerprint_version": fingerprint_version,
        "serializer_version": SERIALIZER_VERSION,
        "run_kind": DEFAULT_RUN_KIND,
    }
    existing = connection.execute(
        """
        SELECT run_id
        FROM extraction_runs
        WHERE run_id = ?
        """,
        (resolved_run_id,),
    ).fetchone()
    if existing is None:
        connection.execute(
            """
            INSERT INTO extraction_runs (
              run_id,
              run_kind,
              model_name,
              prompt_version,
              config_json,
              started_at,
              run_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_run_id,
                DEFAULT_RUN_KIND,
                DEFAULT_MODEL_NAME,
                fingerprint_version,
                json.dumps(config, sort_keys=True),
                now_utc(),
                "running",
            ),
        )
    else:
        connection.execute(
            """
            UPDATE extraction_runs
            SET run_kind = ?,
                model_name = ?,
                prompt_version = ?,
                config_json = ?,
                run_status = ?
            WHERE run_id = ?
            """,
            (
                DEFAULT_RUN_KIND,
                DEFAULT_MODEL_NAME,
                fingerprint_version,
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def build_filters(args):
    clauses = ["mi.lifecycle_status = 'active'"]
    params = []
    if args.paper_id:
        placeholders = ", ".join("?" for _ in args.paper_id)
        clauses.append(f"mi.paper_id IN ({placeholders})")
        params.extend(args.paper_id)
    if args.mechanism_instance_id:
        placeholders = ", ".join("?" for _ in args.mechanism_instance_id)
        clauses.append(f"mi.mechanism_instance_id IN ({placeholders})")
        params.extend(args.mechanism_instance_id)
    limit_clause = f" LIMIT {args.limit}" if args.limit is not None else ""
    return " AND ".join(clauses), params, limit_clause


def load_mechanisms(connection, args):
    where_clause, params, limit_clause = build_filters(args)
    connection.row_factory = sqlite3.Row
    query = f"""
        SELECT
          mi.mechanism_instance_id,
          mi.paper_id,
          mi.run_id,
          mi.mechanism_label,
          mi.mechanism_summary,
          mi.insight_type,
          mi.evidence_confidence,
          mi.required_assumptions_json,
          mi.assumption_violations_json,
          mi.fragility_flags_json,
          mi.capacity_constraints_json,
          mi.failure_regimes_json,
          mi.mechanism_json
        FROM mechanism_instances mi
        WHERE {where_clause}
        ORDER BY mi.mechanism_instance_id
        {limit_clause}
    """
    return connection.execute(query, params).fetchall()


def load_evidence_bundle(connection, mechanism_instance_id: int):
    rows = connection.execute(
        """
        SELECT
          mes.evidence_text,
          COALESCE(ps.section_label, '') AS section_label
        FROM mechanism_evidence_spans mes
        LEFT JOIN paper_sections ps
          ON ps.section_id = mes.section_id
        WHERE mes.mechanism_instance_id = ?
        ORDER BY
          CASE WHEN mes.section_id IS NULL THEN 1 ELSE 0 END,
          ps.section_order,
          mes.evidence_span_id
        """,
        (mechanism_instance_id,),
    ).fetchall()
    evidence_text = "\n".join(row["evidence_text"] for row in rows if row["evidence_text"])
    return {
        "evidence_text": evidence_text,
        "section_labels": dedupe(row["section_label"] for row in rows if row["section_label"]),
    }


def persist_fingerprint(connection, mechanism_row, run_id: str, fingerprint_version: str, fingerprint):
    connection.execute(
        """
        INSERT INTO mechanism_fingerprints (
          mechanism_instance_id,
          paper_id,
          run_id,
          fingerprint_version,
          trigger_json,
          state_variables_json,
          actor_structure_json,
          market_topology_json,
          pricing_path_json,
          execution_shape_json,
          liquidity_regime_json,
          capacity_limit_json,
          boundary_conditions_json,
          portability_blockers_json,
          ambiguity_flags_json,
          serializer_version,
          fingerprint_text,
          fingerprint_json,
          updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(mechanism_instance_id, run_id, fingerprint_version) DO UPDATE SET
          trigger_json = excluded.trigger_json,
          state_variables_json = excluded.state_variables_json,
          actor_structure_json = excluded.actor_structure_json,
          market_topology_json = excluded.market_topology_json,
          pricing_path_json = excluded.pricing_path_json,
          execution_shape_json = excluded.execution_shape_json,
          liquidity_regime_json = excluded.liquidity_regime_json,
          capacity_limit_json = excluded.capacity_limit_json,
          boundary_conditions_json = excluded.boundary_conditions_json,
          portability_blockers_json = excluded.portability_blockers_json,
          ambiguity_flags_json = excluded.ambiguity_flags_json,
          serializer_version = excluded.serializer_version,
          fingerprint_text = excluded.fingerprint_text,
          fingerprint_json = excluded.fingerprint_json,
          updated_at = excluded.updated_at
        """,
        (
            mechanism_row["mechanism_instance_id"],
            mechanism_row["paper_id"],
            run_id,
            fingerprint_version,
            json.dumps(fingerprint["trigger"], sort_keys=True),
            json.dumps(fingerprint["state_variables"], sort_keys=True),
            json.dumps(fingerprint["actor_structure"], sort_keys=True),
            json.dumps(fingerprint["market_topology"], sort_keys=True),
            json.dumps(fingerprint["pricing_path"], sort_keys=True),
            json.dumps(fingerprint["execution_shape"], sort_keys=True),
            json.dumps(fingerprint["liquidity_regime"], sort_keys=True),
            json.dumps(fingerprint["capacity_limit"], sort_keys=True),
            json.dumps(fingerprint["boundary_conditions"], sort_keys=True),
            json.dumps(fingerprint["portability_blockers"], sort_keys=True),
            json.dumps(fingerprint["ambiguity_flags"], sort_keys=True),
            SERIALIZER_VERSION,
            fingerprint["fingerprint_text"],
            json.dumps(fingerprint, sort_keys=True),
            now_utc(),
        ),
    )


def persist_review(connection, mechanism_row, run_id: str, fingerprint_version: str, fingerprint):
    if fingerprint["ambiguity_flags"]:
        connection.execute(
            """
            INSERT INTO normalization_reviews (
              mechanism_instance_id,
              paper_id,
              run_id,
              fingerprint_version,
              review_status,
              ambiguity_flags_json,
              candidate_mappings_json,
              review_notes,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mechanism_instance_id, run_id, fingerprint_version) DO UPDATE SET
              review_status = excluded.review_status,
              ambiguity_flags_json = excluded.ambiguity_flags_json,
              candidate_mappings_json = excluded.candidate_mappings_json,
              review_notes = excluded.review_notes,
              updated_at = excluded.updated_at
            """,
            (
                mechanism_row["mechanism_instance_id"],
                mechanism_row["paper_id"],
                run_id,
                fingerprint_version,
                "queued",
                json.dumps(fingerprint["ambiguity_flags"], sort_keys=True),
                json.dumps(
                    {
                        "mechanism_label": mechanism_row["mechanism_label"],
                        "fingerprint": {
                            key: value
                            for key, value in fingerprint.items()
                            if key != "fingerprint_text"
                        },
                    },
                    sort_keys=True,
                ),
                "Queued automatically by normalize_mechanism_fingerprints.py",
                now_utc(),
            ),
        )
        return True

    connection.execute(
        """
        DELETE FROM normalization_reviews
        WHERE mechanism_instance_id = ?
          AND run_id = ?
          AND fingerprint_version = ?
        """,
        (
            mechanism_row["mechanism_instance_id"],
            run_id,
            fingerprint_version,
        ),
    )
    return False


def normalize(connection, schema, run_id: str, fingerprint_version: str, args):
    ensure_c08_store_contract(connection)
    mechanisms = load_mechanisms(connection, args)
    normalized_count = 0
    ambiguity_review_count = 0
    connection.execute("BEGIN")
    try:
        for mechanism_row in mechanisms:
            evidence_bundle = load_evidence_bundle(
                connection, mechanism_row["mechanism_instance_id"]
            )
            fingerprint = build_fingerprint(
                mechanism_row=mechanism_row,
                evidence_bundle=evidence_bundle,
                fingerprint_version=fingerprint_version,
            )
            validate(schema, fingerprint)
            persist_fingerprint(
                connection=connection,
                mechanism_row=mechanism_row,
                run_id=run_id,
                fingerprint_version=fingerprint_version,
                fingerprint=fingerprint,
            )
            if persist_review(
                connection=connection,
                mechanism_row=mechanism_row,
                run_id=run_id,
                fingerprint_version=fingerprint_version,
                fingerprint=fingerprint,
            ):
                ambiguity_review_count += 1
            normalized_count += 1

        connection.execute(
            """
            UPDATE extraction_runs
            SET run_status = ?, completed_at = ?
            WHERE run_id = ?
            """,
            ("completed", now_utc(), run_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "run_id": run_id,
        "fingerprint_version": fingerprint_version,
        "normalized_count": normalized_count,
        "ambiguity_review_count": ambiguity_review_count,
    }


def write_summary(run_id: str, summary):
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "fingerprint_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary_path


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    schema = load_json(Path(args.schema_path).resolve())

    connection = sqlite3.connect(str(db_path))
    try:
        run_id = ensure_run(connection, args.run_id, args.fingerprint_version)
        connection.commit()
        summary = normalize(
            connection=connection,
            schema=schema,
            run_id=run_id,
            fingerprint_version=args.fingerprint_version,
            args=args,
        )
    finally:
        connection.close()

    summary_path = write_summary(run_id, summary)
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
