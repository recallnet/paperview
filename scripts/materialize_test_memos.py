#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_RUNS_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_REPORTS_ROOT = ROOT / "reports"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize executable test memos from the current research state.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="test-memos-20260328")
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--reports-root", default=str(DEFAULT_REPORTS_ROOT))
    parser.add_argument("--research-output-path", default=str(ROOT / "research_output.md"))
    parser.add_argument("--unrealized-run-id", default="unrealized-ideas-index-enhanced-20260328")
    parser.add_argument("--stranded-run-id", default="stranded-result-ledger-enhanced-20260328")
    parser.add_argument("--transition-run-id", default="transition-state-ledger-enhanced-20260328")
    parser.add_argument("--findings-run-id", default="findings-and-throwaways-enhanced-20260328")
    return parser.parse_args()


def require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"missing_required_artifact:{path}")
    return path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def fetch_titles(connection: sqlite3.Connection, paper_ids: list[str]) -> dict[str, str]:
    if not paper_ids:
        return {}
    placeholders = ",".join("?" for _ in paper_ids)
    rows = connection.execute(
        f"SELECT paper_id, title FROM papers WHERE paper_id IN ({placeholders})",
        tuple(paper_ids),
    ).fetchall()
    return {row["paper_id"]: row["title"] for row in rows}


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def find_row(rows: list[dict], key: str, value: str) -> dict | None:
    return next((row for row in rows if row.get(key) == value), None)


def format_reference(paper_id: str, titles: dict[str, str]) -> str:
    title = titles.get(paper_id)
    if title:
        return f"`{paper_id}` ({title})"
    return f"`{paper_id}`"


def ensure_current_state(research_output_path: Path, unrealized_rows: list[dict], transition_rows: list[dict], findings_rows: list[dict]) -> None:
    report_text = require_file(research_output_path).read_text(encoding="utf-8")
    if "There may be executable edge in modeling passive quote value" not in report_text:
        raise ValueError("research_output_missing_core_thesis")
    if not unrealized_rows:
        raise ValueError("missing_unrealized_rows")
    if not find_row(transition_rows, "pattern_label", "near auction handoff and queue value"):
        raise ValueError("missing_transition_queue_seam")
    if not find_row(findings_rows, "shortlist_id", "bridge:maker_stress_inventory_retreat__queue_value_passive_quoting"):
        raise ValueError("missing_maker_retreat_bridge")


def build_queue_refill_memo(titles: dict[str, str]) -> str:
    return "\n".join(
        [
            "# Post-Shock Passive Quoting: Queue Value x Refill Lag",
            "",
            "## Thesis",
            "",
            "There may be positive passive-quoting edge immediately after local shocks when queue position is still favorable and displayed depth refills quickly, while the same setup becomes adverse when refill lags and maker participation falls away.",
            "",
            "## Supporting Papers",
            "",
            f"- {format_reference('1902.10743', titles)}",
            f"- {format_reference('2408.03181', titles)}",
            f"- {format_reference('2406.04969', titles)}",
            f"- {format_reference('2009.02808', titles)}",
            f"- {format_reference('1005.0182', titles)}",
            "",
            "## Event Definitions",
            "",
            "- Shock: either an absolute mid-price move greater than 3 rolling short-horizon sigma inside 5 seconds, or best-level displayed depth depletion greater than 40% on one side of the book inside 2 seconds.",
            "- Refill: displayed depth at the best level and first two price levels recovering to at least 80% of the pre-shock depth baseline.",
            "- Refill lag: elapsed time from the shock timestamp to 80% depth recovery.",
            "",
            "## Features",
            "",
            "- Queue position at shock time, measured in shares or contracts ahead at the posting level.",
            "- Refill lag, measured as time to 80% depth recovery.",
            "- Pre-shock displayed depth at the best level and first two levels.",
            "- Post-shock spread in ticks and notional terms.",
            "- Maker count change around the shock window, using unique visible liquidity providers when available or proxy quote-source counts when not.",
            "",
            "## Baseline Policy",
            "",
            "Naive spread-based passive posting: post passively at the best bid or ask whenever the spread is above a fixed threshold, with no conditioning on queue position, refill state, or maker withdrawal.",
            "",
            "## Seam-Aware Policy",
            "",
            "Post passively only when queue position is inside a favorable bound and refill is already recovering. A concrete first pass is: only join or keep a passive quote when queue position is in the front 20% of visible queue and refill lag is below 2 seconds, while suppressing passive posting when refill lag exceeds 5 seconds or maker count drops sharply.",
            "",
            "## Success Metric",
            "",
            "Use fill-quality-adjusted expectancy, not fill rate. Compare baseline versus seam-aware policy on realized markout per fill net of fees, and explicitly decompose expectancy into fill probability, adverse selection after fill, and missed-trade opportunity cost.",
            "",
            "## Data Requirements",
            "",
            "- Full-depth limit-order-book snapshots or event-level reconstruction.",
            "- Event markers for volatility shocks and depth depletion windows.",
            "- At least one liquid equity or futures instrument.",
            "- Minimum three months of data to cover multiple volatility regimes.",
            "",
            "## Known Risks",
            "",
            "- Refill lag measurement is venue-specific and can be distorted by hidden liquidity or iceberg replenishment.",
            "- Queue-position advantage may not survive hidden liquidity, midpoint interaction, or internalization.",
            "- A shock definition that is too broad will blur together informed price moves and purely mechanical dislocations.",
            "",
        ]
    ) + "\n"


