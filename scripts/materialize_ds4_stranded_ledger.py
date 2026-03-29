#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_REPORTS_DIR = ROOT / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize the DS4 stranded q-fin rescue ledger.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--stranded-run-id", default="stranded-resurfacing-materialization-20260328")
    parser.add_argument("--enhanced-interpretation-run-id", default="enhanced-interpretation-ingestion-20260328-broadened")
    parser.add_argument("--top-k", type=int, default=15)
    return parser.parse_args()


def fetch_interpretation_map(connection: sqlite3.Connection, run_id: str) -> dict[str, sqlite3.Row]:
    lane_columns = {row["name"] for row in connection.execute("PRAGMA table_info(enhanced_interpretations)").fetchall()}
    lane_filter = "lane_family = 'stranded_qfin'" if "lane_family" in lane_columns else "operator_family = 'stranded_qfin'"
    rows = connection.execute(
        f"""
        SELECT
          source_ref,
          result_summary,
          first_step,
          instrument_assumed,
          modern_equivalent,
          why_stranded_or_unrealized,
          gap_to_close,
          confidence
        FROM enhanced_interpretations
        WHERE run_id = ?
          AND {lane_filter}
        """,
        (run_id,),
    ).fetchall()
    return {row["source_ref"]: row for row in rows}


def family_for(title: str, primary_category: str) -> str:
    lowered = title.lower()
    if "execution" in lowered or "liquidation" in lowered or "surrogate" in lowered:
        return "execution_control"
    if "portfolio" in lowered or "asset" in lowered:
        return "portfolio_control"
    if "contagion" in lowered or "capital ratio" in lowered or "liquidation prices" in lowered:
        return "contagion_stress"
    if "variance swap" in lowered or "derivative" in lowered or "stochastic volatility" in lowered:
        return "derivatives_surface"
    if "yield curve" in lowered or "interest rate" in lowered:
        return "funding_curve"
    if "bubble" in lowered or "first passage" in lowered:
        return "regime_timing"
    if "reinsurance" in lowered or "insurance" in lowered:
        return "risk_transfer"
    if "policy" in lowered or "ramsey" in lowered:
        return "macro_policy"
    if "calibration" in lowered or "smile" in lowered:
        return "calibration_speedup"
    return "general_qfin"


