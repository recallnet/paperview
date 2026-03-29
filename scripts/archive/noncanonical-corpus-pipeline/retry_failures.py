#!/usr/bin/env python3
"""Materialize and optionally retry canonical retryable downloader failures."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_RETRYABLE_TYPES = {
    "retryable_http_5xx",
    "retryable_http_error",
    "transient_or_unknown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--canonical-failures",
        type=Path,
        default=Path("data/arxiv-qfin/inventory/failures_canonical.jsonl"),
        help="Canonical latest-per-ID failures file.",
    )
    parser.add_argument(
        "--output-ids",
        type=Path,
        default=Path("data/arxiv-qfin/inventory/retryable_failure_ids.txt"),
        help="Path for retryable failure IDs.",
    )
    parser.add_argument(
        "--metadata-jsonl",
        type=Path,
        default=Path("data/arxiv-qfin/metadata.jsonl"),
        help="Metadata JSONL for downloader manifest enrichment.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/arxiv-qfin/pdfs"),
        help="PDF output directory.",
    )
    parser.add_argument(
        "--failure-types",
        nargs="*",
        default=sorted(DEFAULT_RETRYABLE_TYPES),
        help="Failure types considered retryable.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the downloader against the retryable IDs after writing the list.",
    )
    parser.add_argument("--workers", type=int, default=1, help="Retry worker count if --run is used.")
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.0,
        help="Delay between request starts if --run is used.",
    )
    parser.add_argument("--retries", type=int, default=2, help="Retries per request if --run is used.")
    parser.add_argument("--json", action="store_true", help="Emit summary JSON.")
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def write_ids(path: Path, ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{paper_id}\n" for paper_id in ids), encoding="utf-8")


def build_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "scripts/download_arxiv_pdfs.py",
        "--ids-file",
        str(args.output_ids),
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


def main() -> int:
    args = parse_args()
    rows = load_rows(args.canonical_failures)
    retryable_ids = [
        str(row["id"])
        for row in rows
        if str(row.get("failure_type", "")) in set(args.failure_types)
    ]
    write_ids(args.output_ids, retryable_ids)

    summary = {
        "canonical_failures_path": str(args.canonical_failures),
        "retryable_failure_types": sorted(set(args.failure_types)),
        "retryable_count": len(retryable_ids),
        "retryable_ids_path": str(args.output_ids),
        "ran_downloader": args.run,
    }

    if args.run and retryable_ids:
        command = build_command(args)
        subprocess.run(command, check=False)
        summary["command"] = command

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for key, value in summary.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
