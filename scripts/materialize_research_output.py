#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_RUNS_ROOT = ROOT / "data" / "structural-analogy" / "runs"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize the consolidated research output report.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="research-output-20260328")
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--unrealized-run-id", default="unrealized-ideas-index-enhanced-20260328")
    parser.add_argument("--stranded-run-id", default="stranded-result-ledger-enhanced-20260328")
    parser.add_argument("--transition-run-id", default="transition-state-ledger-enhanced-20260328")
    parser.add_argument("--findings-run-id", default="findings-and-throwaways-enhanced-20260328")
    parser.add_argument("--shortlist-run-id", default="shortlist-materialization-20260328")
    parser.add_argument("--enhanced-interpretation-run-id", default="enhanced-interpretation-ingestion-20260328")
    parser.add_argument("--output-path", default=str(ROOT / "research_output.md"))
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_metrics(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"missing_required_artifact:{path}")
    return path


def report_paths(runs_root: Path, run_id: str, stem: str) -> tuple[Path, Path]:
    run_dir = runs_root / run_id
    return require_file(run_dir / f"{stem}.jsonl"), require_file(run_dir / f"{stem}_metrics.json")


def fetch_paper_metadata(connection: sqlite3.Connection, paper_ids: list[str]) -> dict[str, dict]:
    if not paper_ids:
        return {}
    placeholders = ",".join("?" for _ in paper_ids)
    rows = connection.execute(
        f"""
        SELECT paper_id, title, published_at
        FROM papers
        WHERE paper_id IN ({placeholders})
        """,
        tuple(paper_ids),
    ).fetchall()
    return {
        row["paper_id"]: {"title": row["title"], "published_at": row["published_at"]}
        for row in rows
    }


def find_row(rows: list[dict], key: str, value: str) -> dict | None:
    return next((row for row in rows if row.get(key) == value), None)


def find_near_miss(rows: list[dict], paper_id: str) -> dict | None:
    return next((row for row in rows if row["section"] == "near_miss" and row.get("paper_id") == paper_id), None)


def first_sentence(text: str) -> str:
    sentence = text.strip().split(". ")[0].strip()
    if sentence.endswith("."):
        return sentence
    return sentence + "."


def format_paper(paper_id: str, paper_metadata: dict[str, dict]) -> str:
    metadata = paper_metadata.get(paper_id, {})
    title = metadata.get("title")
    if title:
        return f"`{paper_id}` ({title})"
    return f"`{paper_id}`"


def build_paper_metadata(connection: sqlite3.Connection, findings_rows: list[dict]) -> dict[str, dict]:
    paper_ids = {
        "2106.00581",
        "2204.08581",
        "2101.03086",
        "1011.6402",
        "1902.10743",
        "2408.03181",
        "2406.04969",
    }
    for row in findings_rows:
        paper_id = row.get("paper_id")
        if paper_id:
            paper_ids.add(paper_id)
    return fetch_paper_metadata(connection, sorted(paper_ids))


def load_optional_metrics(path: Path) -> dict:
    if not path.exists():
        return {}
    return load_metrics(path)