def build_auction_handoff_memo(titles: dict[str, str]) -> str:
    return "\n".join(
        [
            "# Auction-to-Continuous Transition Seam",
            "",
            "## Thesis",
            "",
            "Queue value and refill asymmetry immediately after auction uncrossing may carry more execution signal than the same variables later in the continuous session, creating a distinct post-uncrossing quoting regime.",
            "",
            "## Supporting Papers",
            "",
            f"- {format_reference('2101.03086', titles)}",
            f"- {format_reference('1011.6402', titles)}",
            f"- {format_reference('cond-mat/0210475', titles)}",
            "",
            "## Venue-Specific State Boundary",
            "",
            "- First concrete venue: NYSE opening auction.",
            "- Auction mode ends at the official uncrossing timestamp disseminated by the auction feed.",
            "- Continuous-book mode begins with the first regular-way continuous-book event after the uncrossing print.",
            "- Secondary venue candidate for replication: Euronext closing auction, using the same boundary logic around the official uncrossing event and the first post-auction continuous-book update.",
            "",
            "## Uncrossing Window Definition",
            "",
            "- Primary definition: the first 10 seconds after the auction price is set.",
            "- Secondary definition for robustness: the first 200 book events after uncrossing.",
            "",
            "## Test 1",
            "",
            "Does queue priority gained immediately after uncrossing predict short-horizon adverse selection better than queue priority gained 5 minutes later? Measure queue rank at entry, subsequent fill probability, and 1-minute and 5-minute markouts, then compare the post-uncrossing window against a matched later-session control window.",
            "",
            "## Test 2",
            "",
            "Does refill-speed asymmetry in the post-uncrossing window add signal beyond queue priority alone? Estimate depth recovery speed separately on bid and ask, then test whether a model with both queue rank and refill asymmetry explains fill-quality outcomes better than queue rank by itself.",
            "",
            "## Data Requirements",
            "",
            "- Auction event feeds with official uncrossing timestamps and auction prints.",
            "- Post-auction limit-order-book reconstruction at message or high-resolution snapshot level.",
            "- Sufficient history to capture many opening or closing auctions, ideally at least three months on a liquid venue.",
            "",
            "## Known Risks",
            "",
            "- Auction mechanics differ materially across venues, so the state boundary may not transfer cleanly.",
            "- Sample sizes for uncrossing events may be small once filters for liquid, clean events are applied.",
            "- Queue priority after uncrossing may proxy for informational urgency rather than a durable microstructure edge.",
            "",
        ]
    ) + "\n"


