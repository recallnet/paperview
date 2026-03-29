#!/usr/bin/env python3
"""Normalize downloader failure artifacts into a canonical latest-per-ID view."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--failures-file",
        type=Path,
        default=Path("data/arxiv-qfin/pdfs/failures.jsonl"),
        help="Raw downloader failures log.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/arxiv-qfin/inventory"),
        help="Directory for reconciled failure artifacts.",
    )
    parser.add_argument(
        "--rewrite-raw",
        action="store_true",
        help="Rewrite the raw failures log to canonical latest-per-ID records.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit summary JSON.",
    )
    return parser.parse_args()


def load_failure_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def canonicalize(rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], int]:
    latest_by_id: dict[str, dict[str, object]] = {}
    duplicate_rows = 0
    for row in rows:
        paper_id = row.get("id")
        if not isinstance(paper_id, str) or not paper_id:
            continue
        if paper_id in latest_by_id:
            duplicate_rows += 1
        latest_by_id[paper_id] = row
    canonical_rows = sorted(latest_by_id.values(), key=lambda row: str(row["id"]))
    return canonical_rows, duplicate_rows


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_lines(path: Path, items: list[str]) -> None:
    path.write_text("".join(f"{item}\n" for item in items), encoding="utf-8")


def build_summary(rows: list[dict[str, object]], duplicate_rows: int, output_dir: Path) -> dict[str, object]:
    failure_types: dict[str, int] = {}
    permanent_ids: list[str] = []
    unknown_ids: list[str] = []
    for row in rows:
        failure_type = str(row.get("failure_type", "unknown"))
        failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        paper_id = str(row["id"])
        if failure_type == "permanent":
            permanent_ids.append(paper_id)
        if failure_type == "unknown":
            unknown_ids.append(paper_id)
    return {
        "canonical_failure_count": len(rows),
        "duplicate_rows_removed": duplicate_rows,
        "failure_types": failure_types,
        "permanent_failure_count": len(permanent_ids),
        "unknown_failure_count": len(unknown_ids),
        "output_dir": str(output_dir),
    }


def reconcile_failures(failures_file: Path, output_dir: Path, rewrite_raw: bool = False) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_failure_rows(failures_file)
    canonical_rows, duplicate_rows = canonicalize(rows)
    write_jsonl(output_dir / "failures_canonical.jsonl", canonical_rows)
    write_lines(
        output_dir / "failed_ids_canonical.txt",
        [str(row["id"]) for row in canonical_rows],
    )
    write_lines(
        output_dir / "failed_ids_permanent.txt",
        [str(row["id"]) for row in canonical_rows if row.get("failure_type") == "permanent"],
    )
    summary = build_summary(canonical_rows, duplicate_rows, output_dir)
    (output_dir / "failures_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if rewrite_raw:
        write_jsonl(failures_file, canonical_rows)
    return summary


def main() -> int:
    args = parse_args()
    summary = reconcile_failures(args.failures_file, args.output_dir, rewrite_raw=args.rewrite_raw)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for key, value in summary.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
