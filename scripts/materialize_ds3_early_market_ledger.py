#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_REPORTS_DIR = ROOT / "reports"

BRIDGE_RUN_ID = "bridge-materialization-20260328-broadened"
COMPOSITION_RUN_ID = "composition-materialization-20260328-broadened"
TRANSITION_RUN_ID = "transition-state-candidate-materialization-20260328-broadened"
STRANDED_RUN_ID = "stranded-resurfacing-materialization-20260328"
ENHANCED_INTERPRETATION_RUN_ID = "enhanced-interpretation-ingestion-20260328-broadened"

LANE_CAPS = {
    "market_design": 10,
    "settlement_resolution": 10,
    "participant_pathologies": 8,
    "state_graph": 8,
    "lifecycle": 8,
    "stranded_qfin": 8,
    "transition_state": 8,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize the DS3 early-market failure-mode ledger.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--bridge-run-id", default=BRIDGE_RUN_ID)
    parser.add_argument("--composition-run-id", default=COMPOSITION_RUN_ID)
    parser.add_argument("--transition-run-id", default=TRANSITION_RUN_ID)
    parser.add_argument("--stranded-run-id", default=STRANDED_RUN_ID)
    parser.add_argument("--enhanced-interpretation-run-id", default=ENHANCED_INTERPRETATION_RUN_ID)
    return parser.parse_args()


def normalized_score(operator_family: str, raw_score: float) -> float:
    if operator_family == "bridge":
        return min(1.5, raw_score / 2.7)
    if operator_family == "composition":
        return min(1.8, raw_score / 3.5)
    if operator_family == "transition_state":
        return min(1.4, raw_score / 0.8)
    if operator_family == "stranded_qfin":
        return min(1.4, raw_score / 0.45)
    return 0.0


def pair_ref(anchor_a: str, anchor_b: str) -> str:
    return f"{anchor_a}__{anchor_b}"


def fetch_interpretation_map(connection: sqlite3.Connection, run_id: str) -> dict[tuple[str, str, str], sqlite3.Row]:
    interpretation_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(enhanced_interpretations)").fetchall()
    }
    lane_expr = "lane_family" if "lane_family" in interpretation_columns else "operator_family"
    rows = connection.execute(
        """
        SELECT
          """
        + lane_expr
        + """
          AS lane_family,
          source_kind,
          source_ref,
          result_summary,
          first_step,
          modern_equivalent,
          why_stranded_or_unrealized,
          gap_to_close,
          confidence
        FROM enhanced_interpretations
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    interpretation_map: dict[tuple[str, str, str], sqlite3.Row] = {}
    for row in rows:
        interpretation_map[(row["lane_family"], row["source_kind"], row["source_ref"])] = row
    return interpretation_map


def infer_lane(anchor_ids: list[str], operator_family: str, pattern_id: str | None) -> str:
    anchor_set = set(anchor_ids)
    if operator_family == "stranded_qfin":
        return "stranded_qfin"
    if operator_family == "transition_state":
        return "transition_state"
    if "lifecycle_professionalization" in anchor_set:
        return "lifecycle"
    if {"amm_settlement_latency", "settlement_resolution_seams"} & anchor_set:
        return "settlement_resolution"
    if {"state_graph_inconsistencies", "parity_propagation", "parity_propagation_delayed_repair"} & anchor_set:
        return "state_graph"
    if "participant_pathologies" in anchor_set:
        return "participant_pathologies"
    if {"market_design_seams", "auction_handoff", "auction_parimutuel_design"} & anchor_set:
        return "market_design"
    return "transition_state"


def signal_flags(title: str, primary_category: str | None, lane_family: str, anchor_ids: list[str]) -> dict[str, float]:
    lowered = title.lower()
    anchor_set = set(anchor_ids)
    lifecycle = 1.0 if lane_family == "lifecycle" or "lifecycle_professionalization" in anchor_set else 0.0
    rule = 1.0 if {"market_design_seams", "auction_handoff", "auction_parimutuel_design"} & anchor_set else 0.0
    settlement = 1.0 if {"amm_settlement_latency", "settlement_resolution_seams"} & anchor_set else 0.0
    pathology = 1.0 if "participant_pathologies" in anchor_set else 0.0
    graph = 1.0 if {"state_graph_inconsistencies", "parity_propagation", "parity_propagation_delayed_repair"} & anchor_set else 0.0
    thin_keywords = [
        "emerging",
        "decentralized",
        "liquidation",
        "auction",
        "otc",
        "credit",
        "double auction",
        "market making",
        "liquidity provider",
        "adoption",
        "fragment",
    ]
    thinness = 1.0 if any(keyword in lowered for keyword in thin_keywords) or lane_family in {"lifecycle", "settlement_resolution", "state_graph"} else 0.0
    non_qfin = 1.0 if not (primary_category or "").startswith("q-fin") else 0.0
    return {
        "lifecycle": lifecycle,
        "rule": rule,
        "settlement": settlement,
        "pathology": pathology,
        "graph": graph,
        "thinness": thinness,
        "non_qfin": non_qfin,
    }


def failure_mode_for(candidate: dict) -> str:
    lane = candidate["lane_family"]
    anchors = set(candidate["anchor_ids"])
    pattern_id = candidate.get("pattern_id")
    if lane == "settlement_resolution" and ({"state_graph_inconsistencies", "parity_propagation_delayed_repair"} & anchors):
        return "Delayed consistency repair across asynchronously settled markets"
    if lane == "settlement_resolution":
        return "Execution-finality gap leaves repair trades open"
    if lane == "participant_pathologies":
        return "Rule-exposed toxic or manipulative flow persists longer than expected"
    if lane == "state_graph":
        return "Cross-market state disagreement survives longer than naive arbitrage expects"
    if lane == "lifecycle":
        return "Professionalization lag leaves early-market rule seams unclosed"
    if lane == "market_design" and {"refill_lag_local_shock", "refill_lag_resiliency"} & anchors:
        return "Venue rules amplify post-shock liquidity recovery asymmetry"
    if lane == "market_design":
        return "Venue design creates durable execution asymmetry in thin markets"
    if lane == "stranded_qfin":
        return "Stranded illiquidity-aware execution control remains untranslated"
    if pattern_id == "near_transition_auction_queue":
        return "Post-uncrossing queue value resets faster than traders adapt"
    if pattern_id == "near_transition_auction_refill":
        return "Post-auction refill asymmetry leaves a brief execution seam"
    if pattern_id == "near_transition_maker_queue":
        return "Maker retreat breaks queue-value assumptions during stress"
    if pattern_id == "near_transition_parity_repair":
        return "Local shock delays parity repair across linked venues"
    return "Shock-recovery queue value remains mispriced during transition states"


def wrong_actor_for(candidate: dict) -> str:
    lane = candidate["lane_family"]
    if lane == "settlement_resolution":
        return "clearing stack, collateral managers, and undercapitalized arbitrageurs"
    if lane == "participant_pathologies":
        return "toxic, manipulative, or latency-sensitive participants"
    if lane == "state_graph":
        return "cross-venue arbitrage desks and fragmented venue operators"
    if lane == "lifecycle":
        return "thin early liquidity providers and new-venue operators"
    if lane == "market_design":
        return "venue designers, routing logic, and rule-takers adapting too slowly"
    if lane == "stranded_qfin":
        return "research and execution teams that left the result in theory language"
    return "post-shock passive liquidity providers and event-driven market makers"


def what_closes_it_for(candidate: dict) -> str:
    lane = candidate["lane_family"]
    if lane == "settlement_resolution":
        return "faster settlement synchronization, tighter collateral plumbing, and capital committed to repair trades"
    if lane == "participant_pathologies":
        return "toxicity-aware quoting, stronger venue controls, or rule changes that stop exposing the same flow pathology"
    if lane == "state_graph":
        return "rule harmonization plus capitalized cross-venue arbitrage that can keep linked states synchronized"
    if lane == "lifecycle":
        return "professional market making, denser participation, and market-structure hardening"
    if lane == "market_design":
        return "priority, fee, or matching-rule changes that stop amplifying the same recovery or routing gap"
    if lane == "stranded_qfin":
        return "explicit implementation, modern replay validation, and translation out of math-finance language"
    return "explicit transition-state models and deeper event-level liquidity provision"


def market_stage_for(candidate: dict) -> str:
    lane = candidate["lane_family"]
    if lane == "settlement_resolution":
        return "fragmented or delayed-settlement market"
    if lane == "participant_pathologies":
        return "thin, weakly policed, or manipulation-prone market"
    if lane == "state_graph":
        return "weakly arbitraged multi-venue or cross-instrument market"
    if lane == "lifecycle":
        return "pre-professionalization or newly electronified market"
    if lane == "market_design":
        return "early rule-setting or still-maturing venue"
    if lane == "stranded_qfin":
        return "modern but still illiquidity-constrained market"
    return "maturing electronic-book regime"


def default_first_test(candidate: dict) -> str:
    lane = candidate["lane_family"]
    if lane == "settlement_resolution":
        return "Measure whether settlement-cycle, margin, or close-out timing predicts delayed convergence after an obvious cross-market inconsistency."
    if lane == "participant_pathologies":
        return "Build participant-toxicity proxies and test whether the same venue states repeatedly precede adverse-selection spikes."
    if lane == "state_graph":
        return "Construct a venue state graph and test whether rule mismatches explain how long parity gaps remain open."
    if lane == "lifecycle":
        return "Split a market into early and mature regimes and test whether the same rule produces larger gaps before professionalization."
    if lane == "market_design":
        return "Replay venue rule changes and test whether refill, routing, or execution asymmetries change around the rule boundary."
    if lane == "stranded_qfin":
        return "Re-estimate the control on modern intraday data and compare it to simpler adaptive execution baselines."
    return "Measure whether the transition event changes fill quality faster than naive spread or imbalance baselines adapt."


def source_ref_for(operator_family: str, anchor_ids: list[str], pattern_id: str | None, paper_id: str) -> tuple[str, str]:
    if operator_family == "transition_state":
        return "transition_state_candidate", pattern_id or ""
    if operator_family == "stranded_qfin":
        return "stranded_resurfacing_candidate", paper_id
    return f"{operator_family}_candidate_pair", pair_ref(anchor_ids[0], anchor_ids[1])


def interpretation_for(candidate: dict, interpretation_map: dict[tuple[str, str, str], sqlite3.Row]) -> sqlite3.Row | None:
    source_kind, source_ref = source_ref_for(
        candidate["source_operator_family"],
        candidate["anchor_ids"],
        candidate.get("pattern_id"),
        candidate["paper_id"],
    )
    lane = candidate["lane_family"]
    direct = interpretation_map.get((lane, source_kind, source_ref))
    if direct is not None:
        return direct
    if source_kind.endswith("_pair"):
        anchor_a, anchor_b = source_ref.split("__", 1)
        reversed_ref = pair_ref(anchor_b, anchor_a)
        return interpretation_map.get((lane, source_kind, reversed_ref))
    return None


def early_market_score(candidate: dict, interpretation: sqlite3.Row | None) -> float:
    flags = candidate["signals"]
    base = candidate["normalized_source_score"]
    score = (
        base
        + 1.2 * flags["lifecycle"]
        + 1.1 * flags["settlement"]
        + 1.0 * flags["rule"]
        + 1.0 * flags["pathology"]
        + 1.0 * flags["graph"]
        + 0.8 * flags["thinness"]
        + 0.5 * flags["non_qfin"]
    )
    if interpretation is not None:
        score += 0.8
    if candidate["lane_family"] == "transition_state" and sum(flags[key] for key in ("lifecycle", "settlement", "rule", "pathology", "graph")) == 0:
        score -= 0.7
    return round(score, 6)


def fetch_operator_candidates(connection: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    candidates: list[dict] = []
    for table, run_id, operator_family, score_col in [
        ("bridge_candidates", args.bridge_run_id, "bridge", "bridge_score"),
        ("composition_candidates", args.composition_run_id, "composition", "composition_score"),
    ]:
        rows = connection.execute(
            f"""
            SELECT
              candidate.paper_id,
              paper.title,
              paper.primary_category,
              candidate.source_anchor_id,
              candidate.target_anchor_id,
              candidate.{score_col} AS raw_score
            FROM {table} candidate
            JOIN papers paper
              ON paper.paper_id = candidate.paper_id
            WHERE candidate.run_id = ?
            """,
            (run_id,),
        ).fetchall()
        for row in rows:
            anchor_ids = [row["source_anchor_id"], row["target_anchor_id"]]
            lane_family = infer_lane(anchor_ids, operator_family, None)
            candidates.append(
                {
                    "paper_id": row["paper_id"],
                    "title": row["title"],
                    "home_domain": row["primary_category"],
                    "lane_family": lane_family,
                    "source_operator_family": operator_family,
                    "anchor_ids": anchor_ids,
                    "pattern_id": None,
                    "raw_source_score": round(float(row["raw_score"]), 6),
                    "normalized_source_score": round(normalized_score(operator_family, float(row["raw_score"])), 6),
                }
            )
    transition_rows = connection.execute(
        """
        SELECT
          candidate.paper_id,
          paper.title,
          paper.primary_category,
          candidate.pattern_id,
          candidate.transition_state_candidate_score AS raw_score
        FROM transition_state_candidates candidate
        JOIN papers paper
          ON paper.paper_id = candidate.paper_id
        WHERE candidate.run_id = ?
        """,
        (args.transition_run_id,),
    ).fetchall()
    for row in transition_rows:
        candidates.append(
            {
                "paper_id": row["paper_id"],
                "title": row["title"],
                "home_domain": row["primary_category"],
                "lane_family": "transition_state",
                "source_operator_family": "transition_state",
                "anchor_ids": [],
                "pattern_id": row["pattern_id"],
                "raw_source_score": round(float(row["raw_score"]), 6),
                "normalized_source_score": round(normalized_score("transition_state", float(row["raw_score"])), 6),
            }
        )
    stranded_rows = connection.execute(
        """
        SELECT
          candidate.paper_id,
          paper.title,
          paper.primary_category,
          candidate.resurfacing_score AS raw_score
        FROM stranded_resurfacing_candidates candidate
        JOIN papers paper
          ON paper.paper_id = candidate.paper_id
        WHERE candidate.run_id = ?
        """,
        (args.stranded_run_id,),
    ).fetchall()
    for row in stranded_rows:
        candidates.append(
            {
                "paper_id": row["paper_id"],
                "title": row["title"],
                "home_domain": row["primary_category"],
                "lane_family": "stranded_qfin",
                "source_operator_family": "stranded_qfin",
                "anchor_ids": [],
                "pattern_id": None,
                "raw_source_score": round(float(row["raw_score"]), 6),
                "normalized_source_score": round(normalized_score("stranded_qfin", float(row["raw_score"])), 6),
            }
        )
    return candidates


def build_rows(connection: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    interpretation_map = fetch_interpretation_map(connection, args.enhanced_interpretation_run_id)
    raw_candidates = fetch_operator_candidates(connection, args)
    best_by_paper: dict[str, dict] = {}
    for candidate in raw_candidates:
        candidate["signals"] = signal_flags(
            candidate["title"],
            candidate["home_domain"],
            candidate["lane_family"],
            candidate["anchor_ids"],
        )
        interpretation = interpretation_for(candidate, interpretation_map)
        candidate["interpretation"] = interpretation
        candidate["early_market_score"] = early_market_score(candidate, interpretation)
        candidate["failure_mode"] = failure_mode_for(candidate)
        candidate["wrong_actor"] = wrong_actor_for(candidate)
        candidate["why_persists"] = (
            interpretation["why_stranded_or_unrealized"]
            if interpretation is not None
            else f"This persists because {candidate['lane_family'].replace('_', ' ')} evidence exists in the corpus but is still fragmented across operator surfaces rather than translated into an explicit early-market workflow."
        )
        candidate["what_closes_it"] = what_closes_it_for(candidate)
        candidate["likely_market_stage"] = market_stage_for(candidate)
        candidate["first_test"] = interpretation["first_step"] if interpretation is not None else default_first_test(candidate)
        candidate["modern_equivalent"] = interpretation["modern_equivalent"] if interpretation is not None else None
        existing = best_by_paper.get(candidate["paper_id"])
        if existing is None or (
            candidate["early_market_score"],
            candidate["lane_family"] != "transition_state",
            candidate["normalized_source_score"],
        ) > (
            existing["early_market_score"],
            existing["lane_family"] != "transition_state",
            existing["normalized_source_score"],
        ):
            best_by_paper[candidate["paper_id"]] = candidate

    ranked = sorted(
        best_by_paper.values(),
        key=lambda item: (
            -item["early_market_score"],
            item["lane_family"] == "transition_state",
            -item["normalized_source_score"],
            item["paper_id"],
        ),
    )
    selected: list[dict] = []
    lane_counts = {lane: 0 for lane in LANE_CAPS}
    for candidate in ranked:
        lane = candidate["lane_family"]
        if lane_counts.get(lane, 0) >= LANE_CAPS.get(lane, args.top_k):
            continue
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
        selected.append(
            {
                "rank": len(selected) + 1,
                "paper_id": candidate["paper_id"],
                "title": candidate["title"],
                "home_domain": candidate["home_domain"],
                "lane_family": lane,
                "source_operator_family": candidate["source_operator_family"],
                "failure_mode": candidate["failure_mode"],
                "wrong_actor": candidate["wrong_actor"],
                "why_persists": candidate["why_persists"],
                "what_closes_it": candidate["what_closes_it"],
                "likely_market_stage": candidate["likely_market_stage"],
                "first_test": candidate["first_test"],
                "early_market_score": candidate["early_market_score"],
                "non_transition_dominant": lane != "transition_state",
            }
        )
        if len(selected) >= args.top_k:
            break
    return selected


def count_by_key(rows: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row[key]] = counts.get(row[key], 0) + 1
    return dict(sorted(counts.items()))


def render_report(rows: list[dict], metrics: dict) -> str:
    lines = [
        "# DS3 Early-Market Failure Mode Ledger",
        "",
        "This study ranks failure modes specific to thin, weakly arbitraged, early, delayed-settlement, or still-professionalizing markets.",
        "",
        "## Stop / Go",
        "",
        f"- ledger entries materialized: `{metrics['entry_count']}`",
        f"- non-transition-state entries: `{metrics['non_transition_count']}`",
        f"- success threshold met: `{str(metrics['success']).lower()}`",
        "",
        "## Candidate-Family Diversity",
        "",
    ]
    for lane, count in metrics["counts_by_lane"].items():
        lines.append(f"- {lane}: `{count}`")
    lines.extend(["", "## Operator Mix", ""])
    for family, count in metrics["counts_by_operator"].items():
        lines.append(f"- {family}: `{count}`")
    lines.extend(["", "## Top 20 Preview", ""])
    for row in rows[:20]:
        lines.extend(
            [
                f"- `{row['paper_id']}` | `{row['lane_family']}` | score `{row['early_market_score']}`",
                f"  failure mode: {row['failure_mode']}",
                f"  likely stage: {row['likely_market_stage']}",
                f"  first test: {row['first_test']}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def log_run_event(connection: sqlite3.Connection, metrics: dict, reports_dir: Path) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (
            "ds3-early-market-failure-ledger",
            "diamond_study",
            "completed",
            json.dumps(
                {
                    "entry_count": metrics["entry_count"],
                    "non_transition_count": metrics["non_transition_count"],
                    "success": metrics["success"],
                    "reports_dir": str(reports_dir),
                },
                sort_keys=True,
            ),
        ),
    )


def main() -> None:
    args = parse_args()
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        rows = build_rows(connection, args)
        metrics = {
            "entry_count": len(rows),
            "non_transition_count": sum(1 for row in rows if row["non_transition_dominant"]),
            "counts_by_lane": count_by_key(rows, "lane_family"),
            "counts_by_operator": count_by_key(rows, "source_operator_family"),
        }
        metrics["success"] = metrics["non_transition_count"] >= 15

        jsonl_path = reports_dir / "ds3-early-market-ledger.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown_path = reports_dir / "ds3-early-market-ledger.md"
        markdown_path.write_text(render_report(rows, metrics), encoding="utf-8")

        log_run_event(connection, metrics, reports_dir)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
