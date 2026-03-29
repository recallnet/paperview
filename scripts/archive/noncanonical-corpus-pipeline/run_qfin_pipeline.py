#!/usr/bin/env python3
"""Run the q-fin downloader plus post-pass retry reconciliation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
HELPER_DIR = PIPELINE_DIR.parent / "noncanonical-corpus-helpers"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/arxiv-qfin"),
        help="Corpus data directory for inventory and retry artifacts.",
    )
    parser.add_argument(
        "--ids-file",
        type=Path,
        default=Path("data/arxiv-qfin/ids.txt"),
        help="Text file containing one arXiv ID per line.",
    )
    parser.add_argument(
        "--metadata-jsonl",
        type=Path,
        default=Path("data/arxiv-qfin/metadata.jsonl"),
        help="Metadata JSONL for manifest enrichment.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/arxiv-qfin/pdfs"),
        help="PDF output directory.",
    )
    parser.add_argument("--workers", type=int, default=3, help="Concurrent download workers.")
    parser.add_argument("--delay-seconds", type=float, default=1.0, help="Minimum delay between request starts.")
    parser.add_argument("--retries", type=int, default=4, help="Retries per request in the main pass.")
    parser.add_argument(
        "--retry-passes",
        type=int,
        default=1,
        help="Number of post-pass retryable failure retry rounds.",
    )
    parser.add_argument(
        "--retry-workers",
        type=int,
        default=1,
        help="Worker count for retryable failure retry rounds.",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=1.0,
        help="Delay between request starts in retry rounds.",
    )
    parser.add_argument(
        "--retry-retries",
        type=int,
        default=2,
        help="Retries per request in retry rounds.",
    )
    return parser.parse_args()


def run_command(command: list[str]) -> int:
    result = subprocess.run(command, check=False)
    return result.returncode


def main_download_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "scripts/download_arxiv_pdfs.py",
        "--ids-file",
        str(args.ids_file),
        "--metadata-jsonl",
        str(args.metadata_jsonl),
        "--output-dir",
        str(args.output_dir),
        "--workers",
        str(args.workers),
        "--delay-seconds",
        str(args.delay_seconds),
        "--retries",
        str(args.retries),
        "--skip-existing",
    ]


def inventory_command() -> list[str]:
    return []


def retry_command(args: argparse.Namespace, run: bool) -> list[str]:
    command = [
        sys.executable,
        str(PIPELINE_DIR / "retry_failures.py"),
        "--canonical-failures",
        str(args.data_dir / "inventory" / "failures_canonical.jsonl"),
        "--output-ids",
        str(args.data_dir / "inventory" / "retryable_failure_ids.txt"),
        "--metadata-jsonl",
        str(args.metadata_jsonl),
        "--output-dir",
        str(args.output_dir),
        "--workers",
        str(args.retry_workers),
        "--delay-seconds",
        str(args.retry_delay_seconds),
        "--retries",
        str(args.retry_retries),
    ]
    if run:
        command.append("--run")
    return command


def retry_queue_count(data_dir: Path) -> int:
    path = data_dir / "inventory" / "retryable_failure_ids.txt"
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def inventory_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(HELPER_DIR / "corpus_inventory.py"),
        "--data-dir",
        str(args.data_dir),
        "--output-dir",
        str(args.data_dir / "inventory"),
    ]


def main() -> int:
    args = parse_args()

    run_command(main_download_command(args))
    run_command(inventory_command(args))

    for _ in range(args.retry_passes):
        run_command(retry_command(args, run=False))
        if retry_queue_count(args.data_dir) == 0:
            break
        run_command(retry_command(args, run=True))
        run_command(inventory_command(args))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
