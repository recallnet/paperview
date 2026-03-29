#!/usr/bin/env python3
"""Report local corpus readiness and download progress."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from corpus_inventory import build_inventory


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
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    parser.add_argument(
        "--refresh-inventory",
        action="store_true",
        help="Refresh inventory artifacts before reporting status.",
    )
    return parser.parse_args()


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def read_jsonl_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    result: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            paper_id = row.get("id")
            if paper_id:
                result.add(paper_id)
    return result


def read_tail(path: Path, lines: int) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()[-lines:]


def pid_status(pid_file: Path) -> dict[str, object]:
    status: dict[str, object] = {
        "pid": None,
        "running": False,
    }
    if not pid_file.exists():
        return status
    raw = pid_file.read_text(encoding="utf-8").strip()
    if not raw:
        return status
    pid = int(raw)
    status["pid"] = pid
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        status["running"] = False
    except PermissionError:
        status["running"] = True
    else:
        status["running"] = True
    return status


def file_age_seconds(path: Path) -> float | None:
    if not path.exists():
        return None
    return time.time() - path.stat().st_mtime


def should_refresh_inventory(data_dir: Path, explicit_refresh: bool) -> bool:
    if explicit_refresh:
        return True
    inventory_summary = data_dir / "inventory" / "summary.json"
    manifest_path = data_dir / "pdfs" / "manifest.jsonl"
    failures_path = data_dir / "pdfs" / "failures.jsonl"
    if not inventory_summary.exists():
        return True
    inventory_mtime = inventory_summary.stat().st_mtime
    manifest_mtime = manifest_path.stat().st_mtime if manifest_path.exists() else 0.0
    failures_mtime = failures_path.stat().st_mtime if failures_path.exists() else 0.0
    return max(manifest_mtime, failures_mtime) > inventory_mtime


def build_status(args: argparse.Namespace) -> dict[str, object]:
    ids_path = args.data_dir / "ids.txt"
    manifest_path = args.data_dir / "pdfs" / "manifest.jsonl"
    failures_path = args.data_dir / "pdfs" / "failures.jsonl"
    metadata_path = args.data_dir / "metadata.jsonl"
    inventory_summary_path = args.data_dir / "inventory" / "summary.json"

    if should_refresh_inventory(args.data_dir, args.refresh_inventory):
        build_inventory(args.data_dir, args.data_dir / "inventory")

    expected = count_lines(ids_path)
    metadata = count_lines(metadata_path)
    downloaded = len(read_jsonl_ids(manifest_path))
    failures = len(read_jsonl_ids(failures_path))
    remaining = max(expected - downloaded, 0)
    percent_complete = (downloaded / expected * 100.0) if expected else 0.0

    status = {
        "expected_papers": expected,
        "metadata_records": metadata,
        "downloaded_pdfs": downloaded,
        "failed_downloads": failures,
        "remaining_pdfs": remaining,
        "percent_complete": round(percent_complete, 4),
        "log_file": str(args.log_file),
        "log_age_seconds": file_age_seconds(args.log_file),
        "recent_log_lines": read_tail(args.log_file, args.tail_lines),
        "downloader": pid_status(args.pid_file),
    }
    if inventory_summary_path.exists():
        status["inventory_summary"] = json.loads(inventory_summary_path.read_text(encoding="utf-8"))
    return status


def render_text(status: dict[str, object]) -> str:
    lines = [
        "Corpus Status",
        f"expected_papers: {status['expected_papers']}",
        f"metadata_records: {status['metadata_records']}",
        f"downloaded_pdfs: {status['downloaded_pdfs']}",
        f"failed_downloads: {status['failed_downloads']}",
        f"remaining_pdfs: {status['remaining_pdfs']}",
        f"percent_complete: {status['percent_complete']:.4f}%",
        f"downloader_pid: {status['downloader']['pid']}",
        f"downloader_running: {status['downloader']['running']}",
        f"log_age_seconds: {status['log_age_seconds']}",
    ]
    inventory = status.get("inventory_summary")
    if inventory:
        lines.extend(
            [
                f"inventory_missing_count: {inventory['missing_count']}",
                f"inventory_output_dir: {inventory['output_dir']}",
            ]
        )
    lines.append("recent_log_lines:")
    for line in status["recent_log_lines"]:
        lines.append(f"  {line}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    status = build_status(args)
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print(render_text(status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
