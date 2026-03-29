#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_REPORTS_ROOT = ROOT / "reports"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize focused lane memos from the current diamond publication state.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="lane-memos-20260329")
    parser.add_argument("--reports-root", default=str(DEFAULT_REPORTS_ROOT))
    parser.add_argument("--diamond-board-path", default=str(ROOT / "diamond_board.md"))
    parser.add_argument("--findings-path", default=str(ROOT / "findings_and_throwaways.md"))
    parser.add_argument("--research-output-path", default=str(ROOT / "research_output.md"))
    parser.add_argument(
        "--memo-id",
        choices=[
            "market-design-delayed-parity-repair",
            "settlement-lag-resolution-friction-timing",
            "rule-sensitive-toxic-flow-filters",
            "state-graph-repair-timing-monitor",
        ],
        default="market-design-delayed-parity-repair",
    )
    return parser.parse_args()


def require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"missing_required_artifact:{path}")
    return path


def read_text(path: Path) -> str:
    return require_file(path).read_text(encoding="utf-8")


def fetch_titles(connection: sqlite3.Connection, paper_ids: list[str]) -> dict[str, str]:
    placeholders = ",".join("?" for _ in paper_ids)
    rows = connection.execute(
        f"SELECT paper_id, title FROM papers WHERE paper_id IN ({placeholders})",
        tuple(paper_ids),
    ).fetchall()
    return {row["paper_id"]: row["title"] for row in rows}


def format_reference(paper_id: str, titles: dict[str, str]) -> str:
    title = titles.get(paper_id, "unknown title")
    return f"`{paper_id}` ({title})"


def ensure_market_design_state(diamond_board_text: str, findings_text: str, research_output_text: str) -> None:
    # @context requirement -- S35 lane memos must codify already-published evidence, not invent
    # fresh leads from hidden artifacts. If these guard strings disappear from the publication
    # surfaces, the memo would be drifting beyond the canonical accepted state.
    if "venue-shaped delayed parity repair" not in diamond_board_text:
        raise ValueError("missing_market_design_clue_in_diamond_board")
    if "market_design:composition:market_design_seams__parity_propagation" not in findings_text:
        raise ValueError("missing_market_design_accept_in_findings")
    if "Cross-market inconsistencies may persist longer when the connected venues enforce different trading or protection rules." not in research_output_text:
        raise ValueError("missing_market_design_thesis_in_research_output")


def ensure_settlement_state(diamond_board_text: str, findings_text: str, research_output_text: str) -> None:
    # @context requirement -- Each S35 memo must be pinned to the accepted root publication
    # wording for its lane. Reusing bridge-study evidence is allowed only after the canonical
    # settlement clue already exists in the root surfaces.
    if "rule-conditioned settlement lag arbitrage" not in diamond_board_text:
        raise ValueError("missing_settlement_clue_in_diamond_board")
    if "settlement_resolution:composition:market_design_seams__settlement_resolution_seams" not in findings_text:
        raise ValueError("missing_settlement_accept_in_findings")
    if "settlement-lag arbitrage and resolution-friction timing" not in research_output_text:
        raise ValueError("missing_settlement_thesis_in_research_output")


def ensure_toxic_flow_state(diamond_board_text: str, findings_text: str, research_output_text: str) -> None:
    if "rule-sensitive toxic-flow filters" not in diamond_board_text:
        raise ValueError("missing_toxic_flow_clue_in_diamond_board")
    if "participant_pathologies:1104.0587" not in findings_text:
        raise ValueError("missing_toxic_flow_accept_in_findings")
    if "Participant pathologies such as toxic or manipulative flow may become more predictable when they interact with specific market-design rules." not in research_output_text:
        raise ValueError("missing_toxic_flow_thesis_in_research_output")


