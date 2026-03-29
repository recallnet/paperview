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


def format_paper(paper_id: str, paper_metadata: dict[str, dict]) -> str:
    metadata = paper_metadata.get(paper_id, {})
    title = metadata.get("title")
    if title:
        return f"`{paper_id}` ({title})"
    return f"`{paper_id}`"


def build_paper_metadata(connection: sqlite3.Connection, findings_rows: list[dict], stranded_rows: list[dict], transition_rows: list[dict]) -> dict[str, dict]:
    paper_ids = set()
    for row in findings_rows:
        if row.get("paper_id"):
            paper_ids.add(row["paper_id"])
    for row in stranded_rows:
        if row.get("paper_id"):
            paper_ids.add(row["paper_id"])
    for row in transition_rows:
        if row.get("paper_id"):
            paper_ids.add(row["paper_id"])
    return fetch_paper_metadata(connection, sorted(paper_ids))


def load_optional_metrics(path: Path) -> dict:
    if not path.exists():
        return {}
    return load_metrics(path)


def humanize_family(value: str) -> str:
    return value.replace("_", " ").strip()


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
    accepted_rows = [row for row in findings_rows if row.get("section") == "accepted"]
    accepted_by_family: dict[str, list[dict]] = {}
    for row in accepted_rows:
        accepted_by_family.setdefault(row["operator_family"], []).append(row)
    for rows in accepted_by_family.values():
        rows.sort(key=lambda row: (row.get("shortlist_rank", 10**9), row.get("shortlist_id", "")))

    near_miss_rows = [row for row in findings_rows if row.get("section") == "near_miss"]
    near_miss_rows.sort(key=lambda row: (row.get("operator_family", ""), -(row.get("score", 0.0)), row.get("paper_id", "")))

    thesis = (
        "The broadened run suggests exploitable edge is not confined to mature electronic-book transition states: "
        "the strongest surviving ideas cluster where market design, settlement timing, participant pathology, "
        "state-graph inconsistency, and market maturation interact with execution microstructure."
    )

    # @context decision -- S25 is the only root-level narrative surface. It must stay human-facing
    # and artifact-grounded: read the published outputs and supporting metrics, but do not reprint
    # publication ids or raw scoring dumps here, or the root memo collapses back into telemetry.
    lines = [
        "# Research Memo",
        "",
        thesis,
        "",
        "## Broadest Surviving Leads",
        "",
    ]

    for idx, row in enumerate(unrealized_rows, start=1):
        lines.extend(
            [
                f"### {idx}. {row['title']}",
                "",
                f"Lane: {humanize_family(row.get('item_type', 'unknown'))}.",
                f"What it is: {row['result_summary']}",
                f"Why it survived: {row['why_stranded_or_unrealized']}",
                f"First test: {row['first_step']}",
                f"Modern equivalent: {row['modern_equivalent']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Lane Coverage",
            "",
            "The broadened discovery set now has surviving accepted interpretations in all five new early-market lanes, plus the existing stranded-q-fin and transition-state paths.",
            "",
        ]
    )
    for family in (
        "market_design",
        "settlement_resolution",
        "participant_pathologies",
        "state_graph",
        "lifecycle",
        "stranded_qfin",
        "transition_state",
    ):
        rows = accepted_by_family.get(family, [])
        if not rows:
            lines.append(f"- {humanize_family(family)}: no accepted item survived publication or ingestion.")
            continue
        lines.append(f"- {humanize_family(family)}: {rows[0]['result_summary']}")

    lines.extend(
        [
            "",
            "## The Stranded Results That Came Back",
            "",
        ]
    )
    for row in stranded_rows:
        title = paper_metadata.get(row["paper_id"], {}).get("title", "title unavailable")
        published_at = paper_metadata.get(row["paper_id"], {}).get("published_at", "date unavailable")
        lines.extend(
            [
                f"### {row['paper_id']} — {title} ({published_at})",
                "",
                f"What it is in plain language: {row['result_summary']}",
                f"Why it matters now: {row['why_stranded_or_unrealized']}",
                f"Modern equivalent: {row['modern_equivalent']}",
                f"First test: {row['first_test']}",
                f"Gap remaining: {row['gap_to_close']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Transition-State Seams Still Matter",
            "",
            "The broadened run no longer treats transition-state microstructure as the only center of gravity, but the venue-level auction and queue seams remain the clearest microstructure benchmark.",
            "",
        ]
    )
    for row in transition_rows:
        lines.append(f"- {row['pattern_label']}: {row['result_summary']} First test: {row['first_test']}")

    lines.extend(
        [
            "",
            "## The Conversion Funnel",
            "",
            (
                f"The search started with {stranding_metrics.get('scored_papers', 0):,} scored discovery papers, narrowed to "
                f"{shortlist_metrics.get('shortlist_count', 0)} shortlist items, then to "
                f"{enhanced_metrics.get('accepted_count', 0)} accepted broadened interpretations, and finally to "
                f"{unrealized_metrics.get('entry_count', 0)} unrealized cross-domain entries, "
                f"{stranded_metrics.get('entry_count', 0)} stranded q-fin results, and "
                f"{transition_metrics.get('entry_count', 0)} transition-state entries."
            ),
            "What this means: discovery is now broader than the original microstructure loop, but publication is still selective. The system can find multi-lane seams; the remaining bottleneck is converting those seams into dense interpretation evidence and durable publication rows.",
            "",
            "## What To Do Next",
            "",
            "Operationalize the broadened publication set in three tracks.",
            "1. Build lane-specific research programs for the surviving market-design, settlement-resolution, participant-pathology, state-graph, and lifecycle leads, using the unrealized index rows as the canonical queue of next experiments.",
            "2. Keep the stranded q-fin results on a separate execution track, because those papers are already close to deployable execution research rather than broad discovery hypotheses.",
            "3. Use the transition-state ledger as the venue-microstructure benchmark so the broader lanes can be compared against the older queue/refill seam instead of replacing it blindly.",
            "",
            "## Papers Worth a Second Look",
            "",
        ]
    )
    for row in near_miss_rows[:8]:
        paper_id = row.get("paper_id")
        label = row.get("operator_label", row.get("operator_family", "unknown"))
        if paper_id:
            lines.append(f"- {format_paper(paper_id, paper_metadata)} is worth another pass because it keeps appearing near the {label} seam.")
        else:
            title = row.get("title", "title unavailable")
            lines.append(f"- {title} is worth another pass because it keeps appearing near the {label} seam.")

    lines.extend(
        [
            "",
            "## Publication Summary",
            "",
            f"Accepted findings in the broadened run: {findings_metrics.get('accepted_count', 0)}.",
            f"Rejected findings recorded with reasons: {findings_metrics.get('rejected_count', 0)}.",
            f"Near-miss papers still worth inspection: {findings_metrics.get('near_miss_count', 0)}.",
            "",
        ]
    )
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
        paper_metadata = build_paper_metadata(connection, findings_rows, stranded_rows, transition_rows)
        report = render_report(
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
            paper_metadata,
        )
        output_path.write_text(report, encoding="utf-8")
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
