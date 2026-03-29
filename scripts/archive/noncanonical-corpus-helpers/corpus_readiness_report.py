#!/usr/bin/env python3
"""Build a Phase 0 corpus readiness report from local artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from corpus_status import build_status, parse_args as parse_status_args


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/arxiv-qfin"),
        help="Corpus data directory.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("logs/qfin_download.log"),
        help="Downloader log file.",
    )
    parser.add_argument(
        "--pid-file",
        type=Path,
        default=Path("logs/qfin_download.pid"),
        help="Downloader PID file.",
    )
    parser.add_argument(
        "--tail-lines",
        type=int,
        default=10,
        help="Number of log lines to include.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/corpus-readiness"),
        help="Directory for readiness report artifacts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON to stdout instead of Markdown.",
    )
    return parser.parse_args()


def classify_readiness(status: dict[str, object]) -> tuple[str, list[str]]:
    notes: list[str] = []
    level = "operational"

    remaining = int(status["remaining_pdfs"])
    failed = int(status["failed_downloads"])
    running = bool(status["downloader"]["running"])

    if not running and remaining > 0:
        level = "attention"
        notes.append("Downloader is not running.")

    inventory = status.get("inventory_summary") or {}
    unknown_failure_count = int((inventory.get("failure_summary") or {}).get("unknown_failure_count", 0))
    if unknown_failure_count > 0:
        level = "attention"
        notes.append(f"{unknown_failure_count} failures remain unclassified.")

    if failed > 0:
        notes.append(f"{failed} canonical failed IDs currently exist.")

    if int(status["downloaded_pdfs"]) == 0:
        level = "attention"
        notes.append("No PDFs have been downloaded yet.")

    if remaining == 0 and running:
        notes.append("Downloader is still running even though no remaining IDs are reported.")

    if remaining == 0 and unknown_failure_count == 0 and failed == 0:
        level = "complete"
        notes.append("Corpus pull is complete with no canonical failures.")

    if remaining > 0 and running:
        notes.append("Corpus pull is still in progress.")

    if not notes:
        notes.append("Corpus pull is active and operational artifacts are coherent.")

    return level, notes


def markdown_report(status: dict[str, object], readiness_level: str, notes: list[str]) -> str:
    inventory = status.get("inventory_summary") or {}
    failure_summary = inventory.get("failure_summary") or {}
    lines = [
        "# Corpus Readiness Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Readiness: `{readiness_level}`",
        "",
        "## Summary",
        "",
        f"- Expected papers: `{status['expected_papers']}`",
        f"- Downloaded PDFs: `{status['downloaded_pdfs']}`",
        f"- Canonical failed IDs: `{status['failed_downloads']}`",
        f"- Remaining IDs: `{status['remaining_pdfs']}`",
        f"- Downloader running: `{status['downloader']['running']}`",
        "",
        "## Notes",
        "",
    ]
    for note in notes:
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Failure Summary",
            "",
            f"- Failure types: `{json.dumps(failure_summary.get('failure_types', {}), sort_keys=True)}`",
            f"- Permanent failures: `{failure_summary.get('permanent_failure_count', 0)}`",
            f"- Unknown failures: `{failure_summary.get('unknown_failure_count', 0)}`",
            "",
            "## Recent Log Lines",
            "",
        ]
    )
    for line in status["recent_log_lines"]:
        lines.append(f"- `{line}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    status_args = parse_status_args()
    status_args.data_dir = args.data_dir
    status_args.log_file = args.log_file
    status_args.pid_file = args.pid_file
    status_args.tail_lines = args.tail_lines
    status_args.json = False
    status_args.refresh_inventory = True

    status = build_status(status_args)
    readiness_level, notes = classify_readiness(status)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "readiness_level": readiness_level,
        "notes": notes,
        "status": status,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "latest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.output_dir / "latest.md").write_text(
        markdown_report(status, readiness_level, notes), encoding="utf-8"
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(markdown_report(status, readiness_level, notes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