def ensure_state_graph_state(diamond_board_text: str, findings_text: str, research_output_text: str) -> None:
    if "state-graph inconsistency monitor" not in diamond_board_text:
        raise ValueError("missing_state_graph_clue_in_diamond_board")
    if "state_graph:2104.09309" not in findings_text:
        raise ValueError("missing_state_graph_accept_in_findings")
    if "Cross-market inconsistencies may persist longer when the connected venues enforce different trading or protection rules." not in research_output_text:
        raise ValueError("missing_state_graph_thesis_in_research_output")


def build_market_design_parity_repair_memo(titles: dict[str, str]) -> str:
    return "\n".join(
        [
            "# Market-Design Delayed Parity Repair",
            "",
            "## Thesis",
            "",
            "Cross-market parity breaks may last materially longer when linked venues enforce different protection, priority, or tick rules, so repair timing should be modeled as a venue-design state variable rather than as generic arbitrage latency.",
            "",
            "## Why This Lead Exists",
            "",
            "The accepted market-design publication row says rule differences change how quickly linked markets repair temporary inconsistencies. The adjacent transition-state evidence says the edge lives at the repair boundary itself, not in ordinary spread mean reversion. Together, they point to a lane where venue design shapes when a visible inconsistency can actually close.",
            "",
            "## Supporting Papers",
            "",
            f"- {format_reference('1609.04620', titles)}: supports the idea that price impact and repair can behave differently when the market structure is not a simple continuous order book.",
            f"- {format_reference('1811.08038', titles)}: shows that consistency breaks can persist when derivative and credit market state variables do not synchronize cleanly.",
            f"- {format_reference('1709.08238', titles)}: provides a concrete rule-layer example where risk-mitigation mechanics change everyday trading behavior and therefore likely change repair speed.",
            f"- {format_reference('2011.04367', titles)}: gives a direct venue-comparison surface where differing exchange rules can be aligned with convergence timing outcomes.",
            f"- {format_reference('2004.12011', titles)}: grounds the state-graph side of the memo by treating linked-market consistency as a repair problem rather than a single-market signal.",
            "",
            "## Hypothesis",
            "",
            "When two related venues or instruments disagree on price, basis, or implied state, the repair window will be longer and more tradeable when venue rules differ on priority, tick size, protection, or risk controls. The same raw mispricing should repair faster when the rule set is symmetric.",
            "",
            "## Data",
            "",
            "- Two or more linked venues or instruments with synchronized quote and trade timestamps.",
            "- Venue-rule metadata: tick size regime, order-priority rule, auction/protection status, market-order protection, and any counterparty or risk-control constraints that can block immediate repair.",
            "- Full-depth or top-of-book reconstruction around detected parity breaks.",
            "- At least three months of data for one concrete linked pair, such as dual-listed equities, cash/futures, ETF/NAV proxies, or cross-venue FX/crypto pairs.",
            "",
            "## Baseline",
            "",
            "A naive parity monitor that flags deviations above a fixed spread or basis threshold and assumes repair speed depends only on deviation size, volatility, and liquidity, without any venue-design state.",
            "",
            "## Seam-Aware Program",
            "",
            "Track parity breaks jointly with venue-design asymmetry. The first concrete model should classify each event by rule mismatch features such as asymmetric tick size, different priority rules, or protection/auction state mismatch, then estimate whether repair speed, quote fade, and executable convergence differ from matched symmetric-rule events.",
            "",
            "## First Test",
            "",
            "Compare venue rule differences against delayed cross-market convergence after local dislocations. Start with one linked pair, define a parity break, measure time-to-repair, and test whether rule-mismatch windows have slower repair or more favorable execution than matched same-rule windows.",
            "",
            "## Metric",
            "",
            "Primary metric: repair-time delta between rule-mismatch and rule-symmetric events, conditioned on deviation size and contemporaneous liquidity. Secondary metrics: executable capture after fees, quote fade before repair, and adverse selection after entering the convergence trade.",
            "",
            "## Fail-Fast",
            "",
            "- If repair timing is fully explained by volatility and liquidity once rule variables are added, this is not a market-design seam.",
            "- If the result depends on stale timestamps or unaligned feeds, the seam is a data artifact rather than a venue-rule effect.",
            "- If execution cannot be achieved before repair because the relevant venue is too thin or too protected, the lead remains descriptive rather than tradeable.",
            "",
            "## Stop / Go",
            "",
            "Go if at least one rule-mismatch feature materially widens the repair window and improves executable capture relative to the naive parity baseline. Stop if the effect disappears after controlling for event size, venue liquidity, and time-of-day state.",
            "",
            "## Gap To Close",
            "",
            "The remaining gap is a clean venue-rule panel aligned to repair events. Without explicit rule-state annotations, delayed parity repair can still be mistaken for generic fragmentation noise.",
            "",
        ]
    ) + "\n"


