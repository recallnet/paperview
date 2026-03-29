#!/usr/bin/env python3
"""Build an inventory of expected, downloaded, failed, and missing corpus items."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reconcile_failures import reconcile_failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/arxiv-qfin"),
        help="Corpus data directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/arxiv-qfin/inventory"),
        help="Directory for generated inventory artifacts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit summary JSON to stdout.",
    )
    return parser.parse_args()


def read_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_manifest_ids(path: Path) -> set[str]:
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


def write_lines(path: Path, items: list[str]) -> None:
    path.write_text("".join(f"{item}\n" for item in items), encoding="utf-8")


def build_inventory(data_dir: Path, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    failure_summary = reconcile_failures(data_dir / "pdfs" / "failures.jsonl", output_dir)

    expected_ids = read_ids(data_dir / "ids.txt")
    downloaded_ids = read_manifest_ids(data_dir / "pdfs" / "manifest.jsonl")
    failed_ids = set(read_ids(output_dir / "failed_ids_canonical.txt"))

    expected_set = set(expected_ids)
    missing_ids = sorted(expected_set - downloaded_ids)
    downloaded_ordered = [paper_id for paper_id in expected_ids if paper_id in downloaded_ids]
    failed_ordered = [paper_id for paper_id in expected_ids if paper_id in failed_ids]
    unexpected_downloaded = sorted(downloaded_ids - expected_set)
    unexpected_failed = sorted(failed_ids - expected_set)

    write_lines(output_dir / "expected_ids.txt", expected_ids)
    write_lines(output_dir / "downloaded_ids.txt", downloaded_ordered)
    write_lines(output_dir / "missing_ids.txt", missing_ids)
    write_lines(output_dir / "failed_ids.txt", failed_ordered)
    write_lines(output_dir / "unexpected_downloaded_ids.txt", unexpected_downloaded)
    write_lines(output_dir / "unexpected_failed_ids.txt", unexpected_failed)

    summary = {
        "expected_count": len(expected_ids),
        "downloaded_count": len(downloaded_ordered),
        "failed_count": len(failed_ordered),
        "missing_count": len(missing_ids),
        "unexpected_downloaded_count": len(unexpected_downloaded),
        "unexpected_failed_count": len(unexpected_failed),
        "output_dir": str(output_dir),
        "failure_summary": failure_summary,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    args = parse_args()
    summary = build_inventory(args.data_dir, args.output_dir)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for key, value in summary.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
