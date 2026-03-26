#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
import math
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "pilots"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a deterministic abstract-first pilot batch from the local SQLite store."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--source-corpus",
        default="arxiv-qfin",
        help="Corpus label to filter on. Use 'all' to allow every imported corpus.",
    )
    parser.add_argument(
        "--literature-families",
        default=None,
        help="Optional comma-separated literature families to include.",
    )
    parser.add_argument(
        "--exclude-evaluation-split",
        default="holdout",
        help="Evaluation split to exclude from pilot construction.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Number of papers to include in the pilot batch.",
    )
    parser.add_argument(
        "--downloaded-pdf-quota",
        type=int,
        default=50,
        help="Target number of already-downloaded PDFs to include when available.",
    )
    parser.add_argument(
        "--batch-name",
        default="abstract-pilot-v1",
        help="Directory name for output artifacts.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory for generated pilot artifacts.",
    )
    return parser.parse_args()


def stable_rank(paper_id: str) -> str:
    return hashlib.sha256(paper_id.encode("utf-8")).hexdigest()


def parse_csv_argument(value):
    if value is None:
        return None
    parts = [part.strip() for part in value.split(",")]
    return [part for part in parts if part]


def fetch_candidates(
    connection,
    source_corpus: str,
    literature_families,
    exclude_evaluation_split: str | None,
    downloaded_only: bool,
):
    query = """
        SELECT
          paper_id,
          source_corpus,
          literature_family,
          evaluation_split,
          title,
          abstract,
          primary_category,
          published_at,
          updated_at,
          pdf_path,
          ingest_status
        FROM papers
        WHERE 1 = 1
          AND abstract IS NOT NULL
          AND trim(abstract) != ''
    """
    params = []

    if source_corpus != "all":
        query += " AND source_corpus = ?"
        params.append(source_corpus)

    if literature_families:
        placeholders = ", ".join("?" for _ in literature_families)
        query += f" AND literature_family IN ({placeholders})"
        params.extend(literature_families)

    if exclude_evaluation_split:
        query += " AND evaluation_split != ?"
        params.append(exclude_evaluation_split)

    if downloaded_only:
        query += " AND ingest_status = 'pdf_downloaded'"

    rows = []
    for row in connection.execute(query, params):
        rows.append(
            {
                "paper_id": row[0],
                "source_corpus": row[1],
                "literature_family": row[2],
                "evaluation_split": row[3],
                "title": row[4],
                "abstract": row[5],
                "primary_category": row[6] or "unknown",
                "published_at": row[7],
                "updated_at": row[8],
                "pdf_path": row[9],
                "ingest_status": row[10],
            }
        )

    return rows


def stratified_sample(rows, desired_count, key_name):
    if desired_count <= 0 or not rows:
        return []

    if desired_count >= len(rows):
        return sorted(rows, key=lambda row: stable_rank(row["paper_id"]))

    by_category = {}
    for row in rows:
        by_category.setdefault(row[key_name], []).append(row)

    total = len(rows)
    allocations = {}
    remainders = []

    for category, category_rows in by_category.items():
        exact = desired_count * len(category_rows) / total
        base = math.floor(exact)
        if base == 0 and exact > 0:
            base = 1
        allocations[category] = min(base, len(category_rows))
        remainders.append((exact - math.floor(exact), category))

    allocated = sum(allocations.values())

    if allocated > desired_count:
        ordered_categories = sorted(
            allocations,
            key=lambda category: (
                allocations[category],
                len(by_category[category]),
                category,
            ),
        )
        for category in ordered_categories:
            while allocated > desired_count and allocations[category] > 0:
                allocations[category] -= 1
                allocated -= 1

    if allocated < desired_count:
        for _, category in sorted(remainders, reverse=True):
            if allocated >= desired_count:
                break
            capacity = len(by_category[category]) - allocations[category]
            if capacity <= 0:
                continue
            allocations[category] += 1
            allocated += 1

    selected = []
    for category, category_rows in by_category.items():
        ordered = sorted(category_rows, key=lambda row: stable_rank(row["paper_id"]))
        selected.extend(ordered[: allocations[category]])

    selected = sorted(selected, key=lambda row: stable_rank(row["paper_id"]))
    return selected[:desired_count]