def build_settlement_lag_memo(titles: dict[str, str]) -> str:
    return "\n".join(
        [
            "# Settlement-Lag / Resolution-Friction Timing",
            "",
            "## Thesis",
            "",
            "Execution opportunities may persist when trades clear economically before they settle legally or operationally, so timing edges should be modeled around collateral, margin, and resolution-state synchronization rather than around printed price gaps alone.",
            "",
            "## Why This Lead Exists",
            "",
            "The accepted settlement-resolution publication row says settlement frictions and market rules create a seam between economic execution and legal resolution. The broader research memo and DS2 bridge study both push the same claim: some consistency breaks remain tradeable because the post-trade state cannot synchronize immediately even when the market sees the mismatch.",
            "",
            "## Supporting Papers",
            "",
            f"- {format_reference('1811.08038', titles)}: supports the idea that apparent arbitrage can persist when derivative and credit-market state variables do not resolve on the same timetable.",
            f"- {format_reference('1709.08238', titles)}: shows that risk controls and counterparty limits can block immediate repair even in everyday trading.",
            f"- {format_reference('1609.04620', titles)}: gives a market where impact and execution occur without a canonical order book, which makes legal or operational resolution timing more visible.",
            f"- {format_reference('1101.3926', titles)}: grounds the collateral and netting side of the memo by making resolution state explicit instead of treating settlement as background plumbing.",
            f"- {format_reference('1312.0128', titles)}: expands the post-trade state space into CCP, CSA, funding, margin, and closeout mechanics that can all delay practical repair.",
            f"- {format_reference('2106.06389', titles)} and {format_reference('2009.13235', titles)}: show that the same timing seam appears in thin or immature markets where liquidation and settlement mechanics are observable rather than hidden.",
            "",
            "## Hypothesis",
            "",
            "Basis, hedge slippage, or unwind opportunities should be more persistent and more executable when collateral, margin, or closeout state is out of sync with the economic trade state. Events with slower resolution-state synchronization should display wider repair windows than matched events with similar price deviations but cleaner settlement state.",
            "",
            "## Data",
            "",
            "- Execution timestamps and post-trade lifecycle events for at least one market with observable settlement or collateral state.",
            "- Collateral, margin, liquidation, or closeout event markers aligned to the executed position lifecycle.",
            "- Linked hedging or reference-market prices so the repair window can be measured against an external state.",
            "- At least three months of data in one concrete venue family, such as CDS/credit, futures basis, or on-chain liquidation venues with observable settlement mechanics.",
            "",
            "## Baseline",
            "",
            "A price-only basis monitor that flags deviations and assumes repair depends only on spread, volatility, and liquidity, with no explicit model of settlement or resolution-state timing.",
            "",
            "## Seam-Aware Program",
            "",
            "Classify each event by both the economic trade state and the legal or operational resolution state. The first model should separate cleanly settled events from delayed-resolution events, then estimate whether delay state predicts basis persistence, unwind pressure, or hedge slippage after controlling for raw deviation size.",
            "",
            "## First Test",
            "",
            "Test whether settlement timing and venue-rule mismatches create repeatable basis or unwind windows around resolution events. Start with one product family, mark resolution-state transitions, and compare time-to-repair plus executable unwind quality between delayed-resolution and clean-resolution windows.",
            "",
            "## Metric",
            "",
            "Primary metric: repair-window length conditional on observed resolution friction. Secondary metrics: executable capture after fees, hedge slippage during the delay window, and forced-unwind pressure around margin or liquidation boundaries.",
            "",
            "## Fail-Fast",
            "",
            "- If the apparent edge disappears once true resolution-state timestamps are aligned, the signal was only a data-latency artifact.",
            "- If settlement and collateral state cannot be observed with enough fidelity, this memo collapses into a generic basis-trading story.",
            "- If resolution friction predicts persistence but not executable capture after fees and financing, the lead is descriptive rather than actionable.",
            "",
            "## Stop / Go",
            "",
            "Go if delayed-resolution events materially extend the repair window and improve executable capture relative to the price-only baseline. Stop if price deviation, volatility, and liquidity explain the full effect without any incremental contribution from settlement-state variables.",
            "",
            "## Gap To Close",
            "",
            "The remaining gap is synchronized post-trade state data. Without explicit collateral, margin, closeout, or liquidation timing, resolution friction is too easy to confuse with ordinary illiquidity.",
            "",
        ]
    ) + "\n"


