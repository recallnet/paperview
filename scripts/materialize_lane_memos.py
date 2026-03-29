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
        choices=["market-design-delayed-parity-repair"],
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
    ensure_market_design_state(diamond_board_text, findings_text, research_output_text)

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        titles = fetch_titles(connection, ["1609.04620", "1811.08038", "1709.08238", "2011.04367", "2004.12011"])
        reports_root.mkdir(parents=True, exist_ok=True)
        outputs = {
            "market-design-delayed-parity-repair": (
                reports_root / "lane-memo-market-design-delayed-parity-repair.md",
                build_market_design_parity_repair_memo(titles),
            )
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
