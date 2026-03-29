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


def render_unrealized(rows: list[dict]) -> list[str]:
    lines = ["## Unrealized Cross-Domain Ideas", ""]
    for index, row in enumerate(rows, start=1):
        echoes = row.get("rationale", {}).get("top_holdout_echoes", [])
        lines.extend(
            [
                f"### {index}. {row['title']}",
                "",
                f"- publication id: `{row['publication_item_id']}`",
                f"- classification: `{row['classification']}`",
                f"- confidence: `{row['confidence']}`",
                f"- result: {row['result_summary']}",
                f"- modern equivalent: {row['modern_equivalent']}",
                f"- first test: {row['first_step']}",
                f"- why unrealized: {row['why_stranded_or_unrealized']}",
                "- holdout echoes:",
            ]
        )
        for echo in echoes:
            lines.append(f"  - `{echo['paper_id']}` | {echo['title']} | echo `{echo['echo_score']}`")
        lines.append("")
    return lines


def render_stranded(rows: list[dict]) -> list[str]:
    lines = ["## Stranded Q-Fin Results", ""]
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"### {index}. {row['paper_id']}",
                "",
                f"- publication id: `{row['publication_item_id']}`",
                f"- confidence: `{row['confidence']}`",
                f"- priority tier: `{row['priority_tier']}`",
                f"- result: {row['result_summary']}",
                f"- why stranded: {row['why_stranded_or_unrealized']}",
                f"- instrument assumed: {row['instrument_assumed']}",
                f"- modern equivalent: {row['modern_equivalent']}",
                f"- first test: {row['first_test']}",
                f"- gap to close: {row['gap_to_close']}",
                "",
            ]
        )
    return lines


def render_transition(rows: list[dict]) -> list[str]:
    lines = ["## Transition-State Microstructure Seams", ""]
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"### {index}. {row['pattern_label']}",
                "",
                f"- publication id: `{row['publication_item_id']}`",
                f"- representative paper: `{row['paper_id']}`",
                f"- confidence: `{row['confidence']}`",
                f"- priority tier: `{row['priority_tier']}`",
                f"- result: {row['result_summary']}",
                f"- why unrealized: {row['why_stranded_or_unrealized']}",
                f"- instrument assumed: {row['instrument_assumed']}",
                f"- modern equivalent: {row['modern_equivalent']}",
                f"- first test: {row['first_test']}",
                f"- gap to close: {row['gap_to_close']}",
                "",
            ]
        )
    return lines


def render_throwaways(rows: list[dict]) -> list[str]:
    lines = ["## Near-Misses and Throwaways", ""]
    rejected = [row for row in rows if row["section"] == "rejected"]
    near_miss = [row for row in rows if row["section"] == "near_miss"]
    stranded_failures = [row for row in rows if row["section"] == "stranded_qfin_failure"]

    lines.extend(["### Rejected Interpretations", ""])
    if not rejected:
        lines.extend(["- none", ""])
    else:
        for row in rejected:
            label = row.get("shortlist_id") or "unresolved"
            lines.extend(
                [
                    f"- `{label}` | reason `{row['reason']}`",
                    f"  title: {row.get('title') or 'no matched packet'}",
                ]
            )
        lines.append("")

    lines.extend(["### Operator Near-Misses", ""])
    if not near_miss:
        lines.extend(["- none", ""])
    else:
        for row in near_miss:
            lines.extend(
                [
                    f"- `{row['paper_id']}` | `{row['operator_family']}` | score `{row['score']}`",
                    f"  title: {row['title']}",
                    f"  clue: {row['operator_label']}",
                ]
            )
        lines.append("")

    lines.extend(["### Stranded Q-Fin Failures", ""])
    if not stranded_failures:
        lines.extend(["- none", ""])
    else:
        for row in stranded_failures:
            lines.extend(
                [
                    f"- `{row['paper_id']}` | reason `{row['failure_reason']}`",
                    f"  title: {row['title']}",
                ]
            )
        lines.append("")
    return lines


def build_next_steps(unrealized_rows: list[dict], stranded_rows: list[dict], transition_rows: list[dict], findings_rows: list[dict]) -> list[str]:
    steps = []
    if unrealized_rows:
        row = unrealized_rows[0]
        steps.append(
            f"Validate `{row['publication_item_id']}` on recent order-book data: {row['first_step']}"
        )
    if transition_rows:
        row = transition_rows[0]
        steps.append(
            f"Treat `{row['pattern_label']}` as the top transition-state seam and test: {row['first_test']}"
        )
    if stranded_rows:
        row = stranded_rows[0]
        steps.append(
            f"Resurface `{row['paper_id']}` into a live execution memo: {row['first_test']}"
        )
    failure = next((row for row in findings_rows if row["section"] == "stranded_qfin_failure"), None)
    if failure:
        steps.append(
            f"Review stranded failure `{failure['paper_id']}` to decide whether it needs a new interpretation pass or explicit rejection."
        )
    return steps


def render_report(
    unrealized_rows: list[dict],
    unrealized_metrics: dict,
    stranded_rows: list[dict],
    stranded_metrics: dict,
    transition_rows: list[dict],
    transition_metrics: dict,
    findings_rows: list[dict],
    findings_metrics: dict,
) -> str:
    accepted_rows = [row for row in findings_rows if row["section"] == "accepted"]
    next_steps = build_next_steps(unrealized_rows, stranded_rows, transition_rows, findings_rows)
    lead_unrealized = unrealized_rows[0] if unrealized_rows else None
    lead_transition = transition_rows[0] if transition_rows else None
    lead_stranded = stranded_rows[0] if stranded_rows else None
    # @context decision -- S25 is the only root-level narrative surface. It must read from the four
    # already-published S24 artifacts instead of regenerating findings from upstream tables, or the
    # root report could silently drift away from the canonical publication outputs it is supposed to summarize.
    lines = [
        "# Research Output",
        "",
        "## Executive Summary",
        "",
        (
            f"The strongest cross-domain clue is `{lead_unrealized['publication_item_id']}`: "
            f"{lead_unrealized['result_summary']}"
            if lead_unrealized
            else "No unrealized cross-domain idea survived publication."
        ),
        (
            f"The stranded q-fin resurfacing pass produced concrete execution-style results, led by "
            f"`{lead_stranded['publication_item_id']}` and `{lead_stranded['modern_equivalent']}`."
            if lead_stranded
            else "No stranded q-fin result survived publication."
        ),
        (
            f"The clearest microstructure seam is `{lead_transition['pattern_label']}`: "
            f"{lead_transition['result_summary']}"
            if lead_transition
            else "No transition-state seam survived publication."
        ),
        (
            "The remaining throwaways still matter because they separate explicit rejections from "
            "high-value near misses and stranded failures that deserve another research pass."
            if accepted_rows or findings_rows
            else "No accepted or rejected findings were available for synthesis."
        ),
        "",
    ]
    lines.extend(render_unrealized(unrealized_rows))
    lines.extend(render_stranded(stranded_rows))
    lines.extend(render_transition(transition_rows))
    lines.extend(render_throwaways(findings_rows))
    lines.extend(["## What to Investigate Next", ""])
    for step in next_steps:
        lines.append(f"- {step}")
    lines.append("")
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

    report_text = render_report(
        unrealized_rows,
        unrealized_metrics,
        stranded_rows,
        stranded_metrics,
        transition_rows,
        transition_metrics,
        findings_rows,
        findings_metrics,
    )
    output_path.write_text(report_text, encoding="utf-8")

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    try:
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
