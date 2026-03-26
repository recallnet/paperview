#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_METADATA_JSONL = ROOT / "data" / "arxiv-qfin" / "metadata.jsonl"
DEFAULT_PDF_DIR = ROOT / "data" / "arxiv-qfin" / "pdfs"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Load harvested metadata into the canonical paperview SQLite store."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--metadata-jsonl",
        default=str(DEFAULT_METADATA_JSONL),
        help="Path to harvested metadata JSONL.",
    )
    parser.add_argument(
        "--pdf-dir",
        default=str(DEFAULT_PDF_DIR),
        help="Directory containing downloaded PDFs.",
    )
    parser.add_argument(
        "--source-corpus",
        default="arxiv-qfin",
        help="Corpus label to store on imported papers.",
    )
    parser.add_argument(
        "--literature-family",
        default="q_fin",
        help="Canonical literature family label to store on imported papers.",
    )
    parser.add_argument(
        "--evaluation-split",
        default="tuning",
        choices=["tuning", "holdout"],
        help="Evaluation split label stored on imported papers.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on imported records for test runs.",
    )
    return parser.parse_args()


def canonical_pdf_path(pdf_dir: Path, paper_id: str):
    candidate = pdf_dir / f"{paper_id.replace('/', '_')}.pdf"
    return candidate if candidate.exists() else None


def authors_json(record):
    authors = record.get("authors") or []
    return json.dumps(authors, sort_keys=True)


def categories_json(record):
    categories = record.get("categories") or []
    return json.dumps(categories, sort_keys=True)


def primary_category(record):
    categories = record.get("categories") or []
    return categories[0] if categories else None


def ingest_status(pdf_path):
    return "pdf_downloaded" if pdf_path else "metadata_only"


def load_records(
    connection,
    metadata_jsonl: Path,
    pdf_dir: Path,
    source_corpus: str,
    literature_family: str,
    evaluation_split: str,
    limit,
):
    inserted = 0
    updated = 0
    processed = 0

    connection.execute("BEGIN")
    try:
        with metadata_jsonl.open("r", encoding="utf-8") as handle:
            for line in handle:
                if limit is not None and processed >= limit:
                    break

                record = json.loads(line)
                paper_id = record["id"]
                pdf_path = canonical_pdf_path(pdf_dir, paper_id)
                existed = connection.execute(
                    "SELECT 1 FROM papers WHERE paper_id = ?",
                    (paper_id,),
                ).fetchone() is not None

                connection.execute(
                    """
                    INSERT INTO papers (
                      paper_id,
                      source_corpus,
                      literature_family,
                      evaluation_split,
                      title,
                      abstract,
                      authors_json,
                      categories_json,
                      primary_category,
                      published_at,
                      updated_at,
                      metadata_path,
                      pdf_path,
                      ingest_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(paper_id) DO UPDATE SET
                      source_corpus = excluded.source_corpus,
                      literature_family = excluded.literature_family,
                      evaluation_split = excluded.evaluation_split,
                      title = excluded.title,
                      abstract = excluded.abstract,
                      authors_json = excluded.authors_json,
                      categories_json = excluded.categories_json,
                      primary_category = excluded.primary_category,
                      published_at = excluded.published_at,
                      updated_at = excluded.updated_at,
                      metadata_path = excluded.metadata_path,
                      pdf_path = excluded.pdf_path,
                      ingest_status = excluded.ingest_status,
                      updated_at_record = CURRENT_TIMESTAMP
                    """,
                    (
                        paper_id,
                        source_corpus,
                        literature_family,
                        evaluation_split,
                        record.get("title"),
                        record.get("abstract"),
                        authors_json(record),
                        categories_json(record),
                        primary_category(record),
                        record.get("created"),
                        record.get("updated"),
                        str(metadata_jsonl.resolve()),
                        str(pdf_path.resolve()) if pdf_path else None,
                        ingest_status(pdf_path),
                    ),
                )

                if existed:
                    updated += 1
                else:
                    inserted += 1
                processed += 1

        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return processed, inserted, updated


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    metadata_jsonl = Path(args.metadata_jsonl).resolve()
    pdf_dir = Path(args.pdf_dir).resolve()

    connection = sqlite3.connect(str(db_path))
    try:
        processed, inserted, updated = load_records(
            connection=connection,
            metadata_jsonl=metadata_jsonl,
            pdf_dir=pdf_dir,
            source_corpus=args.source_corpus,
            literature_family=args.literature_family,
            evaluation_split=args.evaluation_split,
            limit=args.limit,
        )
        total = connection.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        pdf_downloaded = connection.execute(
            "SELECT COUNT(*) FROM papers WHERE ingest_status = 'pdf_downloaded'"
        ).fetchone()[0]
    finally:
        connection.close()

    print(
        json.dumps(
            {
                "processed": processed,
                "inserted": inserted,
                "updated": updated,
                "papers_total": total,
                "pdf_downloaded": pdf_downloaded,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