def build_maker_retreat_memo(titles: dict[str, str]) -> str:
    return "\n".join(
        [
            "# Maker-Retreat Regime Switch for Queue-Based Quoting",
            "",
            "## Thesis",
            "",
            "Queue-position value may degrade materially, or even flip sign, when makers withdraw under stress, so passive quoting logic should treat maker-retreat windows as a separate regime rather than as ordinary queue competition.",
            "",
            "## Supporting Papers",
            "",
            f"- {format_reference('1005.0182', titles)}",
            f"- {format_reference('2009.02808', titles)}",
            f"- {format_reference('2101.03086', titles)}",
            "",
            "## Maker Withdrawal Proxies",
            "",
            "- Number of unique maker IDs or quote-source identifiers at the best levels, when available.",
            "- Depth change rate at the best level and first two levels.",
            "- Cancellation-rate spike over a short rolling window relative to normal conditions.",
            "- Inventory-imbalance indicators or one-sided quote retreat proxies inferred from persistent depth withdrawal on one side.",
            "",
            "## Regime Classifier",
            "",
            "Start with a binary classifier: `normal` versus `maker_retreat`. Label a window as `maker_retreat` when at least two withdrawal proxies breach their rolling 90th percentile thresholds, then extend to a three-state classifier (`normal`, `stressed`, `maker_retreat`) if the binary split is too coarse.",
            "",
            "## Test",
            "",
            "Measure queue-position value as fill quality minus subsequent adverse selection. Then ask whether this value degrades materially, or turns negative, during maker-retreat regimes relative to normal regimes. The key comparison is not raw fill count but whether front-of-queue placement still buys good fills once makers start pulling away.",
            "",
            "## Baseline",
            "",
            "Unconditional queue-position value across all regimes, using the same fill-quality and markout calculations but without any regime conditioning.",
            "",
            "## Success Metric",
            "",
            "A regime-conditional fill-quality difference that survives transaction-cost and adverse-selection controls. Success means queue-position value is measurably worse in maker-retreat windows than in normal windows, and the difference remains after controlling for spread, volatility, and instrument fixed effects.",
            "",
            "## Data Requirements",
            "",
            "- Order-level attribution data or credible maker proxy indicators.",
            "- The same liquid equity or futures instruments used in the queue/refill memo so results can be compared directly.",
            "- Enough depth and event history to estimate cancellation spikes, quote retreat, and regime transitions reliably.",
            "",
            "## Known Risks",
            "",
            "- Maker identity is often not directly observable, so proxy quality will vary by venue.",
            "- Queue degradation may be confounded with volatility shocks unless the regime classifier controls for concurrent price moves.",
            "- Some venues may show little visible maker dispersion, which weakens maker-count features.",
            "",
        ]
    ) + "\n"


def main():
    args = parse_args()
    runs_root = Path(args.runs_root).resolve()
    reports_root = Path(args.reports_root).resolve()
    research_output_path = Path(args.research_output_path).resolve()

    unrealized_rows = load_jsonl(
        require_file(runs_root / args.unrealized_run_id / "unrealized_ideas_index.jsonl")
    )
    transition_rows = load_jsonl(
        require_file(runs_root / args.transition_run_id / "transition_state_ledger.jsonl")
    )
    findings_rows = load_jsonl(
        require_file(runs_root / args.findings_run_id / "findings_and_throwaways.jsonl")
    )
    ensure_current_state(research_output_path, unrealized_rows, transition_rows, findings_rows)

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        titles = fetch_titles(
            connection,
            [
                "1902.10743",
                "2408.03181",
                "2406.04969",
                "2101.03086",
                "1011.6402",
                "cond-mat/0210475",
                "1005.0182",
                "2009.02808",
            ],
        )
        reports_root.mkdir(parents=True, exist_ok=True)
        outputs = {
            "test-memo-queue-refill.md": build_queue_refill_memo(titles),
            "test-memo-auction-handoff.md": build_auction_handoff_memo(titles),
            "test-memo-maker-retreat.md": build_maker_retreat_memo(titles),
        }
        for filename, content in outputs.items():
            (reports_root / filename).write_text(content, encoding="utf-8")

        # @context decision -- S26 memo generation is intentionally deterministic and anchored to
        # the current published research state. If this script starts inventing new leads instead
        # of codifying the already-published seams, the memos stop being executable follow-on work.
        log_run_event(
            connection,
            args.run_id,
            "test_memos",
            "completed",
            {
                "reports_root": str(reports_root),
                "files": sorted(outputs.keys()),
                "research_output_path": str(research_output_path),
            },
        )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