def select_batch(
    connection,
    source_corpus: str,
    literature_families,
    exclude_evaluation_split: str | None,
    batch_size: int,
    downloaded_pdf_quota: int,
):
    downloaded_rows = fetch_candidates(
        connection=connection,
        source_corpus=source_corpus,
        literature_families=literature_families,
        exclude_evaluation_split=exclude_evaluation_split,
        downloaded_only=True,
    )
    all_rows = fetch_candidates(
        connection=connection,
        source_corpus=source_corpus,
        literature_families=literature_families,
        exclude_evaluation_split=exclude_evaluation_split,
        downloaded_only=False,
    )

    downloaded_target = min(downloaded_pdf_quota, batch_size, len(downloaded_rows))
    # @context decision -- Mixed-family pilots stratify on `literature_family` first so the
    # existing q-fin anchor corpus cannot drown adjacent-domain seeds once multiple corpora land.
    downloaded_selected = stratified_sample(downloaded_rows, downloaded_target, "literature_family")
    selected_ids = {row["paper_id"] for row in downloaded_selected}

    remaining_needed = batch_size - len(downloaded_selected)
    remaining_pool = [
        row for row in all_rows if row["paper_id"] not in selected_ids
    ]
    remaining_selected = stratified_sample(remaining_pool, remaining_needed, "literature_family")

    selected = downloaded_selected + remaining_selected
    selected = sorted(selected, key=lambda row: stable_rank(row["paper_id"]))
    return selected


def write_outputs(
    output_dir: Path,
    selected_rows,
    source_corpus: str,
    literature_families,
    excluded_evaluation_split: str | None,
    batch_size: int,
    downloaded_pdf_quota: int,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / "papers.jsonl"
    ids_path = output_dir / "paper_ids.txt"
    csv_path = output_dir / "papers.csv"
    summary_path = output_dir / "summary.json"

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in selected_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    with ids_path.open("w", encoding="utf-8") as handle:
        for row in selected_rows:
            handle.write(f"{row['paper_id']}\n")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "literature_family",
                "evaluation_split",
                "primary_category",
                "ingest_status",
                "published_at",
                "updated_at",
                "title",
            ],
        )
        writer.writeheader()
        for row in selected_rows:
            writer.writerow(
                {
                    "paper_id": row["paper_id"],
                    "literature_family": row["literature_family"],
                    "evaluation_split": row["evaluation_split"],
                    "primary_category": row["primary_category"],
                    "ingest_status": row["ingest_status"],
                    "published_at": row["published_at"],
                    "updated_at": row["updated_at"],
                    "title": row["title"],
                }
            )

    by_category = {}
    by_family = {}
    by_status = {}
    for row in selected_rows:
        by_family[row["literature_family"]] = by_family.get(row["literature_family"], 0) + 1
        by_category[row["primary_category"]] = by_category.get(row["primary_category"], 0) + 1
        by_status[row["ingest_status"]] = by_status.get(row["ingest_status"], 0) + 1

    summary = {
        "batch_size": len(selected_rows),
        "requested_batch_size": batch_size,
        "requested_downloaded_pdf_quota": downloaded_pdf_quota,
        "source_corpus": source_corpus,
        "literature_families": literature_families or ["*"],
        "excluded_evaluation_split": excluded_evaluation_split,
        "literature_family_counts": dict(
            sorted(by_family.items(), key=lambda item: (-item[1], item[0]))
        ),
        "category_counts": dict(sorted(by_category.items(), key=lambda item: (-item[1], item[0]))),
        "ingest_status_counts": dict(sorted(by_status.items())),
        "artifacts": {
            "jsonl": str(jsonl_path.resolve()),
            "ids": str(ids_path.resolve()),
            "csv": str(csv_path.resolve()),
        },
    }

    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary_path


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_root).resolve() / args.batch_name

    connection = sqlite3.connect(str(db_path))
    try:
        selected = select_batch(
            connection=connection,
            source_corpus=args.source_corpus,
            literature_families=parse_csv_argument(args.literature_families),
            exclude_evaluation_split=args.exclude_evaluation_split,
            batch_size=args.batch_size,
            downloaded_pdf_quota=args.downloaded_pdf_quota,
        )
    finally:
        connection.close()

    summary_path = write_outputs(
        output_dir=output_dir,
        selected_rows=selected,
        source_corpus=args.source_corpus,
        literature_families=parse_csv_argument(args.literature_families),
        excluded_evaluation_split=args.exclude_evaluation_split,
        batch_size=args.batch_size,
        downloaded_pdf_quota=args.downloaded_pdf_quota,
    )

    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