def heuristic_fields(title: str, primary_category: str, family: str) -> dict[str, str | bool]:
    if family == "execution_control":
        return {
            "result_plain": "The paper contains an execution or liquidation control that can be replayed as a concrete scheduling policy on modern market data.",
            "instrument_assumed": "fragmented equities, futures, or large-inventory liquidation books",
            "why_stranded_then": "It was published as control, calibration, or optimal-execution theory rather than as an implementation memo.",
            "modern_equivalent_now": "adaptive execution schedule or liquidation-control benchmark",
            "first_implementation_test": "Replay the control on modern intraday data against TWAP, POV, and simple imbalance-aware baselines.",
            "gap_to_close": "Need modern venue-fragmentation, hidden-liquidity, and fee-model robustness checks.",
            "why_not_just_theory": "The control can be evaluated directly with historical order-book or execution-replay data, so it already defines a falsifiable implementation task.",
            "executable_research_task": True,
            "confidence": "medium",
        }
    if family == "portfolio_control":
        return {
            "result_plain": "The paper proposes a portfolio or factor control rule that may become useful when markets are thin, latent-state driven, or incompletely arbitraged.",
            "instrument_assumed": "multi-asset allocation or stat-arb books with latent-state risk",
            "why_stranded_then": "It stayed in portfolio-construction language instead of being reframed as a live market-friction or timing task.",
            "modern_equivalent_now": "state-aware portfolio throttle or inventory-risk overlay",
            "first_implementation_test": "Backtest the rule as a portfolio overlay during thin-liquidity or latent-factor stress windows rather than over the full sample.",
            "gap_to_close": "Need a mapping from the latent-state model to observable market-stage or liquidity indicators.",
            "why_not_just_theory": "The proposal can be stress-tested as a concrete overlay on real portfolio paths and compared with simpler inventory or factor controls.",
            "executable_research_task": True,
            "confidence": "medium",
        }
    if family == "contagion_stress":
        return {
            "result_plain": "The paper identifies a transmission rule for forced selling, balance-sheet stress, or contagion that can be turned into a monitoring and intervention model.",
            "instrument_assumed": "cross-asset stress books, dealer balance-sheet monitoring, or fire-sale risk overlays",
            "why_stranded_then": "It was framed as systemic-risk or regulatory theory rather than as an operational stress signal.",
            "modern_equivalent_now": "liquidity-stress contagion monitor",
            "first_implementation_test": "Build a stress monitor that flags when capital, VWAP liquidation, or credit constraints imply nonlinear spillovers across linked books.",
            "gap_to_close": "Need observable proxies for balance-sheet constraints and forced-liquidation pathways.",
            "why_not_just_theory": "The mechanism implies measurable state variables and event pathways that can be tested against historical stress episodes.",
            "executable_research_task": True,
            "confidence": "medium",
        }
    if family == "derivatives_surface":
        return {
            "result_plain": "The paper offers a pricing or hedging structure that may expose incomplete-market dislocations if translated into observable surface diagnostics.",
            "instrument_assumed": "listed or OTC derivatives with incomplete hedging and sparse market-making",
            "why_stranded_then": "It remained trapped in valuation language instead of being translated into a screen for surface or hedge dislocations.",
            "modern_equivalent_now": "surface-consistency or hedge-break monitor",
            "first_implementation_test": "Track whether the model-implied surface inconsistency predicts later repricing or hedge slippage in thin derivatives markets.",
            "gap_to_close": "Need a direct mapping from the model variables to observable surface, borrow, and liquidity measurements.",
            "why_not_just_theory": "The result becomes testable once the model is recast as a monitor for observed surface breaks, though the implementation burden is higher than for execution papers.",
            "executable_research_task": False,
            "confidence": "low",
        }
    if family == "funding_curve":
        return {
            "result_plain": "The paper describes a curve or calibration structure that may reveal funding-friction or basis seams in incomplete fixed-income markets.",
            "instrument_assumed": "rates, funding, or basis books with multiple curves and sparse liquidity",
            "why_stranded_then": "It was left in rates-model calibration language, which obscured the market-friction timing angle.",
            "modern_equivalent_now": "funding-curve stress monitor",
            "first_implementation_test": "Test whether curve-fit stress or multi-curve inconsistency predicts later basis repair in thin funding markets.",
            "gap_to_close": "Need observable mapping from calibration stress to tradeable funding dislocations.",
            "why_not_just_theory": "The result is closer to a monitor than a ready strategy, but it still suggests a falsifiable timing diagnostic.",
            "executable_research_task": False,
            "confidence": "low",
        }
    if family == "regime_timing":
        return {
            "result_plain": "The paper models a regime transition or bubble-timing process that may help detect fragile, weakly arbitraged market states before repair arrives.",
            "instrument_assumed": "speculative or thinly arbitraged markets with regime-switching risk",
            "why_stranded_then": "It was framed as regime or bubble theory instead of a monitor for thin-market instability.",
            "modern_equivalent_now": "fragility-regime timing indicator",
            "first_implementation_test": "Test whether the model’s regime signal identifies periods where cross-market repair slows or liquidity thins abruptly.",
            "gap_to_close": "Need a stable mapping from latent regime variables to observable fragility signals.",
            "why_not_just_theory": "This is testable as a regime indicator, but it is further from direct implementation than the execution and contagion rescues.",
            "executable_research_task": False,
            "confidence": "low",
        }
    if family == "risk_transfer":
        return {
            "result_plain": "The paper proposes a risk-transfer structure that may become useful when markets cannot clear risk quickly through standard liquidity providers.",
            "instrument_assumed": "insurance, reinsurance, or structured-risk transfer markets",
            "why_stranded_then": "It stayed inside contract-design language rather than being converted into a timing or inventory-constraint workflow.",
            "modern_equivalent_now": "risk-transfer stress overlay",
            "first_implementation_test": "Test whether the proposed structure improves risk transfer during thin-liquidity or delayed-repair regimes compared with vanilla hedges.",
            "gap_to_close": "Need an operational setting where the contract terms can be approximated or simulated realistically.",
            "why_not_just_theory": "The idea can be simulated, but it is not yet as directly executable as the execution-control and contagion rescues.",
            "executable_research_task": False,
            "confidence": "low",
        }
    if family == "macro_policy":
        return {
            "result_plain": "The paper contains a policy-control structure that is too far from a trading implementation to count as a near-term executable edge.",
            "instrument_assumed": "macro or policy-sensitive markets",
            "why_stranded_then": "It belongs to policy design more than trading implementation.",
            "modern_equivalent_now": "policy-regime sensitivity monitor",
            "first_implementation_test": "Check whether the policy-state proxy helps explain later thin-market dislocations, rather than trading it directly.",
            "gap_to_close": "Need a much tighter bridge between policy variables and tradeable market states.",
            "why_not_just_theory": "This remains mainly theoretical for DS4 purposes and is included to keep the rescue queue honest about what is and is not executable.",
            "executable_research_task": False,
            "confidence": "low",
        }
    if family == "calibration_speedup":
        return {
            "result_plain": "The paper speeds model calibration or approximation in a way that might matter if calibration latency itself creates a missed execution or hedging opportunity.",
            "instrument_assumed": "derivatives desks or execution systems with repeated recalibration needs",
            "why_stranded_then": "The contribution was presented as numerical convenience rather than as a way to shorten the decision loop.",
            "modern_equivalent_now": "fast calibration proxy in a live decision loop",
            "first_implementation_test": "Test whether faster recalibration materially changes hedge or execution decisions during rapidly moving but thin markets.",
            "gap_to_close": "Need evidence that calibration latency, not just model error, is the limiting operational bottleneck.",
            "why_not_just_theory": "It becomes concrete only if calibration speed changes a real trading or hedging decision, so this is an executable hypothesis but not yet a full workflow.",
            "executable_research_task": True,
            "confidence": "low",
        }
    return {
        "result_plain": "The paper may hide a usable market-friction or implementation clue, but the rescue path is still underspecified.",
        "instrument_assumed": f"{primary_category} market setting",
        "why_stranded_then": "The result remained in specialist q-fin language instead of being translated into an operational workflow.",
        "modern_equivalent_now": "untranslated q-fin mechanism needing modern recast",
        "first_implementation_test": "Translate the core state variables into observable market features and test whether they predict a repeatable decision edge.",
        "gap_to_close": "Need a clearer mapping from theory variables to observable market-state measurements.",
        "why_not_just_theory": "There is a plausible implementation path, but it is still too generic to count as a strong executable rescue yet.",
        "executable_research_task": False,
        "confidence": "low",
    }