def build_toxic_flow_memo(titles: dict[str, str]) -> str:
    return "\n".join(
        [
            "# Rule-Sensitive Toxic-Flow Filters",
            "",
            "## Thesis",
            "",
            "Toxic or manipulative flow should become more predictable when venue rules expose or amplify it, so the right filter is not generic toxicity detection but a venue-state model that conditions flow signatures on priority, latency, and protection rules.",
            "",
            "## Why This Lead Exists",
            "",
            "The accepted participant-pathology publication row says participant pathologies become more repeatable when interpreted through venue-state and rule constraints. The bridge-zone evidence sharpens that into an executable question: which rule settings make informed, predatory, or manipulative behavior visible enough to trade against?",
            "",
            "## Supporting Papers",
            "",
            f"- {format_reference('1104.0587', titles)}: anchors the core question of how markets react to observable order flow rather than to abstract participant labels.",
            f"- {format_reference('0908.0202', titles)}: connects large-order trading profiles to persistent impact signatures that can be filtered rather than merely described.",
            f"- {format_reference('1903.12458', titles)}: frames manipulation as a security problem, which makes rule sensitivity part of the threat surface instead of background context.",
            f"- {format_reference('1311.4160', titles)}: shows that synchronized high-frequency behavior across venues can emerge endogenously when the market design permits it.",
            f"- {format_reference('2006.08682', titles)} and {format_reference('2009.02808', titles)}: provide concrete low-latency and heterogeneous-information surfaces where venue rules likely change how toxic flow appears in the book.",
            f"- {format_reference('2003.04425', titles)}: ties informed trading, the order book, and implementation shortfall together, which is exactly the seam the memo tries to operationalize.",
            "",
            "## Hypothesis",
            "",
            "Cancellation bursts, sweep patterns, or imbalance shocks should have higher predictive value for adverse selection when they occur under specific venue states such as wide-tick regimes, low-latency priority races, auction handoff windows, or weak protection rules. The same raw flow pattern should be less informative outside those states.",
            "",
            "## Data",
            "",
            "- Event-level order-book data with cancellations, modifications, and aggressive trades.",
            "- Venue-state labels: tick regime, priority rule, auction/protection state, latency tier if available, and any visible queue-priority constraints.",
            "- A toxicity proxy such as short-horizon adverse selection, markout, or sweep-induced impact.",
            "- At least three months of data for one venue family so venue-state strata have enough coverage.",
            "",
            "## Baseline",
            "",
            "An unconditional toxic-flow classifier that uses order-flow imbalance, cancellation rate, and sweep count without conditioning on venue state or rule configuration.",
            "",
            "## Seam-Aware Program",
            "",
            "Estimate toxicity only inside explicit rule states. The first pass should segment events by venue state, then ask whether cancellation spikes, sweep bursts, or imbalance shocks predict adverse selection materially better in some rule regimes than in others.",
            "",
            "## First Test",
            "",
            "Segment cancellation and sweep bursts by venue state to test whether toxic-flow episodes become more predictable under specific rule settings. Compare predictive lift for short-horizon markouts between a state-aware filter and the unconditional baseline.",
            "",
            "## Metric",
            "",
            "Primary metric: incremental predictive value for short-horizon adverse selection or markout from adding venue-state interactions. Secondary metrics: false-positive rate on benign flow, fill-quality improvement after filtering, and stability across time-of-day and volatility regimes.",
            "",
            "## Fail-Fast",
            "",
            "- If state conditioning adds no predictive lift beyond plain toxicity proxies, this is not a rule-sensitive seam.",
            "- If the result depends on participant IDs that are not observable in production, the memo is not deployable.",
            "- If the filter only works in one narrow venue state with negligible trade count, the lead is too brittle to matter.",
            "",
            "## Stop / Go",
            "",
            "Go if at least one venue-state interaction materially improves toxic-flow prediction and translates into better passive or reactive execution quality. Stop if venue-state features behave like redundant descriptions of spread and volatility rather than true amplifiers of toxicity.",
            "",
            "## Gap To Close",
            "",
            "The remaining gap is a production-grade toxicity proxy that survives without direct trader identifiers. The memo is strong only if venue state can replace missing participant labels rather than merely complement them in offline analysis.",
            "",
        ]
    ) + "\n"


