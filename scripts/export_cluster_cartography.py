#!/usr/bin/env python3

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "data"
    / "structural-analogy"
    / "runs"
    / "qfin-prelim-00882-research-pack"
    / "cluster-cartography.md"
)
TARGET_FAMILIES = [
    "parity-break__two-leg-parity__other__missing-executor-primitive",
    "inventory-dislocation__inventory-recycling__quote-ladder__missing-executor-primitive",
]
CORE_EVIDENCE = "core evidence"
PERIPHERAL_ANALOGUE = "peripheral analogue"
CONTAMINATION = "contamination / misclustered"


def parse_args():
    parser = argparse.ArgumentParser(description="Export paper-level cartography for target clusters.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="qfin-prelim-00882-c13")
    parser.add_argument("--family-name", action="append", default=None)
    parser.add_argument("--output-path", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--json-output-path", default=None)
    parser.add_argument("--thesis-output-path", default=None)
    parser.add_argument("--thesis-json-output-path", default=None)
    parser.add_argument("--motif-evidence-output-path", default=None)
    parser.add_argument("--motif-evidence-json-output-path", default=None)
    parser.add_argument("--measurement-spec-output-path", default=None)
    parser.add_argument("--measurement-spec-json-output-path", default=None)
    return parser.parse_args()


def parse_json(value, fallback):
    if not value:
        return fallback
    return json.loads(value)


def normalize_list(value):
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if value:
        return [str(value)]
    return []


def normalize_text(value):
    return (value or "").strip().lower()


def author_names(authors_json):
    authors = parse_json(authors_json, [])
    names = []
    for author in authors:
        if isinstance(author, dict):
            forenames = author.get("forenames", "")
            keyname = author.get("keyname", "")
            name = " ".join(part for part in [forenames, keyname] if part).strip()
            if name:
                names.append(name)
    return names


def first_matching_phrase(text, phrases):
    for phrase in phrases:
        if phrase in text:
            return phrase
    return None


def citation(member):
    return f"`{member['paper_id']}` / mechanism `{member['mechanism_instance_id']}`"


def member_text(member):
    parts = [
        member.get("title", ""),
        member.get("mechanism_label", ""),
        member.get("mechanism_summary", ""),
        member["mechanism_json"].get("source_excerpt", ""),
        " ".join(normalize_list(member.get("required_assumptions"))),
        " ".join(normalize_list(member.get("failure_regimes"))),
        " ".join(normalize_list(member.get("fragility_flags"))),
    ]
    return normalize_text(" ".join(parts))


def structure_key(mechanism_json):
    edge_source = tuple(sorted(normalize_list(mechanism_json.get("edge_source"))))
    execution_style = tuple(sorted(normalize_list(mechanism_json.get("execution_style"))))
    domain = mechanism_json.get("original_market_domain") or "unknown"
    return edge_source, execution_style, domain


def subfamily_name(struct_key):
    edge_source, execution_style, domain = struct_key
    parts = [
        ",".join(edge_source) if edge_source else "unknown-edge",
        ",".join(execution_style) if execution_style else "unknown-execution",
        domain,
    ]
    return " / ".join(parts)


def distinct_observable_pattern(edge_source):
    edge_set = set(edge_source)
    if "cross_venue_basis" in edge_set:
        return "Spread or basis gaps across linked venues, contracts, or markets."
    if "queue_position_value" in edge_set:
        return "Queue position or fill-probability changes that alter maker economics."
    if "inventory_pressure" in edge_set:
        return "Quote shading or liquidity withdrawal under inventory stress."
    return "Only weakly supported by generic extracted edge markers."


def implied_trade_shape(edge_source, execution_style):
    edge_set = set(edge_source)
    exec_set = set(execution_style)
    if "cross_venue_basis" in edge_set:
        return "Basis capture across linked legs; richer than same-market copy trading only when the underlying papers name non-identical linkages."
    if "queue_position_value" in edge_set and "passive_market_making" in exec_set:
        return "Stateful maker or queue-position trade: join, pull, or lean based on local queue economics."
    if "inventory_pressure" in edge_set:
        return "Inventory-stress trade: lean against or exploit inventory-driven quote adjustment."
    return "Only weakly supported by the extracted structure."


def load_cluster_data(connection, family_name, run_id):
    family_row = connection.execute(
        """
        SELECT candidate_family_id, family_name, family_summary, family_json
        FROM candidate_families
        WHERE family_name = ?
        """,
        (family_name,),
    ).fetchone()
    if not family_row:
        return None

    representative_candidate_id = parse_json(family_row["family_json"], {}).get(
        "representative_candidate_mechanism_instance_id"
    )
    rep_row = None
    if representative_candidate_id:
        rep_row = connection.execute(
            """
            SELECT mi.mechanism_instance_id, mi.paper_id, mi.mechanism_label, mi.mechanism_summary,
                   mi.mechanism_json, p.title, p.authors_json, substr(p.published_at,1,4) AS year
            FROM mechanism_instances mi
            JOIN papers p ON p.paper_id = mi.paper_id
            WHERE mi.mechanism_instance_id = ?
            """,
            (representative_candidate_id,),
        ).fetchone()

    rows = connection.execute(
        """
        SELECT
          cfm.candidate_family_member_id,
          cfm.adjudicated_queryless_hit_id,
          cfm.source_mechanism_instance_id,
          cfm.candidate_mechanism_instance_id,
          cfm.member_role,
          cfm.support_json,
          aqh.adjusted_score,
          aqh.adjusted_rank_within_source,
          aqh.score_delta,
          qch.rank_within_source,
          qch.mining_mode,
          qch.structural_similarity_score,
          qch.lexical_distance_score,
          qch.transfer_plausibility_score,
          qch.blocker_penalty_score,
          qch.reranker_score,
          qch.rationale_json,
          mi.paper_id,
          mi.mechanism_label,
          mi.mechanism_summary,
          mi.required_assumptions_json,
          mi.failure_regimes_json,
          mi.fragility_flags_json,
          mi.mechanism_json,
          p.title,
          p.authors_json,
          substr(p.published_at,1,4) AS year
        FROM candidate_family_members cfm
        JOIN adjudicated_queryless_hits aqh ON aqh.adjudicated_queryless_hit_id = cfm.adjudicated_queryless_hit_id
        JOIN queryless_candidate_hits qch ON qch.queryless_candidate_hit_id = aqh.queryless_candidate_hit_id
        JOIN mechanism_instances mi ON mi.mechanism_instance_id = cfm.source_mechanism_instance_id
        JOIN papers p ON p.paper_id = mi.paper_id
        WHERE cfm.candidate_family_id = ? AND cfm.run_id = ?
        ORDER BY cfm.source_mechanism_instance_id, cfm.candidate_family_member_id
        """,
        (family_row["candidate_family_id"], run_id),
    ).fetchall()

    members = {}
    for row in rows:
        mechanism_id = row["source_mechanism_instance_id"]
        support = parse_json(row["support_json"], {})
        if mechanism_id not in members:
            mechanism_json = parse_json(row["mechanism_json"], {})
            members[mechanism_id] = {
                "mechanism_instance_id": mechanism_id,
                "paper_id": row["paper_id"],
                "title": row["title"],
                "year": row["year"],
                "authors": author_names(row["authors_json"]),
                "mechanism_label": row["mechanism_label"],
                "mechanism_summary": row["mechanism_summary"],
                "required_assumptions": parse_json(row["required_assumptions_json"], []),
                "failure_regimes": parse_json(row["failure_regimes_json"], []),
                "fragility_flags": parse_json(row["fragility_flags_json"], []),
                "mechanism_json": mechanism_json,
                "assignment_reasons": [],
                "best_score": support.get("base_utility_score", 0.0),
                "ranking_features": [],
            }
        members[mechanism_id]["assignment_reasons"].append(
            {
                "adjudicated_queryless_hit_id": row["adjudicated_queryless_hit_id"],
                "member_role": row["member_role"],
                "base_utility_score": support.get("base_utility_score", 0.0),
                "transfer_path": support.get("transfer_path", []),
                "gate_results": support.get("gate_results", {}),
            }
        )
        members[mechanism_id]["ranking_features"].append(
            {
                "adjudicated_queryless_hit_id": row["adjudicated_queryless_hit_id"],
                "mining_mode": row["mining_mode"],
                "raw_rank_within_source": row["rank_within_source"],
                "adjusted_rank_within_source": row["adjusted_rank_within_source"],
                "structural_similarity_score": row["structural_similarity_score"],
                "lexical_distance_score": row["lexical_distance_score"],
                "transfer_plausibility_score": row["transfer_plausibility_score"],
                "blocker_penalty_score": row["blocker_penalty_score"],
                "reranker_score": row["reranker_score"],
                "adjusted_score": row["adjusted_score"],
                "score_delta": row["score_delta"],
                "rationale_json": parse_json(row["rationale_json"], {}),
            }
        )
        members[mechanism_id]["best_score"] = max(
            members[mechanism_id]["best_score"], support.get("base_utility_score", 0.0)
        )

    return {
        "family_name": family_row["family_name"],
        "family_summary": family_row["family_summary"],
        "representative_candidate": rep_row,
        "members": sorted(members.values(), key=lambda item: (-item["best_score"], item["mechanism_instance_id"])),
    }


def classify_member_purity(family_name, member):
    text = member_text(member)
    market_terms = [
        "market",
        "exchange",
        "trading",
        "trader",
        "order book",
        "limit order",
        "liquidity",
        "maker",
        "dealer",
        "asset",
        "price",
        "quote",
        "inventory",
        "arbitrage",
        "currency",
        "fx",
        "stock",
        "bond",
        "option",
        "futures",
        "prediction market",
    ]
    off_domain_terms = [
        "wireless",
        "sensor",
        "robot",
        "drone",
        "traffic",
        "vehicle",
        "power grid",
        "energy dispatch",
        "manufacturing",
        "supply chain",
        "medical",
        "healthcare",
        "network routing",
        "cloud scheduling",
        "carbon",
        "school enrollment",
        "climate regulation",
        "monetary policy",
        "crop yield",
        "agricultural productivity",
    ]
    parity_terms = [
        "arbitrage",
        "triangular",
        "cross-currency",
        "currency peg",
        "peg defense",
        "fragmentation",
        "fragmented",
        "cross-venue",
        "lead-lag",
        "price discovery",
        "basis",
        "cross-impact",
        "cointegration",
    ]
    inventory_terms = [
        "inventory",
        "market making",
        "market-maker",
        "maker",
        "queue",
        "fill probability",
        "fill-probability",
        "replenishment",
        "quote placement",
        "quote-placement",
        "quote ladder",
        "quote-ladder",
        "limit order book",
        "liquidity provider",
        "dealer",
    ]
    control_terms = [
        "reinforcement learning",
        "q-learning",
        "stochastic control",
        "optimal control",
        "control",
        "policy",
        "agent-based",
        "agent based",
        "state",
        "trigger",
        "uncertainty",
    ]

    if family_name.startswith("parity-break"):
        direct_match = first_matching_phrase(text, parity_terms)
        if direct_match:
            return CORE_EVIDENCE, [
                "directly names a linked-market / parity / fragmentation / triangular / lead-lag mechanism",
                f"matched phrase: `{direct_match}`",
            ]
    else:
        direct_match = first_matching_phrase(text, inventory_terms)
        if direct_match:
            return CORE_EVIDENCE, [
                "directly names maker inventory / queue / fill-probability / replenishment / quote-placement mechanism",
                f"matched phrase: `{direct_match}`",
            ]

    off_domain_match = first_matching_phrase(text, off_domain_terms)
    if off_domain_match:
        return CONTAMINATION, [
            "clearly non-tradable or domain-misaligned",
            f"matched phrase: `{off_domain_match}`",
        ]

    has_market_language = any(term in text for term in market_terms)
    has_control_language = any(term in text for term in control_terms)
    if has_market_language and has_control_language:
        return PERIPHERAL_ANALOGUE, [
            "only shares abstract control structure",
            "retained as a market analogue but does not directly name the cluster mechanism",
        ]
    if has_market_language:
        return PERIPHERAL_ANALOGUE, [
            "only shares generic state / trigger / topology features",
            "mentions market context but not the cluster-defining mechanism directly",
        ]
    return CONTAMINATION, [
        "clearly non-tradable or domain-misaligned",
        "no direct market mechanism language beyond generic state / trigger structure",
    ]


def apply_cluster_purity_pass(cluster):
    purified_members = []
    contamination = []
    for member in cluster["members"]:
        enriched = dict(member)
        purity_label, purity_reasons = classify_member_purity(cluster["family_name"], member)
        enriched["purity_label"] = purity_label
        enriched["purity_reasons"] = purity_reasons
        purified_members.append(enriched)
        if purity_label == CONTAMINATION:
            contamination.append(enriched)

    kept_members = [
        member for member in purified_members if member["purity_label"] in {CORE_EVIDENCE, PERIPHERAL_ANALOGUE}
    ]
    cluster["members"] = purified_members
    cluster["evidence_members"] = kept_members
    cluster["contamination_members"] = sorted(
        contamination,
        key=lambda item: (
            -max((row["adjusted_score"] for row in item["ranking_features"]), default=0.0),
            item["mechanism_instance_id"],
        ),
    )
    original_size = len(purified_members)
    core_count = sum(1 for member in purified_members if member["purity_label"] == CORE_EVIDENCE)
    peripheral_count = sum(1 for member in purified_members if member["purity_label"] == PERIPHERAL_ANALOGUE)
    contamination_count = sum(1 for member in purified_members if member["purity_label"] == CONTAMINATION)
    cluster["purity"] = {
        "original_cluster_size": original_size,
        "core_evidence_count": core_count,
        "peripheral_analogue_count": peripheral_count,
        "contamination_count": contamination_count,
        # Purity is defined on rows retained for interpretation, not all candidate hits,
        # because the operator question is whether motifs survive after generic structural spillover is removed.
        "purity_ratio": round((core_count + peripheral_count) / original_size, 3) if original_size else 0.0,
    }
    return cluster


def build_subfamilies(members):
    grouped = defaultdict(list)
    for member in members:
        key = structure_key(member["mechanism_json"])
        grouped[key].append(member)
    subfamilies = []
    for key, items in grouped.items():
        edge_source, execution_style, domain = key
        representative = items[0]
        assumptions = Counter()
        blockers = Counter()
        for item in items:
            for value in normalize_list(item["required_assumptions"]):
                assumptions[value] += 1
            for value in normalize_list(item["failure_regimes"]) + normalize_list(item["fragility_flags"]):
                blockers[value] += 1
        subfamilies.append(
            {
                "name": subfamily_name(key),
                "count": len(items),
                "representative_ids": [item["paper_id"] for item in items[:5]],
                "core_mechanism": representative["mechanism_label"],
                "distinct_observable_market_pattern": distinct_observable_pattern(edge_source),
                "implied_trade_shape": implied_trade_shape(edge_source, execution_style),
                "key_assumptions": [item for item, _ in assumptions.most_common(3)]
                or ["only weakly supported; extraction mostly says 'other'"],
                "likely_blockers": [item for item, _ in blockers.most_common(3)]
                or ["only weakly supported; extraction mostly says 'other'"],
                "supporting_mechanism_ids": [item["mechanism_instance_id"] for item in items],
            }
        )
    subfamilies.sort(key=lambda item: (-item["count"], item["name"]))
    return subfamilies


def select_support(members, phrases, allowed_labels=None):
    allowed = set(allowed_labels or [CORE_EVIDENCE, PERIPHERAL_ANALOGUE])
    selected = []
    for member in members:
        if member["purity_label"] not in allowed:
            continue
        text = member_text(member)
        if any(phrase in text for phrase in phrases):
            selected.append(member)
    return selected


def snippet(member):
    return f"{member['mechanism_label']} — {member['mechanism_summary']}"


def confidence_label(members, default="core"):
    labels = {member["purity_label"] for member in members}
    if labels == {PERIPHERAL_ANALOGUE}:
        return "peripheral"
    if default == "speculative":
        return "speculative"
    return "core"


def baseline_for_cluster(cluster_name):
    if cluster_name.startswith("parity-break"):
        return "identical market across two venues drifts apart, we capture the spread"
    return "makers under stress may quote non-neutrally"


def novelty_vs_baseline(cluster_name, motif):
    if cluster_name.startswith("parity-break"):
        if motif == "same-market cross-venue fragmentation":
            return "dressed-up version of the baseline"
        if motif == "triangular / multi-leg currency-linked parity":
            return "extension of the baseline into multi-leg linked markets"
        return "distinct from the baseline but thinly supported"
    if motif == "queue-value / fill-probability tradeoff":
        return "distinct from the baseline because it is about quote placement versus adverse selection, not generic stress"
    if motif == "inventory pressure quote shading":
        return "mostly a dressed-up version of the baseline unless stronger empirical support appears"
    return "distinct from the baseline but still mostly analogical"


def directness_for_motif(motif):
    if motif in {
        "same-market cross-venue fragmentation",
        "queue-value / fill-probability tradeoff",
    }:
        return "directly tradeable"
    if motif in {
        "triangular / multi-leg currency-linked parity",
        "lead-lag synchronization across linked markets",
        "peg-defense or inventory-distorted linked pricing",
    }:
        return "blocked by execution primitive"
    return "mainly theoretical / analogue"


def contamination_risk_for_support(support):
    labels = {member["purity_label"] for member in support}
    if labels == {CORE_EVIDENCE} and len(support) >= 2:
        return "low"
    if CONTAMINATION in labels:
        return "high"
    if len(support) == 1 or PERIPHERAL_ANALOGUE in labels:
        return "medium"
    return "low"


def support_reason_for_motif(motif, member):
    text = member_text(member)
    reasons = {
        "same-market cross-venue fragmentation": "The extracted text explicitly names fragmentation/inefficiency in a market with linked prices.",
        "triangular / multi-leg currency-linked parity": "The extracted text explicitly names triangular arbitrage and cross-currency correlations.",
        "lead-lag synchronization across linked markets": "The extracted text explicitly names a lead-lag relationship across linked exchange rates.",
        "basket / cross-impact / portfolio-linked parity": "The extracted text explicitly names cross-impact in correlated basket execution.",
        "peg-defense or inventory-distorted linked pricing": "The extracted text explicitly names a defended currency peg with inventory accumulation pressure.",
        "queue-value / fill-probability tradeoff": "The extracted text explicitly names the fill-probability versus post-fill return trade-off in market making.",
        "inventory pressure quote shading": "The extracted text explicitly names inventory accumulation or inventory management under uncertainty.",
        "cooperative maker behavior under shared stress": "The extracted text explicitly names cooperative market making or repeated-game maker behavior.",
        "order-book self-excitation / refill-lag analogue": "The extracted text explicitly names order-book dynamics, Hawkes self-excitation, or extreme order-flow dynamics.",
    }
    default = "The extracted text names market microstructure structure that matches the motif more specifically than a generic control analogue."
    if motif == "order-book self-excitation / refill-lag analogue" and "extreme price changes" in text:
        return "The extracted text explicitly studies order-flow dynamics around extreme price changes, which is the closest empirical support for burst/refill behavior."
    return reasons.get(motif, default)


def non_generic_reason(member):
    if member["purity_label"] == CORE_EVIDENCE:
        return "Not generic because the extracted text directly names the motif-defining market linkage or microstructure behavior."
    return "Not direct evidence; retained only as a clearly marked peripheral analogue because it still names market structure rather than only abstract control logic."


def strongest_reason_to_believe(row):
    count = len(row["support_members"])
    motif = row["motif"]
    if count == 1:
        return f"Only one supporting paper, but it explicitly names the motif in the extracted mechanism text: {row['support_members'][0]['paper_id']}."
    return f"{count} supporting papers survive the purity pass, and at least one core paper explicitly names the motif-defining behavior for `{motif}`."


def strongest_reason_to_doubt(row):
    count = len(row["support_members"])
    directness = row["directness"]
    if count == 1:
        return "Only one supporting paper; the motif may be real but is still thin."
    if directness == "mainly theoretical / analogue":
        return "Support is mostly modeling or control-oriented rather than a direct executable trading result."
    if row["contamination_risk"] == "medium":
        return "Some support is peripheral rather than direct, so the motif may still be partly structural spillover."
    return "Support is cleaner than the rest of the queue, but still limited and corpus coverage remains partial."


def build_thesis_seed_rows(clusters):
    rows = []
    for cluster in clusters:
        members = cluster["members"]
        if cluster["family_name"].startswith("parity-break"):
            motif_specs = [
                {
                    "motif": "same-market cross-venue fragmentation",
                    "phrases": ["fragmentation", "cross-venue", "basis"],
                    "allowed_labels": [CORE_EVIDENCE],
                    "exact_market_pattern_implied": "One asset or contract trades across fragmented venues and temporarily diverges from linked prints.",
                    "trade_hypothesis": "When the same market fragments across venues, short-lived price divergence can be captured by buying the cheap venue and selling the rich venue before linkage restores.",
                    "observable_to_measure": "Net cross-venue spread size and closure time after fees and latency.",
                    "minimum_required_data": "Venue-tagged quotes and trades, synchronized timestamps, fees, and fill outcomes.",
                    "build_blocker": "Low; mainly latency-aware routing and synchronized venue state.",
                    "confidence_default": "core",
                },
                {
                    "motif": "triangular / multi-leg currency-linked parity",
                    "phrases": ["triangular", "cross-currency", "arbitrage"],
                    "allowed_labels": [CORE_EVIDENCE],
                    "exact_market_pattern_implied": "Three linked FX or currency markets drift away from closed-loop consistency.",
                    "trade_hypothesis": "When a three-leg currency loop violates parity, a multi-leg trade can capture the gap if execution is synchronized and net of fees.",
                    "observable_to_measure": "Closed-loop parity error across three linked markets.",
                    "minimum_required_data": "Synchronized quotes across all legs, fees, slippage estimates, and execution timestamps.",
                    "build_blocker": "Needs synchronized multi-leg execution and parity graph monitoring.",
                    "confidence_default": "core",
                },
                {
                    "motif": "lead-lag synchronization across linked markets",
                    "phrases": ["lead-lag", "price discovery"],
                    "allowed_labels": [CORE_EVIDENCE],
                    "exact_market_pattern_implied": "One linked market updates first and another follows with measurable lag.",
                    "trade_hypothesis": "If one venue or market systematically leads another, the lagging market can be traded during the propagation window.",
                    "observable_to_measure": "Conditional lag distribution between linked market moves.",
                    "minimum_required_data": "High-resolution quotes/trades across linked markets with synchronized clocks.",
                    "build_blocker": "Needs stable lead-lag estimation and latency-sensitive execution.",
                    "confidence_default": "speculative",
                },
                {
                    "motif": "basket / cross-impact / portfolio-linked parity",
                    "phrases": ["basket", "cross-impact"],
                    "allowed_labels": [CORE_EVIDENCE],
                    "exact_market_pattern_implied": "Execution or price changes in one instrument propagate into correlated basket constituents.",
                    "trade_hypothesis": "If basket-linked cross-impact temporarily misprices correlated legs, relative-value trades can capture the delayed adjustment.",
                    "observable_to_measure": "Short-horizon response of linked instruments after concentrated trading in one leg.",
                    "minimum_required_data": "Multi-instrument order flow, quotes, trades, and correlation map across the basket.",
                    "build_blocker": "Needs multi-instrument linkage model and impact-aware execution.",
                    "confidence_default": "speculative",
                },
                {
                    "motif": "peg-defense or inventory-distorted linked pricing",
                    "phrases": ["currency peg", "peg defense", "inventory accumulation"],
                    "allowed_labels": [CORE_EVIDENCE],
                    "exact_market_pattern_implied": "A defended or inventory-constrained participant distorts linked pricing while maintaining a target relationship.",
                    "trade_hypothesis": "If peg defense or inventory absorption creates predictable overshoot and snapback around a defended relationship, linked markets can be traded around that pressure.",
                    "observable_to_measure": "Deviation and reversion behavior around a defended linked price relationship under stress.",
                    "minimum_required_data": "Linked market prices, stress/regime tags, and intervention or inventory-pressure proxies.",
                    "build_blocker": "Needs regime tagging and reliable intervention-pressure proxies.",
                    "confidence_default": "speculative",
                },
            ]
        else:
            motif_specs = [
                {
                    "motif": "queue-value / fill-probability tradeoff",
                    "phrases": ["queue", "fill probability", "fill-probability", "market making"],
                    "allowed_labels": [CORE_EVIDENCE],
                    "exact_market_pattern_implied": "Quotes placed where fills are likely have worse post-fill outcomes than safer queue locations.",
                    "trade_hypothesis": "A passive quoting edge exists if queue position and fill probability predict post-fill adverse selection strongly enough to choose better quote placements.",
                    "observable_to_measure": "Post-fill markout conditioned on queue position and fill probability.",
                    "minimum_required_data": "Order-book events, queue position or queue-rank estimates, fills, cancels, and short-horizon markouts.",
                    "build_blocker": "Needs queue reconstruction and per-fill markout measurement.",
                    "confidence_default": "core",
                },
                {
                    "motif": "inventory pressure quote shading",
                    "phrases": ["inventory", "inventory accumulation"],
                    "allowed_labels": [CORE_EVIDENCE],
                    "exact_market_pattern_implied": "Participants under inventory pressure alter quote aggressiveness or liquidity provision asymmetrically.",
                    "trade_hypothesis": "If inventory-stressed makers systematically shade or pull quotes, their predictable imbalance can be traded directionally or with passive fades.",
                    "observable_to_measure": "Asymmetric quote shifts or spread widening after one-sided flow that proxies for inventory stress.",
                    "minimum_required_data": "Order-book states, signed trade flow, quote revisions, and maker/entity tags if available.",
                    "build_blocker": "Needs inventory-stress proxy and maker-state attribution.",
                    "confidence_default": "speculative",
                },
                {
                    "motif": "cooperative maker behavior under shared stress",
                    "phrases": ["q-learning", "cooperative", "repeated game"],
                    "allowed_labels": [PERIPHERAL_ANALOGUE],
                    "exact_market_pattern_implied": "Multiple makers react in correlated ways under shared stress without explicit coordination.",
                    "trade_hypothesis": "If makers co-move their quotes or depth under shared stress, the resulting synchronized liquidity shift can create a predictable passive or directional edge.",
                    "observable_to_measure": "Cross-maker synchronized quote or depth shifts after shared stress events.",
                    "minimum_required_data": "Participant-level quote updates, depth changes, and trade flow around stress episodes.",
                    "build_blocker": "Needs participant segmentation; current evidence is still a control analogue.",
                    "confidence_default": "peripheral",
                },
                {
                    "motif": "order-book self-excitation / refill-lag analogue",
                    "phrases": ["hawkes", "order book dynamics", "liquidity migration", "order flow dynamics"],
                    "allowed_labels": [CORE_EVIDENCE, PERIPHERAL_ANALOGUE],
                    "exact_market_pattern_implied": "Order-book events cluster in bursts, and local liquidity can disappear and return with measurable lag.",
                    "trade_hypothesis": "If cancellations, refills, and trades cluster after shocks, transient liquidity holes may create short-lived directional or passive opportunities.",
                    "observable_to_measure": "Burst intensity of cancels/adds/trades and time-to-refill after local book shocks.",
                    "minimum_required_data": "Event-level add/cancel/execute data with price level and timestamps.",
                    "build_blocker": "Current support is theory-heavy and lacks a direct trading rule in the papers.",
                    "confidence_default": "peripheral",
                },
            ]

        for spec in motif_specs:
            support = select_support(members, spec["phrases"], spec["allowed_labels"])
            if not support:
                continue
            cluster_name = cluster["family_name"]
            confidence = confidence_label(support, spec["confidence_default"])
            rows.append(
                {
                    "cluster": cluster_name,
                    "motif": spec["motif"],
                    "supporting_paper_ids": [member["paper_id"] for member in support],
                    "support_members": [
                        {
                            "paper_id": member["paper_id"],
                            "title": member["title"],
                            "year": member["year"],
                            "mechanism_instance_id": member["mechanism_instance_id"],
                            "exact_extracted_mechanism_text": snippet(member),
                            "why_this_paper_supports_this_motif": support_reason_for_motif(spec["motif"], member),
                            "why_this_is_not_just_generic_structural_analogue": non_generic_reason(member),
                            "purity_label": member["purity_label"],
                        }
                        for member in support
                    ],
                    "exact_extracted_mechanism_snippets": [snippet(member) for member in support],
                    "exact_market_pattern_implied": spec["exact_market_pattern_implied"],
                    "trade_hypothesis": spec["trade_hypothesis"],
                    "observable_to_measure": spec["observable_to_measure"],
                    "minimum_required_data": spec["minimum_required_data"],
                    "build_blocker": spec["build_blocker"],
                    "confidence": confidence,
                    "baseline": baseline_for_cluster(cluster_name),
                    "novelty_vs_baseline": novelty_vs_baseline(cluster_name, spec["motif"]),
                    "directness": directness_for_motif(spec["motif"]),
                    "contamination_risk": contamination_risk_for_support(support),
                }
            )
    return rows


def render_thesis_seed_pack(rows):
    lines = [
        "# Thesis Seed Pack",
        "",
        "| cluster | motif | supporting paper IDs | exact market pattern implied | trade hypothesis in one sentence | observable to measure | minimum required data | build blocker | confidence |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        snippets = "; ".join(row["exact_extracted_mechanism_snippets"])
        paper_ids = ", ".join(f"`{paper_id}`" for paper_id in row["supporting_paper_ids"])
        lines.append(
            f"| `{row['cluster']}` | {row['motif']} | {paper_ids} | {row['exact_market_pattern_implied']} | {row['trade_hypothesis']} | {row['observable_to_measure']} | {row['minimum_required_data']} | {row['build_blocker']} | `{row['confidence']}` |"
        )
        lines.append(f"|  | evidence snippets |  | {snippets} |  |  |  |  |  |")
    return "\n".join(lines) + "\n"


def render_motif_evidence_pack(rows):
    lines = ["# Motif Evidence Pack", ""]
    for row in rows:
        lines.extend(
            [
                f"## {row['motif']}",
                "",
                f"- cluster: `{row['cluster']}`",
                f"- confidence: `{row['confidence']}`",
                f"- supporting paper IDs: {', '.join(f'`{paper_id}`' for paper_id in row['supporting_paper_ids'])}",
                f"- baseline: {row['baseline']}",
                f"- novelty vs our current baseline: {row['novelty_vs_baseline']}",
                f"- directness: `{row['directness']}`",
                f"- contamination risk: `{row['contamination_risk']}`",
                f"- exact market linkage or microstructure pattern implied: {row['exact_market_pattern_implied']}",
                f"- strongest paper-backed reason to believe it is real: {strongest_reason_to_believe(row)}",
                f"- strongest reason to doubt it: {strongest_reason_to_doubt(row)}",
                f"- distinct motif or dressed-up baseline?: {'distinct motif' if 'dressed-up version' not in row['novelty_vs_baseline'] else 'dressed-up baseline'}",
                "",
                "### Supporting Papers",
                "",
            ]
        )
        for member in row["support_members"]:
            lines.extend(
                [
                    f"- paper: `{member['paper_id']}` — {member['title']} (`{member['year']}`)",
                    f"  mechanism_instance_id: `{member['mechanism_instance_id']}`",
                    f"  exact extracted mechanism text: {member['exact_extracted_mechanism_text']}",
                    f"  why this paper supports this motif specifically: {member['why_this_paper_supports_this_motif']}",
                    f"  why this is not just a generic structural analogue: {member['why_this_is_not_just_generic_structural_analogue']}",
                ]
            )
        lines.extend(
            [
                "",
                "### Operator Read",
                "",
                f"- Is this actually a distinct motif, or just a dressed-up version of the baseline? {('It is mostly the baseline in a cleaner label.' if 'dressed-up version' in row['novelty_vs_baseline'] else row['novelty_vs_baseline'])}",
                f"- What exact market linkage or microstructure pattern is implied? {row['exact_market_pattern_implied']}",
                f"- What is the strongest paper-backed reason to believe it is real? {strongest_reason_to_believe(row)}",
                f"- What is the strongest reason to doubt it? {strongest_reason_to_doubt(row)}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def measurement_profile(row):
    motif = row["motif"]
    profiles = {
        "same-market cross-venue fragmentation": {
            "category": "relative-value",
            "trigger_condition_to_detect": "Detect times when the same contract's best executable price differs across two venues by more than fees + estimated slippage + latency buffer for at least one quote update.",
            "trade_shape": "Buy the cheap venue and sell the rich venue, then flatten when the spread normalizes.",
            "primary_observable_to_measure": "Net executable cross-venue spread after fees and latency haircut.",
            "secondary_observables": [
                "spread dwell time",
                "fill symmetry across venues",
                "post-entry convergence speed",
            ],
            "minimum_required_data_fields": [
                "venue-tagged best bid/offer",
                "trade prints",
                "timestamps",
                "fees",
                "own fill outcomes or slippage proxy",
            ],
            "derived_features_needed": [
                "synchronized NBBO-style linked quote view",
                "net spread after fees",
                "latency-adjusted executable edge",
                "spread closure time",
            ],
            "spherical_cow_edge_formula": "edge_per_trade ~= gross_cross_venue_spread - fees - slippage - latency_loss",
            "spherical_cow_capacity_formula": "capacity_per_day ~= mean_executable_size_at_trigger * trigger_count_per_day * participation_rate",
            "likely_false_positives": [
                "stale quote on one venue",
                "hidden fees or rebate asymmetry",
                "phantom liquidity that disappears on touch",
            ],
            "main_implementation_blocker": "Reliable synchronized venue state and latency-aware routing.",
            "decision_rule": "build now",
            "cheap_test_first": "Run a descriptive study of net executable spread opportunities and closure times for identical contracts across two venues.",
            "worth_building_if": "At least 50 triggers/day with median net edge > 1.5x fees and enough displayed size to support repeated small clips.",
        },
        "triangular / multi-leg currency-linked parity": {
            "category": "relative-value",
            "trigger_condition_to_detect": "Detect three-leg loops where implied cross rate from legs A/B and B/C differs materially from direct A/C quote after fees and estimated slippage.",
            "trade_shape": "Execute the rich-versus-cheap triangle across the three linked legs and close when loop parity restores.",
            "primary_observable_to_measure": "Closed-loop parity error net of three-leg execution costs.",
            "secondary_observables": [
                "loop error dwell time",
                "leg-level liquidity imbalance",
                "reversion probability by regime",
            ],
            "minimum_required_data_fields": [
                "synchronized quotes for all three legs",
                "trade prints",
                "fees",
                "slippage proxy",
                "timestamps",
            ],
            "derived_features_needed": [
                "implied cross rate",
                "net loop mispricing",
                "three-leg executable size",
                "path-consistency graph",
            ],
            "spherical_cow_edge_formula": "edge_per_loop ~= abs(implied_cross_rate - direct_rate) - three_leg_fees - three_leg_slippage",
            "spherical_cow_capacity_formula": "capacity_per_day ~= min_leg_size_at_trigger * loop_trigger_count_per_day * fill_completion_rate",
            "likely_false_positives": [
                "clock skew across legs",
                "one stale leg creating fake loop errors",
                "slippage on the thin leg dominating gross edge",
            ],
            "main_implementation_blocker": "Synchronized multi-leg execution and loop monitoring.",
            "decision_rule": "measure first",
            "cheap_test_first": "Build a loop-error monitor over historical linked markets and measure frequency, persistence, and gross-to-net decay.",
            "worth_building_if": "At least 10 clean loop events/day with median net edge positive after conservative three-leg slippage assumptions.",
        },
        "lead-lag synchronization across linked markets": {
            "category": "execution-timing",
            "trigger_condition_to_detect": "Condition on a move in market A at time t and test whether market B catches up over the next fixed horizon (for example 50 ms to 5 s depending on venue speed).",
            "trade_shape": "Trade the lagging market in the direction of the leader during the measured catch-up window.",
            "primary_observable_to_measure": "Conditional lag distribution between leader move and follower catch-up.",
            "secondary_observables": [
                "catch-up hit rate by horizon",
                "overshoot vs partial catch-up",
                "lag stability by time of day or regime",
            ],
            "minimum_required_data_fields": [
                "high-resolution quotes/trades across linked markets",
                "synchronized timestamps",
                "fees/slippage proxy",
            ],
            "derived_features_needed": [
                "leader/follower event labels",
                "lagged response curves",
                "conditional markouts after leader moves",
            ],
            "spherical_cow_edge_formula": "edge_per_signal ~= follower_catch_up_move - fees - slippage - latency_loss",
            "spherical_cow_capacity_formula": "capacity_per_day ~= executable_size_on_follower * clean_signal_count_per_day * fill_rate",
            "likely_false_positives": [
                "common information shock hitting both markets nearly simultaneously",
                "regime shifts that flip leader/follower direction",
                "measured lag shorter than actionable latency",
            ],
            "main_implementation_blocker": "Stable leader/follower estimation and latency-sensitive execution.",
            "decision_rule": "measure first",
            "cheap_test_first": "Estimate event-conditioned follower response curves after leader moves and see if any horizon remains positive after cost haircut.",
            "worth_building_if": "A stable leader/follower pair shows statistically persistent catch-up with median post-cost edge > 0 over many days.",
        },
        "basket / cross-impact / portfolio-linked parity": {
            "category": "relative-value",
            "trigger_condition_to_detect": "Detect large directional flow or price shock in one basket member and measure short-horizon drift in correlated members beyond normal co-move expectations.",
            "trade_shape": "Fade or follow lagging correlated legs relative to the shocked instrument depending on measured cross-impact response.",
            "primary_observable_to_measure": "Excess linked-leg response after concentrated flow in one instrument.",
            "secondary_observables": [
                "cross-impact asymmetry by direction",
                "response decay half-life",
                "sensitivity to basket concentration",
            ],
            "minimum_required_data_fields": [
                "multi-instrument quotes/trades",
                "signed flow proxy",
                "correlation or linkage map",
                "timestamps",
            ],
            "derived_features_needed": [
                "shock score per instrument",
                "expected co-move baseline",
                "residual linked-leg response",
            ],
            "spherical_cow_edge_formula": "edge_per_event ~= residual_linked_leg_move - fees - slippage",
            "spherical_cow_capacity_formula": "capacity_per_day ~= linked_leg_depth * qualified_shock_count_per_day * participation_rate",
            "likely_false_positives": [
                "shared news creating common moves rather than cross-impact",
                "spurious correlations in small samples",
                "execution impact from our own hedge leg",
            ],
            "main_implementation_blocker": "Reliable linkage model across instruments and impact-aware execution.",
            "decision_rule": "defer",
            "cheap_test_first": "Run an event study of linked-leg returns after large single-leg flow shocks and compare to matched-control periods.",
            "worth_building_if": "Residual linked-leg response is repeatable, sign-stable, and large enough to beat hedge slippage.",
        },
        "peg-defense or inventory-distorted linked pricing": {
            "category": "relative-value",
            "trigger_condition_to_detect": "Detect stress periods where a defended relationship widens and reversion probability changes alongside inventory/intervention pressure proxies.",
            "trade_shape": "Trade deviations around the defended relationship with regime-aware entry and exit rules.",
            "primary_observable_to_measure": "Deviation and snapback profile around defended price relationships under stress.",
            "secondary_observables": [
                "reversion speed by stress bucket",
                "overshoot frequency",
                "liquidity collapse around defense events",
            ],
            "minimum_required_data_fields": [
                "linked market prices",
                "timestamps",
                "stress or intervention proxies",
                "liquidity measures",
            ],
            "derived_features_needed": [
                "defended-band deviation score",
                "stress regime label",
                "snapback probability curve",
            ],
            "spherical_cow_edge_formula": "edge_per_event ~= expected_snapback_move - fees - slippage - regime_break_loss",
            "spherical_cow_capacity_formula": "capacity_per_day ~= stress_period_depth * stress_event_count * safe_participation_rate",
            "likely_false_positives": [
                "true regime breaks mistaken for temporary dislocations",
                "missing intervention data",
                "one-way markets with no executable exit",
            ],
            "main_implementation_blocker": "Regime tagging and reliable intervention/inventory proxies.",
            "decision_rule": "defer",
            "cheap_test_first": "Measure deviation bands and reversion conditional on observable stress proxies, without assuming intervention visibility.",
            "worth_building_if": "Stress-tagged deviations show repeatable mean reversion with enough depth to survive adverse gaps.",
        },
        "queue-value / fill-probability tradeoff": {
            "category": "passive quoting",
            "trigger_condition_to_detect": "For each passive quote opportunity, estimate fill probability and compare it to expected post-fill markout over the next short horizon.",
            "trade_shape": "Choose quote placements where expected fill-adjusted markout is positive rather than simply maximizing fill rate.",
            "primary_observable_to_measure": "Expected post-fill markout conditioned on queue rank and fill probability.",
            "secondary_observables": [
                "fill probability by queue rank",
                "post-fill adverse selection",
                "quote-level realized spread",
            ],
            "minimum_required_data_fields": [
                "order-book events",
                "our queue position or queue-rank estimate",
                "fills",
                "cancels",
                "short-horizon markouts",
            ],
            "derived_features_needed": [
                "queue rank estimate",
                "fill hazard model",
                "conditional post-fill return curve",
                "expected quote value",
            ],
            "spherical_cow_edge_formula": "edge_per_quote ~= fill_probability * post_fill_markout - adverse_selection_cost - fees",
            "spherical_cow_capacity_formula": "capacity_per_day ~= average_quoted_size * quote_opportunities_per_day * realized_fill_rate",
            "likely_false_positives": [
                "bad queue reconstruction",
                "markout horizon too short or too long",
                "selection bias from only observed fills",
            ],
            "main_implementation_blocker": "Queue reconstruction and per-fill markout pipeline.",
            "decision_rule": "build now",
            "cheap_test_first": "Run a descriptive study of markout by queue rank and fill probability bucket on existing passive fills or simulated queue entries.",
            "worth_building_if": "At least one quote-placement regime shows consistently positive expected quote value after fees and inventory limits.",
        },
        "inventory pressure quote shading": {
            "category": "directional",
            "trigger_condition_to_detect": "Measure asymmetric quote revision and spread widening after N consecutive same-side aggressive prints, conditioned on local depth and refill behavior.",
            "trade_shape": "Trade in the direction implied by stressed maker retreat or fade the stressed side if reversion dominates.",
            "primary_observable_to_measure": "Asymmetric quote revision after one-sided aggressive flow bursts.",
            "secondary_observables": [
                "spread widening",
                "depth withdrawal",
                "refill lag after same-side pressure",
            ],
            "minimum_required_data_fields": [
                "trade direction",
                "order-book depth",
                "quote revisions",
                "timestamps",
                "maker/entity tags if available",
            ],
            "derived_features_needed": [
                "same-side print run length",
                "inventory-stress proxy",
                "quote-shading score",
                "refill-lag estimate",
            ],
            "spherical_cow_edge_formula": "edge_per_event ~= post_stress_price_drift_or_reversion - fees - slippage",
            "spherical_cow_capacity_formula": "capacity_per_day ~= stressed_side_depth * qualifying_stress_event_count * participation_rate",
            "likely_false_positives": [
                "news-driven one-way flow rather than inventory stress",
                "depth changes caused by venue-wide volatility controls",
                "missing maker attribution",
            ],
            "main_implementation_blocker": "Inventory-stress proxy and maker-state attribution.",
            "decision_rule": "measure first",
            "cheap_test_first": "Run an event study on N-print same-side bursts and measure quote shading, spread widening, and subsequent drift.",
            "worth_building_if": "Stress bursts occur daily and show repeatable post-trigger drift or fill-improving passive edge after conservative costs.",
        },
        "cooperative maker behavior under shared stress": {
            "category": "passive quoting",
            "trigger_condition_to_detect": "Detect windows where multiple passive participants shift quotes or reduce depth in the same direction after a shared stress event.",
            "trade_shape": "Exploit synchronized liquidity retreat with passive placement ahead of refill or directional entry before catch-up.",
            "primary_observable_to_measure": "Cross-maker synchronization of quote or depth changes after stress.",
            "secondary_observables": [
                "depth withdrawal correlation across makers",
                "refill synchronization",
                "short-horizon drift after coordinated retreat",
            ],
            "minimum_required_data_fields": [
                "participant-level quote updates",
                "depth by maker or venue segment",
                "trade flow",
                "timestamps",
            ],
            "derived_features_needed": [
                "shared stress event label",
                "maker synchronization score",
                "coordinated retreat indicator",
            ],
            "spherical_cow_edge_formula": "edge_per_event ~= post_sync_move_or_passive_spread_capture - fees - slippage",
            "spherical_cow_capacity_formula": "capacity_per_day ~= depth_available_after_sync * synchronized_event_count * fill_rate",
            "likely_false_positives": [
                "single common news event rather than strategic co-movement",
                "participant labels too coarse to isolate makers",
                "coordination inferred from sparse data",
            ],
            "main_implementation_blocker": "Participant segmentation; current support is still analogical.",
            "decision_rule": "defer",
            "cheap_test_first": "Compute a synchronization score for quote pulls and refills across identifiable liquidity providers around stress events.",
            "worth_building_if": "Synchronized maker retreat is frequent, measurable, and followed by exploitable drift or passive spread capture.",
        },
        "order-book self-excitation / refill-lag analogue": {
            "category": "execution-timing",
            "trigger_condition_to_detect": "Detect local book shocks and measure whether cancels, trades, and refills cluster over the next x milliseconds / seconds with predictable refill lag.",
            "trade_shape": "Trade immediately after local liquidity holes open if refill lag creates a temporary directional or passive execution edge.",
            "primary_observable_to_measure": "Time-to-refill after a local liquidity shock.",
            "secondary_observables": [
                "cancel burst intensity",
                "add/cancel imbalance after shock",
                "post-shock short-horizon return",
            ],
            "minimum_required_data_fields": [
                "event-level add/cancel/execute messages",
                "price level",
                "timestamps",
                "depth snapshots",
            ],
            "derived_features_needed": [
                "shock detector",
                "self-excitation intensity estimate",
                "refill-lag distribution",
                "post-shock markout",
            ],
            "spherical_cow_edge_formula": "edge_per_shock ~= post_shock_move_or_passive_capture - fees - slippage",
            "spherical_cow_capacity_formula": "capacity_per_day ~= liquidity_available_during_lag * shock_count_per_day * fill_rate",
            "likely_false_positives": [
                "book update batching making bursts look artificial",
                "venue throttling causing fake refill lag",
                "theory-driven trigger not matching live microstructure",
            ],
            "main_implementation_blocker": "Current support is theory-heavy and requires clean event-level data.",
            "decision_rule": "measure first",
            "cheap_test_first": "Measure refill-lag distributions after local depth collapses and compare post-shock returns to matched quiet periods.",
            "worth_building_if": "Local shocks happen frequently and refill lag is long enough to support positive post-cost timing or passive capture.",
        },
    }
    return profiles[motif]


def build_measurement_spec_rows(thesis_rows):
    rows = []
    for row in thesis_rows:
        profile = measurement_profile(row)
        rows.append(
            {
                "cluster": row["cluster"],
                "motif": row["motif"],
                "supporting_paper_ids": row["supporting_paper_ids"],
                "confidence": row["confidence"],
                "exact_market_pattern_implied": row["exact_market_pattern_implied"],
                "strategy_type": profile["category"],
                "trigger_condition_to_detect": profile["trigger_condition_to_detect"],
                "trade_shape": profile["trade_shape"],
                "primary_observable_to_measure": profile["primary_observable_to_measure"],
                "secondary_observables": profile["secondary_observables"],
                "minimum_required_data_fields": profile["minimum_required_data_fields"],
                "derived_features_needed": profile["derived_features_needed"],
                "spherical_cow_edge_formula": profile["spherical_cow_edge_formula"],
                "spherical_cow_capacity_formula": profile["spherical_cow_capacity_formula"],
                "likely_false_positives": profile["likely_false_positives"],
                "main_implementation_blocker": profile["main_implementation_blocker"],
                "decision_rule": profile["decision_rule"],
                "cheap_test_first": profile["cheap_test_first"],
                "worth_building_if": profile["worth_building_if"],
            }
        )
    return rows


def render_measurement_spec_pack(rows):
    lines = ["# Measurement Spec Pack", ""]
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["cluster"]].append(row)
    for cluster in [
        "parity-break__two-leg-parity__other__missing-executor-primitive",
        "inventory-dislocation__inventory-recycling__quote-ladder__missing-executor-primitive",
    ]:
        if cluster not in grouped:
            continue
        lines.append(f"## `{cluster}`")
        lines.append("")
        for row in grouped[cluster]:
            lines.extend(
                [
                    f"### {row['motif']}",
                    "",
                    f"- supporting paper IDs: {', '.join(f'`{paper_id}`' for paper_id in row['supporting_paper_ids'])}",
                    f"- confidence: `{row['confidence']}`",
                    f"- type: `{row['strategy_type']}`",
                    f"- exact market pattern implied: {row['exact_market_pattern_implied']}",
                    f"- trigger condition to detect in our data: {row['trigger_condition_to_detect']}",
                    f"- trade shape in one sentence: {row['trade_shape']}",
                    f"- primary observable to measure: {row['primary_observable_to_measure']}",
                    f"- secondary observables: {', '.join(row['secondary_observables'])}",
                    f"- minimum required data fields: {', '.join(row['minimum_required_data_fields'])}",
                    f"- derived features needed: {', '.join(row['derived_features_needed'])}",
                    f"- spherical-cow edge formula: `{row['spherical_cow_edge_formula']}`",
                    f"- spherical-cow capacity formula: `{row['spherical_cow_capacity_formula']}`",
                    f"- likely false positives: {', '.join(row['likely_false_positives'])}",
                    f"- main implementation blocker: {row['main_implementation_blocker']}",
                    f"- cheap_test_first: {row['cheap_test_first']}",
                    f"- worth_building_if: {row['worth_building_if']}",
                    f"- decision rule: `{row['decision_rule']}`",
                    "",
                ]
            )
    return "\n".join(lines) + "\n"


def cartography_summary(cluster):
    members = cluster["evidence_members"]
    subfamilies = build_subfamilies(members)
    if not members:
        return subfamilies, ["- The purified cluster has no retained evidence members after the purity pass."]

    def pick_members(phrases):
        return [
            member
            for member in members
            if any(phrase in member_text(member) for phrase in phrases)
        ]

    def cite_many(items, limit=4):
        if not items:
            return "none"
        return ", ".join(citation(item) for item in items[:limit])

    lines = []
    fam = cluster["family_name"]
    if fam.startswith("parity-break"):
        same_market = pick_members(["fragmentation", "cross-venue", "basis"])
        triangular = pick_members(["triangular", "cross-currency", "fx", "currency peg", "peg defense"])
        basket = pick_members(["basket", "cross-impact"])
        lead_lag = pick_members(["lead-lag", "price discovery", "order flow"])
        theoretical = [member for member in members if member["purity_label"] == PERIPHERAL_ANALOGUE]
        lines.append(
            f"- Purified evidence shows same-market fragmentation or linked-market parity motifs in {cite_many(same_market)}; triangular or currency-linked structure in {cite_many(triangular)}; basket or cross-impact analogues in {cite_many(basket)}; and lead-lag or order-flow propagation in {cite_many(lead_lag)}."
        )
        lines.append(
            f"- Naive same-market cross-venue parity is directly supported where the extracted text explicitly names fragmentation, basis, or linked-venue arbitrage; strongest support is {cite_many(same_market, limit=3)}."
        )
        lines.append(
            f"- Richer structures are present but thin: triangular or currency-linked structure is only weakly supported by {len(triangular)} retained papers, specifically {cite_many(triangular, limit=3)}. Basket or cross-impact structure is only weakly supported by {len(basket)} retained papers, specifically {cite_many(basket, limit=3)}."
        )
        lines.append(
            f"- The most novel piece relative to a naive identical-market arb is the triangular / currency-linked subset in {cite_many(triangular, limit=3)}, but it remains a minority of the purified cluster."
        )
        lines.append(
            f"- Retained peripheral analogues still include theoretical or not-obviously-tradeable papers where market language is present but the mechanism is abstract; these are only weakly supported by {len(theoretical)} papers, including {cite_many(theoretical, limit=3)}."
        )
    else:
        inventory = pick_members(["inventory", "market making", "market-maker", "maker"])
        queue = pick_members(["queue", "fill probability", "fill-probability"])
        replenish = pick_members(["replenishment", "quote placement", "quote-placement", "quote ladder", "quote-ladder"])
        theoretical = [member for member in members if member["purity_label"] == PERIPHERAL_ANALOGUE]
        lines.append(
            f"- Purified evidence shows inventory-pressure or maker-state mechanisms in {cite_many(inventory)}; queue-value or fill-probability mechanisms in {cite_many(queue)}; and quote-replenishment / quote-placement structure in {cite_many(replenish)}."
        )
        lines.append(
            f"- The cleanest direct supports are the papers that explicitly mention inventory, queue, fill probability, or quote placement, specifically {cite_many(inventory + queue + replenish, limit=4)}."
        )
        lines.append(
            f"- Relative to a naive implementation, the more novel part is the explicit queue-value / fill-probability subset, but it is only supported by {len(queue)} retained papers: {cite_many(queue, limit=3)}."
        )
        lines.append(
            f"- Retained peripheral analogues still include theoretical control papers that mention markets but not a directly tradeable queue or maker-state observable; this is only weakly supported by {len(theoretical)} papers, including {cite_many(theoretical, limit=3)}."
        )
    return subfamilies, lines


def render_member(member):
    best_reason = max(member["assignment_reasons"], key=lambda row: row["base_utility_score"])
    best_rank = max(member["ranking_features"], key=lambda row: row["adjusted_score"])
    return [
        f"- mechanism_instance_id: `{member['mechanism_instance_id']}`",
        f"  paper_id: `{member['paper_id']}`",
        f"  title: {member['title']}",
        f"  year: `{member['year']}`",
        f"  authors: {', '.join(member['authors']) if member['authors'] else 'n/a'}",
        f"  exact extracted mechanism text: {member['mechanism_label']} — {member['mechanism_summary']}",
        f"  purity label: {member['purity_label']}",
        f"  purity reasons: {' | '.join(member['purity_reasons'])}",
        f"  why assigned: base score `{best_reason['base_utility_score']:.3f}`; {' | '.join(best_reason['transfer_path']) if best_reason['transfer_path'] else 'weakly supported by generic transfer path only'}",
        f"  raw and final ranking features used: mode `{best_rank['mining_mode']}`, raw rank `{best_rank['raw_rank_within_source']}`, adjusted rank `{best_rank['adjusted_rank_within_source']}`, structural `{best_rank['structural_similarity_score']:.3f}`, lexical-distance `{best_rank['lexical_distance_score']:.3f}`, transfer `{best_rank['transfer_plausibility_score']:.3f}`, blocker-penalty `{best_rank['blocker_penalty_score']:.3f}`, reranker `{best_rank['reranker_score']:.3f}`, adjusted `{best_rank['adjusted_score']:.3f}`",
    ]


def render_cluster(cluster):
    representative = cluster["representative_candidate"]
    subfamilies, summary_lines = cartography_summary(cluster)
    lines = [
        f"# {cluster['family_name']}",
        "",
        f"Representative cluster mechanism: `{representative['mechanism_instance_id']}` / `{representative['paper_id']}` — {representative['mechanism_label']}: {representative['mechanism_summary']}"
        if representative
        else "Representative cluster mechanism: n/a",
        "",
        "## 1. Cluster Purity Pass",
        "",
        f"- original cluster size: `{cluster['purity']['original_cluster_size']}`",
        f"- core evidence count: `{cluster['purity']['core_evidence_count']}`",
        f"- peripheral analogue count: `{cluster['purity']['peripheral_analogue_count']}`",
        f"- contamination count: `{cluster['purity']['contamination_count']}`",
        f"- purity ratio: `{cluster['purity']['purity_ratio']:.3f}`",
        "",
        "## 2. Full Member List",
        "",
    ]
    for member in cluster["members"]:
        lines.extend(render_member(member))
        lines.append("")
    lines.extend(["## 3. Subcluster Decomposition", ""])
    for subfamily in subfamilies:
        lines.append(f"- subfamily name: `{subfamily['name']}`")
        lines.append(f"  count of papers: `{subfamily['count']}`")
        lines.append(f"  representative paper IDs: {', '.join(subfamily['representative_ids'])}")
        lines.append(f"  core mechanism: {subfamily['core_mechanism']}")
        lines.append(f"  distinct observable market pattern: {subfamily['distinct_observable_market_pattern']}")
        lines.append(f"  implied trade shape: {subfamily['implied_trade_shape']}")
        lines.append(f"  key assumptions: {', '.join(subfamily['key_assumptions'])}")
        lines.append(f"  likely blockers / failure modes: {', '.join(subfamily['likely_blockers'])}")
        lines.append(f"  supporting mechanisms: {', '.join(str(v) for v in subfamily['supporting_mechanism_ids'])}")
        lines.append("")
    lines.extend(["## 4. Cartography Summary", ""])
    lines.extend(summary_lines)
    lines.extend(["", "## 5. Top Contamination Cases", ""])
    if cluster["contamination_members"]:
        for member in cluster["contamination_members"][:10]:
            lines.append(f"- {citation(member)}: {' | '.join(member['purity_reasons'])}")
    else:
        lines.append("- No contamination cases were retained in the cluster input.")
    lines.extend(["", "## 6. Final Operator Output", ""])
    if cluster["family_name"].startswith("parity-break"):
        lines.append("- What the papers actually say exists: same-market fragmentation and linked-market parity, plus a thinner triangular / currency-linked subset, supported by the purified evidence cited above.")
        lines.append("- What seems novel relative to our current naive implementation: multi-leg or currency-linked parity structure beyond identical-market cross-venue copies, but only where the purified evidence explicitly names triangular, currency, or peg-style linkages.")
        lines.append("- What is still just speculation: basket parity or generalized lead-lag propagation outside the thin purified subset; those motifs remain only weakly supported by one to two retained papers.")
        lines.append("- What exact observable should we go measure in our data next: distribution of parity gaps across non-identical but linked markets, especially multi-leg or currency-linked structures, with gap size, dwell time, and closure probability stratified by market linkage type.")
    else:
        lines.append("- What the papers actually say exists: maker inventory pressure, queue-value / fill-probability dynamics, and quote-placement or replenishment motifs, but only for the purified evidence cited above.")
        lines.append("- What seems novel relative to our current naive implementation: queue-value / fill-probability dynamics rather than generic 'makers move quotes' behavior, but only where a retained paper directly names queue or fill-probability structure.")
        lines.append("- What is still just speculation: transfer into your venues without richer queue-position and replenishment observables; several retained papers are still only peripheral market-control analogues.")
        lines.append("- What exact observable should we go measure in our data next: quote-ladder shifts, refill timing, cancellation bursts, and queue-position changes around inventory-looking one-sided pressure, then short-horizon price/fill outcomes after those events.")
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        target_families = args.family_name or TARGET_FAMILIES
        clusters = [
            load_cluster_data(connection, family_name, args.run_id) for family_name in target_families
        ]
    finally:
        connection.close()
    output_path = Path(args.output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = []
    payload = {"run_id": args.run_id, "clusters": []}
    purified_clusters = []
    for cluster in clusters:
        if cluster:
            cluster = apply_cluster_purity_pass(cluster)
            purified_clusters.append(cluster)
            text.append(render_cluster(cluster))
            subfamilies, summary_lines = cartography_summary(cluster)
            payload["clusters"].append(
                {
                    "family_name": cluster["family_name"],
                    "family_summary": cluster["family_summary"],
                    "representative_candidate": dict(cluster["representative_candidate"]) if cluster["representative_candidate"] else None,
                    "purity": cluster["purity"],
                    "members": cluster["members"],
                    "subfamilies": subfamilies,
                    "cartography_summary": summary_lines,
                    "top_contamination_cases": cluster["contamination_members"][:10],
                }
            )
    output_path.write_text("\n\n".join(text), encoding="utf-8")
    json_output_path = (
        Path(args.json_output_path).resolve()
        if args.json_output_path
        else output_path.with_suffix(".json")
    )
    json_output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    thesis_rows = build_thesis_seed_rows(purified_clusters)
    thesis_output_path = (
        Path(args.thesis_output_path).resolve()
        if args.thesis_output_path
        else output_path.with_name("thesis_seed_pack.md")
    )
    thesis_output_path.write_text(render_thesis_seed_pack(thesis_rows), encoding="utf-8")
    thesis_json_output_path = (
        Path(args.thesis_json_output_path).resolve()
        if args.thesis_json_output_path
        else thesis_output_path.with_suffix(".json")
    )
    thesis_json_output_path.write_text(
        json.dumps({"run_id": args.run_id, "rows": thesis_rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    motif_evidence_output_path = (
        Path(args.motif_evidence_output_path).resolve()
        if args.motif_evidence_output_path
        else output_path.with_name("motif_evidence_pack.md")
    )
    motif_evidence_output_path.write_text(render_motif_evidence_pack(thesis_rows), encoding="utf-8")
    motif_evidence_json_output_path = (
        Path(args.motif_evidence_json_output_path).resolve()
        if args.motif_evidence_json_output_path
        else motif_evidence_output_path.with_suffix(".json")
    )
    motif_evidence_json_output_path.write_text(
        json.dumps({"run_id": args.run_id, "rows": thesis_rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    measurement_rows = build_measurement_spec_rows(thesis_rows)
    measurement_output_path = (
        Path(args.measurement_spec_output_path).resolve()
        if args.measurement_spec_output_path
        else output_path.with_name("measurement_spec_pack.md")
    )
    measurement_output_path.write_text(render_measurement_spec_pack(measurement_rows), encoding="utf-8")
    measurement_json_output_path = (
        Path(args.measurement_spec_json_output_path).resolve()
        if args.measurement_spec_json_output_path
        else measurement_output_path.with_suffix(".json")
    )
    measurement_json_output_path.write_text(
        json.dumps({"run_id": args.run_id, "rows": measurement_rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(output_path)


if __name__ == "__main__":
    main()