def forced_translation_for(row: sqlite3.Row, interpretation: sqlite3.Row | None) -> dict:
    title = row["title"]
    primary_category = row["primary_category"] or "unknown"
    family = family_for(title, primary_category)
    if interpretation is not None:
        return {
            "rescue_family": family,
            "result_plain": interpretation["result_summary"],
            "instrument_assumed": interpretation["instrument_assumed"],
            "why_stranded_then": interpretation["why_stranded_or_unrealized"],
            "modern_equivalent_now": interpretation["modern_equivalent"],
            "first_implementation_test": interpretation["first_step"],
            "gap_to_close": interpretation["gap_to_close"],
            "why_not_just_theory": "The result already specifies a concrete modern replay or implementation comparison, so it can be evaluated as a live research task rather than only as a theorem.",
            "confidence": interpretation["confidence"],
            "executable_research_task": True,
        }
    heuristic = heuristic_fields(title, primary_category, family)
    heuristic["rescue_family"] = family
    return heuristic


def render_report(rows: list[dict], executable_count: int, family_counts: dict[str, int]) -> str:
    lines = [
        "# DS4 Stranded Result Ledger",
        "",
        "This study forces top stranded q-fin papers into explicit modern implementation paths instead of leaving them in theory language.",
        "",
        "## Stop / Go",
        "",
        f"- stranded entries materialized: `{len(rows)}`",
        f"- executable-looking rescues: `{executable_count}`",
        f"- success threshold met: `{str(executable_count >= 5).lower()}`",
        "",
        "## Rescue-Family Diversity",
        "",
    ]
    for family, count in sorted(family_counts.items()):
        lines.append(f"- {family}: `{count}`")
    lines.extend(["", "## Entries", ""])
    for row in rows:
        lines.extend(
            [
                f"## {row['rescue_rank']}. {row['paper_id']} — {row['title']}",
                "",
                f"- home domain: `{row['home_domain']}`",
                f"- date: `{row['published_at']}`",
                f"- rescue family: `{row['rescue_family']}`",
                f"- confidence: `{row['confidence']}`",
                f"- executable research task: `{str(row['executable_research_task']).lower()}`",
                "",
                f"Result plain: {row['result_plain']}",
                "",
                f"Instrument assumed: {row['instrument_assumed']}",
                "",
                f"Why stranded then: {row['why_stranded_then']}",
                "",
                f"Modern equivalent now: {row['modern_equivalent_now']}",
                "",
                f"First implementation test: {row['first_implementation_test']}",
                "",
                f"Gap to close: {row['gap_to_close']}",
                "",
                f"Why not just theory: {row['why_not_just_theory']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def log_run_event(connection: sqlite3.Connection, reports_dir: Path, entry_count: int, executable_count: int) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (
            "ds4-stranded-qfin-rescue",
            "diamond_study",
            "completed",
            json.dumps(
                {
                    "reports_dir": str(reports_dir),
                    "entry_count": entry_count,
                    "executable_count": executable_count,
                    "success": executable_count >= 5,
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
        interpretation_map = fetch_interpretation_map(connection, args.enhanced_interpretation_run_id)
        rows = connection.execute(
            """
            SELECT
              candidate.paper_id,
              candidate.resurfacing_score,
              candidate.resurfacing_rank,
              paper.title,
              paper.primary_category,
              paper.published_at
            FROM stranded_resurfacing_candidates candidate
            JOIN papers paper
              ON paper.paper_id = candidate.paper_id
            WHERE candidate.run_id = ?
            ORDER BY candidate.resurfacing_rank ASC, candidate.paper_id ASC
            LIMIT ?
            """,
            (args.stranded_run_id, args.top_k),
        ).fetchall()

        output_rows = []
        family_counts: dict[str, int] = {}
        executable_count = 0
        for rank, row in enumerate(rows, start=1):
            interpretation = interpretation_map.get(row["paper_id"])
            translated = forced_translation_for(row, interpretation)
            family_counts[translated["rescue_family"]] = family_counts.get(translated["rescue_family"], 0) + 1
            if translated["executable_research_task"]:
                executable_count += 1
            output_rows.append(
                {
                    "rescue_rank": rank,
                    "paper_id": row["paper_id"],
                    "title": row["title"],
                    "published_at": row["published_at"],
                    "home_domain": row["primary_category"],
                    "resurfacing_score": round(float(row["resurfacing_score"]), 6),
                    "rescue_family": translated["rescue_family"],
                    "result_plain": translated["result_plain"],
                    "instrument_assumed": translated["instrument_assumed"],
                    "why_stranded_then": translated["why_stranded_then"],
                    "modern_equivalent_now": translated["modern_equivalent_now"],
                    "first_implementation_test": translated["first_implementation_test"],
                    "gap_to_close": translated["gap_to_close"],
                    "why_not_just_theory": translated["why_not_just_theory"],
                    "confidence": translated["confidence"],
                    "executable_research_task": translated["executable_research_task"],
                }
            )

        jsonl_path = reports_dir / "ds4-stranded-ledger.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in output_rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown_path = reports_dir / "ds4-stranded-ledger.md"
        markdown_path.write_text(render_report(output_rows, executable_count, family_counts), encoding="utf-8")

        log_run_event(connection, reports_dir, len(output_rows), executable_count)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