def build_state_graph_memo(titles: dict[str, str]) -> str:
    return "\n".join(
        [
            "# State-Graph Repair Timing Monitor",
            "",
            "## Thesis",
            "",
            "Linked markets should be monitored as a state graph whose inconsistent edges repair on different clocks, so the tradeable signal is not the raw spread but the timing pattern of which state relationships lag and which ones heal first.",
            "",
            "## Why This Lead Exists",
            "",
            "The accepted state-graph publication row already says the candidate is a repair-timing workflow across temporarily inconsistent market states. The related parity-repair evidence shows that some of these edges become executable only around the repair boundary, which means the operational task is to monitor graph state transitions rather than to chase isolated price gaps.",
            "",
            "## Supporting Papers",
            "",
            f"- {format_reference('2104.09309', titles)}: is the accepted anchor because it frames price response and spread impact in a way that naturally extends to linked-state repair monitoring.",
            f"- {format_reference('1111.7103', titles)}: provides direct high-frequency lead-lag evidence that some linked relationships consistently move before others.",
            f"- {format_reference('2010.15105', titles)}: turns correlated-market response into an explicit spread-impact problem rather than a single-instrument signal.",
            f"- {format_reference('2004.12011', titles)}: grounds the graph view with a concrete multi-leg consistency problem in FX triplets.",
            f"- {format_reference('1609.04620', titles)} and {format_reference('1811.08038', titles)}: show that graph repair can be slowed or distorted when market structure or post-trade state interferes with immediate convergence.",
            "",
            "## Hypothesis",
            "",
            "When a linked market graph enters an inconsistent state, the order and speed with which edges repair should predict where executable hedging slippage or convergence capture is available. Some edges should systematically lag because they sit behind slower liquidity, protection, or settlement states.",
            "",
            "## Data",
            "",
            "- Synchronized prices or quotes for all instruments in one linked graph, such as FX triangles, ETF-basket relationships, or cash-futures pairs.",
            "- A reproducible graph-state definition for each edge, including parity, basis, or implied-price relationships.",
            "- Event timestamps for graph inconsistency onset, partial repair, and full repair.",
            "- At least three months of data so lag structure can be estimated across many repair events.",
            "",
            "## Baseline",
            "",
            "A pairwise spread monitor that treats each inconsistency independently and ignores the order in which the wider graph repairs.",
            "",
            "## Seam-Aware Program",
            "",
            "Construct a live state graph and classify each event by which edges are broken, which edges repair first, and how long each remaining inconsistency survives. The first model should test whether lagging-edge identity improves prediction of executable repair timing beyond pairwise spread size alone.",
            "",
            "## First Test",
            "",
            "Monitor linked markets for transient state disagreement and test whether delayed repair predicts execution quality or hedging slippage. Start with one graph, detect inconsistency events, and compare a graph-aware repair timer against a pairwise spread baseline.",
            "",
            "## Metric",
            "",
            "Primary metric: improvement in repair-time prediction from graph-aware edge-order features over pairwise spread-only features. Secondary metrics: executable convergence capture, hedge slippage during the lag window, and false alarms where pairwise gaps never become tradeable repair events.",
            "",
            "## Fail-Fast",
            "",
            "- If graph-aware features add no signal beyond pairwise spread size, this is not a state-graph seam.",
            "- If synchronization errors across feeds create fake graph lags, the monitor is just measuring data latency.",
            "- If the lagging edge is statistically stable but not executable because liquidity vanishes before repair, the lead is descriptive rather than practical.",
            "",
            "## Stop / Go",
            "",
            "Go if graph-aware lag structure materially improves repair-time prediction and points to better executable capture or lower hedging slippage than pairwise spread monitoring. Stop if the graph collapses to independent pairwise gaps once feed alignment and liquidity controls are applied.",
            "",
            "## Gap To Close",
            "",
            "The remaining gap is a robust event definition for graph inconsistency and repair. Without a stable graph-state ontology, the monitor will drift back into ad hoc spread watching.",
            "",
        ]
    ) + "\n"


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def main():
    args = parse_args()
    reports_root = Path(args.reports_root).resolve()
    diamond_board_text = read_text(Path(args.diamond_board_path).resolve())
    findings_text = read_text(Path(args.findings_path).resolve())
    research_output_text = read_text(Path(args.research_output_path).resolve())
    if args.memo_id == "market-design-delayed-parity-repair":
        ensure_market_design_state(diamond_board_text, findings_text, research_output_text)
    elif args.memo_id == "settlement-lag-resolution-friction-timing":
        ensure_settlement_state(diamond_board_text, findings_text, research_output_text)
    elif args.memo_id == "rule-sensitive-toxic-flow-filters":
        ensure_toxic_flow_state(diamond_board_text, findings_text, research_output_text)
    elif args.memo_id == "state-graph-repair-timing-monitor":
        ensure_state_graph_state(diamond_board_text, findings_text, research_output_text)

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        titles = fetch_titles(
            connection,
            [
                "1609.04620",
                "1811.08038",
                "1709.08238",
                "2011.04367",
                "2004.12011",
                "1101.3926",
                "1312.0128",
                "2106.06389",
                "2009.13235",
                "1104.0587",
                "0908.0202",
                "1903.12458",
                "1311.4160",
                "2006.08682",
                "2009.02808",
                "2003.04425",
                "2104.09309",
                "1111.7103",
                "2010.15105",
            ],
        )
        reports_root.mkdir(parents=True, exist_ok=True)
        outputs = {
            "market-design-delayed-parity-repair": (
                reports_root / "lane-memo-market-design-delayed-parity-repair.md",
                build_market_design_parity_repair_memo(titles),
            ),
            "settlement-lag-resolution-friction-timing": (
                reports_root / "lane-memo-settlement-lag-resolution-friction-timing.md",
                build_settlement_lag_memo(titles),
            ),
            "rule-sensitive-toxic-flow-filters": (
                reports_root / "lane-memo-rule-sensitive-toxic-flow-filters.md",
                build_toxic_flow_memo(titles),
            ),
            "state-graph-repair-timing-monitor": (
                reports_root / "lane-memo-state-graph-repair-timing-monitor.md",
                build_state_graph_memo(titles),
            ),
        }
        output_path, content = outputs[args.memo_id]
        output_path.write_text(content, encoding="utf-8")
        log_run_event(
            connection,
            args.run_id,
            "lane_memos",
            "completed",
            {
                "memo_id": args.memo_id,
                "output_path": str(output_path),
            },
        )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