def render_report(
    unrealized_rows: list[dict],
    unrealized_metrics: dict,
    stranded_rows: list[dict],
    stranded_metrics: dict,
    transition_rows: list[dict],
    transition_metrics: dict,
    findings_rows: list[dict],
    findings_metrics: dict,
    stranding_metrics: dict,
    shortlist_metrics: dict,
    enhanced_metrics: dict,
    paper_metadata: dict[str, dict],
) -> str:
    queue_refill = unrealized_rows[0] if unrealized_rows else None
    auction_queue = find_row(transition_rows, "pattern_label", "near auction handoff and queue value")
    auction_refill = find_row(transition_rows, "pattern_label", "near auction handoff and refill resiliency")
    maker_bridge = find_row(findings_rows, "shortlist_id", "bridge:maker_stress_inventory_retreat__queue_value_passive_quoting")
    auction_bridge = find_row(findings_rows, "shortlist_id", "bridge:auction_parimutuel_design__refill_lag_local_shock")
    stranded_2106 = find_row(stranded_rows, "paper_id", "2106.00581")
    stranded_2204 = find_row(stranded_rows, "paper_id", "2204.08581")
    queue_near_miss = find_near_miss(findings_rows, "2009.02808")
    auction_near_miss = find_near_miss(findings_rows, "cond-mat/0210475")
    maker_near_miss = find_near_miss(findings_rows, "1005.0182")
    defi_2205 = find_near_miss(findings_rows, "2205.14699")
    defi_2012 = find_near_miss(findings_rows, "2012.13230")
    parity_failure = find_row(findings_rows, "shortlist_id", "bridge:parity_propagation__queue_value_passive_quoting")

    # @context decision -- S25 is the only root-level narrative surface. It must stay human-facing
    # and artifact-grounded: read the four published S24 outputs plus supporting metrics, but do
    # not reprint publication ids or raw scoring dumps here, or the root memo collapses back into
    # pipeline telemetry instead of a research synthesis.
    lines = [
        "# Research Memo",
        "",
        "There may be executable edge in modeling passive quote value immediately after shocks, auctions, or maker withdrawals, especially when refill timing and queue dynamics diverge from naive displayed-depth assumptions.",
        "",
        "## Three Best Practical Leads",
        "",
        "### 1. Post-shock passive quoting via queue value plus refill lag",
        "",
        f"What it is: {queue_refill['result_summary']}" if queue_refill else "What it is: no surviving queue/refill lead.",
        "Why the system surfaced it: the queue/refill pairing is the only cross-domain idea that survived all the way to publication, and the same motif kept recurring across bridge, composition, and transition-state evidence instead of appearing as a one-off packet.",
        "What papers back it: "
        + ", ".join(
            [
                format_paper("1902.10743", paper_metadata),
                format_paper("2408.03181", paper_metadata),
                format_paper("2406.04969", paper_metadata),
                format_paper("2009.02808", paper_metadata),
                format_paper("1005.0182", paper_metadata),
            ]
        )
        + ".",
        f"First test: {queue_refill['first_step']}" if queue_refill else "First test: not available.",
        (
            f"Gap remaining: {queue_refill['why_stranded_or_unrealized']} The missing piece is a live rule that ties shock state, queue position, and refill timing into one quoting policy."
            if queue_refill
            else "Gap remaining: not available."
        ),
        "",
        "### 2. Auction-to-continuous-book transition seam",
        "",
        (
            f"What it is: {auction_bridge['result_summary']} {first_sentence(auction_queue['result_summary'])}"
            if auction_bridge and auction_queue
            else "What it is: no surviving auction seam."
        ),
        "Why the system surfaced it: the auction seam survived twice as a transition-state publication surface and separately as an accepted bridge lead, which means the handoff signal appears both in direct microstructure papers and in cross-domain recombination.",
        "What papers back it: "
        + ", ".join(
            [
                format_paper("2101.03086", paper_metadata),
                format_paper("1011.6402", paper_metadata),
                format_paper("cond-mat/0210475", paper_metadata),
            ]
        )
        + ".",
        (
            f"First test: {auction_queue['first_test']} Then test whether refill-speed asymmetry in the same post-uncrossing window adds incremental signal beyond queue priority alone."
            if auction_queue and auction_refill
            else "First test: not available."
        ),
        (
            f"Gap remaining: {auction_queue['gap_to_close']} The seam still needs a venue-specific definition of when auction logic hands off to continuous-book logic."
            if auction_queue
            else "Gap remaining: not available."
        ),
        "",
        "### 3. Maker-retreat regime switch for queue-based quoting",
        "",
        f"What it is: {maker_bridge['result_summary']}" if maker_bridge else "What it is: no surviving maker-retreat lead.",
        "Why the system surfaced it: the accepted bridge says displayed depth stops being reliable protection when makers back away, and the same queue-centric microstructure papers keep reappearing in the near-miss set, which points to a regime switch rather than a generic liquidity story.",
        (
            "What papers back it: "
            + ", ".join(
                [
                    format_paper("1005.0182", paper_metadata),
                    format_paper("2009.02808", paper_metadata),
                    format_paper("2101.03086", paper_metadata),
                ]
            )
            + "."
            if maker_near_miss
            else "What papers back it: the accepted maker-retreat bridge packet and the recurring queue-value near misses."
        ),
        f"First test: {maker_bridge['first_step']}" if maker_bridge else "First test: not available.",
        "Gap remaining: the lead still lacks a dedicated transition-state ledger entry, so the maker-withdrawal regime has an accepted interpretation but not yet a publication-grade representative seam or canonical representative paper.",
        "",
        "## The Stranded Results That Came Back",
        "",
        f"### 1. 2106.00581 — {paper_metadata.get('2106.00581', {}).get('title', 'title unavailable')} ({paper_metadata.get('2106.00581', {}).get('published_at', 'date unavailable')})",
        "",
        f"What it is in plain language: {stranded_2106['result_summary']}" if stranded_2106 else "What it is in plain language: not available.",
        "What changed since publication: modern depth feeds, cheaper intraday calibration, and queue-aware backtesting infrastructure make an impact-aware control law much easier to test now than it was in 2021.",
        f"Why it matters now: the old result reads like math-finance control theory, but today it can be treated as a concrete adaptive execution policy for fragmented electronic books. Modern equivalent: {stranded_2106['modern_equivalent']}" if stranded_2106 else "Why it matters now: not available.",
        f"First test: {stranded_2106['first_test']}" if stranded_2106 else "First test: not available.",
        f"Gap remaining: {stranded_2106['gap_to_close']}" if stranded_2106 else "Gap remaining: not available.",
        "",
        f"### 2. 2204.08581 — {paper_metadata.get('2204.08581', {}).get('title', 'title unavailable')} ({paper_metadata.get('2204.08581', {}).get('published_at', 'date unavailable')})",
        "",
        f"What it is in plain language: {stranded_2204['result_summary']}" if stranded_2204 else "What it is in plain language: not available.",
        "What changed since publication: surrogate-model tooling, GPU inference, and broader venue-fragmented execution data make fast policy search much more operationally plausible now than when the paper first appeared.",
        f"Why it matters now: the original result sat inside calibration language, but today it looks like a practical execution-research workflow for searching policy space quickly. Modern equivalent: {stranded_2204['modern_equivalent']}" if stranded_2204 else "Why it matters now: not available.",
        f"First test: {stranded_2204['first_test']}" if stranded_2204 else "First test: not available.",
        f"Gap remaining: {stranded_2204['gap_to_close']}" if stranded_2204 else "Gap remaining: not available.",
        "",
        "## The Transition-State Seam Map",
        "",
        (
            f"- queue x refill: evidenced. {queue_refill['result_summary']} This seam has the strongest support because it is already a published cross-domain idea and keeps reappearing in the near-miss set."
            if queue_refill
            else "- queue x refill: speculative."
        ),
        (
            f"- auction x refill: evidenced. {auction_refill['result_summary']} The seam is grounded by {format_paper('1011.6402', paper_metadata)} and the accepted auction/refill bridge."
            if auction_refill
            else "- auction x refill: speculative."
        ),
        (
            f"- auction x queue: evidenced. {auction_queue['result_summary']} The seam is grounded by {format_paper('2101.03086', paper_metadata)} and reinforced by the older auction microstructure backdrop in {format_paper('cond-mat/0210475', paper_metadata)}."
            if auction_queue
            else "- auction x queue: speculative."
        ),
        (
            f"- maker-stress x queue: provisional evidence. {maker_bridge['result_summary']} It has an accepted interpretation but not yet a dedicated ledger entry."
            if maker_bridge
            else "- maker-stress x queue: speculative."
        ),
        (
            f"- parity x refill: speculative. The seam still shows up in transition and bridge evidence, but the current run preserves it only as a rejection (`{parity_failure['reason']}`) plus the recurring near miss around {format_paper('1011.6402', paper_metadata)}."
            if parity_failure
            else "- parity x refill: speculative."
        ),
        "",
        "## The Conversion Funnel",
        "",
        "The system is strong at discovery and weak at synthesis.",
        "",
        (
            f"The search started with {stranding_metrics.get('scored_papers', 0):,} scored discovery papers, narrowed to {shortlist_metrics.get('shortlist_count', 0)} shortlist items, then to {enhanced_metrics.get('accepted_count', 0)} accepted interpretations, and finally to {unrealized_metrics.get('entry_count', 0)} published unrealized cross-domain idea, {stranded_metrics.get('entry_count', 0)} stranded q-fin results, and {transition_metrics.get('entry_count', 0)} transition-state entries."
        ),
        "What this means: discovery is working. The system is repeatedly finding the same microstructure motif across bridge, composition, transition, and stranded-q-fin paths. What is still weak is synthesis and ledger translation: too many good packets stop at interpretation or remain one step away from a publishable test memo.",
        "",
        "## What To Do Next",
        "",
        "Operationalize the queue x refill seam first. Use full-depth order-book data with event markers for volatility shocks, auction uncrossings, fill outcomes, queue position, refill timing, and maker-withdrawal proxies.",
        "The first test should be an event study plus simulated passive quoting policy: compare a shock-conditioned queue/refill model against naive spread-based passive posting after shocks and immediately after auction uncrossings.",
        "Success means the seam survives realistic fees and adverse-selection controls: the queue/refill-conditioned policy should improve fill-quality-adjusted expectancy, not just fill rate, across more than one venue or instrument.",
        "The second test should layer maker withdrawal on top of the same framework. If queue value degrades materially when makers retreat, that turns the current accepted maker bridge into a concrete regime switch rather than a narrative add-on.",
        "",
        "## The Near-Misses That Matter",
        "",
        (
            f"- {format_paper('2009.02808', paper_metadata)} is worth a second look because it keeps surfacing as the top queue/refill near miss and may supply the state variables for shock-conditioned passive quoting."
            if queue_near_miss
            else "- `2009.02808` is worth a second look because it keeps surfacing as the top queue/refill near miss."
        ),
        (
            f"- {format_paper('cond-mat/0210475', paper_metadata)} is worth a second look because it is the cleanest older foundation for the auction-to-book transition seam and keeps reappearing around auction/refill evidence."
            if auction_near_miss
            else "- `cond-mat/0210475` is worth a second look because it is a recurrent auction seam near miss."
        ),
        (
            f"- {format_paper('1005.0182', paper_metadata)} is worth a second look because it gives a maker-behavior and queue-dynamics lens on why displayed depth may lose protective value under stress."
            if maker_near_miss
            else "- `1005.0182` is worth a second look because it is a recurrent maker/queue near miss."
        ),
        (
            f"- {format_paper('2205.14699', paper_metadata)} is an interesting cross-domain signal because DeFi settlement and liquidation risk may rhyme with fragmented execution stress even though the venue structure is different."
            if defi_2205
            else "- `2205.14699` is an interesting cross-domain signal because it keeps surfacing in the contrast set."
        ),
        (
            f"- {format_paper('2012.13230', paper_metadata)} is an interesting cross-domain signal because pool depletion and refill mechanics may transfer into how the system thinks about liquidity recovery after stress."
            if defi_2012
            else "- `2012.13230` is an interesting cross-domain signal because it keeps surfacing in the contrast set."
        ),
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def main():
    args = parse_args()
    runs_root = Path(args.runs_root).resolve()
    output_path = Path(args.output_path).resolve()

    unrealized_jsonl, unrealized_metrics_path = report_paths(runs_root, args.unrealized_run_id, "unrealized_ideas_index")
    stranded_jsonl, stranded_metrics_path = report_paths(runs_root, args.stranded_run_id, "stranded_result_ledger")
    transition_jsonl, transition_metrics_path = report_paths(runs_root, args.transition_run_id, "transition_state_ledger")
    findings_jsonl, findings_metrics_path = report_paths(runs_root, args.findings_run_id, "findings_and_throwaways")

    unrealized_rows = load_jsonl(unrealized_jsonl)
    stranded_rows = load_jsonl(stranded_jsonl)
    transition_rows = load_jsonl(transition_jsonl)
    findings_rows = load_jsonl(findings_jsonl)
    unrealized_metrics = load_metrics(unrealized_metrics_path)
    stranded_metrics = load_metrics(stranded_metrics_path)
    transition_metrics = load_metrics(transition_metrics_path)
    findings_metrics = load_metrics(findings_metrics_path)
    stranding_metrics = load_optional_metrics(
        runs_root / "stranding-score-materialization-20260328" / "stranding_score_metrics.json"
    )
    shortlist_metrics = load_metrics(
        require_file(runs_root / args.shortlist_run_id / "shortlist_metrics.json")
    )
    enhanced_metrics = load_metrics(
        require_file(
            runs_root
            / args.enhanced_interpretation_run_id
            / "enhanced_interpretation_ingestion_metrics.json"
        )
    )

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        report_text = render_report(
            unrealized_rows,
            unrealized_metrics,
            stranded_rows,
            stranded_metrics,
            transition_rows,
            transition_metrics,
            findings_rows,
            findings_metrics,
            stranding_metrics,
            shortlist_metrics,
            enhanced_metrics,
            build_paper_metadata(connection, findings_rows),
        )
        output_path.write_text(report_text, encoding="utf-8")

        log_run_event(
            connection,
            args.run_id,
            "research_output",
            "completed",
            {
                "unrealized_run_id": args.unrealized_run_id,
                "stranded_run_id": args.stranded_run_id,
                "transition_run_id": args.transition_run_id,
                "findings_run_id": args.findings_run_id,
                "output_path": str(output_path),
            },
        )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
