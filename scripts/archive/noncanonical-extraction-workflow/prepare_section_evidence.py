#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"

KNOWN_SECTION_LABELS = {
    "abstract",
    "introduction",
    "background",
    "related work",
    "literature review",
    "model",
    "setup",
    "method",
    "methodology",
    "data",
    "empirical strategy",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "appendix",
    "references",
}
SECTION_PREFIX_RE = re.compile(r"^(?:(?:\d+(?:\.\d+)*)|(?:[ivxlcdm]+))[.)]?\s+", re.IGNORECASE)
GENERIC_SECTION_RE = re.compile(r"^\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9/&,\- ]{2,80}$")
TOKEN_RE = re.compile(r"[a-z0-9]{4,}")
WHITESPACE_RE = re.compile(r"\s+")
STOPWORDS = {
    "about",
    "above",
    "after",
    "before",
    "below",
    "between",
    "could",
    "first",
    "from",
    "have",
    "into",
    "might",
    "model",
    "paper",
    "result",
    "section",
    "study",
    "that",
    "their",
    "there",
    "these",
    "this",
    "those",
    "using",
    "with",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parse downloaded PDFs into section-aware local storage and upgrade mechanism evidence spans."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--paper-id",
        action="append",
        default=None,
        help="Optional explicit paper id to process. Repeat for multiple papers.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on processed papers when no explicit ids are provided.",
    )
    parser.add_argument(
        "--min-section-chars",
        type=int,
        default=160,
        help="Minimum section length before a parsed block is retained on its own.",
    )
    return parser.parse_args()


def load_pdf_text(pdf_path: Path):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SystemExit(
            "pypdf is required. Run via `uv run --with pypdf python3 scripts/prepare_section_evidence.py ...`."
        ) from exc

    reader = PdfReader(str(pdf_path))
    page_texts = []
    for page in reader.pages:
        page_texts.append(page.extract_text() or "")
    text = "\n".join(page_texts)
    return text


def normalize_line(line: str):
    collapsed = WHITESPACE_RE.sub(" ", line.replace("\x00", " ")).strip()
    return collapsed


def canonical_section_label(raw_label: str):
    label = SECTION_PREFIX_RE.sub("", raw_label.strip())
    label = WHITESPACE_RE.sub(" ", label).strip(" :-")
    return label or "body"


def is_section_heading(line: str):
    if not line:
        return False
    if len(line) > 90:
        return False
    canonical = canonical_section_label(line).lower()
    if canonical in KNOWN_SECTION_LABELS:
        return True
    if line.endswith("."):
        return False
    if GENERIC_SECTION_RE.match(line):
        return True
    words = canonical.split()
    if 0 < len(words) <= 6 and all(word[:1].isupper() or word.isupper() for word in line.split()):
        return True
    return False


def merge_small_sections(parsed_sections, min_section_chars: int):
    merged = []
    pending = None
    for section in parsed_sections:
        if pending is None:
            pending = dict(section)
            continue
        if len(pending["content_text"]) < min_section_chars:
            pending["content_text"] = f"{pending['content_text']}\n\n{section['content_text']}".strip()
            pending["section_label"] = pending["section_label"]
            continue
        merged.append(pending)
        pending = dict(section)

    if pending is not None:
        if merged and len(pending["content_text"]) < min_section_chars:
            merged[-1]["content_text"] = (
                f"{merged[-1]['content_text']}\n\n{pending['content_text']}"
            ).strip()
        else:
            merged.append(pending)
    return merged


def parse_sections(raw_text: str, min_section_chars: int):
    lines = [normalize_line(line) for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        raise ValueError("pdf_text_empty")

    sections = []
    current_label = "front_matter"
    buffer = []

    def flush_section():
        if not buffer:
            return
        content = "\n".join(buffer).strip()
        if not content:
            return
        sections.append(
            {
                "section_label": current_label,
                "content_text": content,
            }
        )

    for line in lines:
        if is_section_heading(line):
            flush_section()
            buffer = []
            current_label = canonical_section_label(line)
            continue
        buffer.append(line)
    flush_section()

    if not sections:
        sections = [{"section_label": "full_text", "content_text": "\n".join(lines)}]

    return merge_small_sections(sections, min_section_chars)


def section_hash(content_text: str):
    return hashlib.sha256(content_text.encode("utf-8")).hexdigest()


def record_parse_failure(connection, paper_id: str, failure_type: str, failure_reason: str, source_path: str):
    connection.execute(
        """
        DELETE FROM parse_failures
        WHERE paper_id = ? AND failure_stage = 'section_parse'
        """,
        (paper_id,),
    )
    connection.execute(
        """
        INSERT INTO parse_failures (
          paper_id,
          failure_stage,
          failure_type,
          failure_reason,
          source_path
        )
        VALUES (?, 'section_parse', ?, ?, ?)
        """,
        (paper_id, failure_type, failure_reason, source_path),
    )


def replace_sections(connection, paper_id: str, sections):
    connection.execute(
        """
        DELETE FROM paper_sections
        WHERE paper_id = ?
        """,
        (paper_id,),
    )
    inserted = []
    for index, section in enumerate(sections):
        connection.execute(
            """
            INSERT INTO paper_sections (
              paper_id,
              section_label,
              section_order,
              content_text,
              content_hash,
              extraction_method
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                section["section_label"],
                index,
                section["content_text"],
                section_hash(section["content_text"]),
                "pypdf-rule-based-v1",
            ),
        )
        section_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        inserted.append(
            {
                "section_id": section_id,
                "section_label": section["section_label"],
                "content_text": section["content_text"],
            }
        )
    connection.execute(
        """
        DELETE FROM parse_failures
        WHERE paper_id = ? AND failure_stage = 'section_parse'
        """,
        (paper_id,),
    )
    return inserted


def significant_tokens(text: str):
    tokens = []
    for token in TOKEN_RE.findall(text.lower()):
        if token in STOPWORDS:
            continue
        tokens.append(token)
    deduped = []
    seen = set()
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped[:12]


def score_section_match(section, query_tokens):
    section_text = section["content_text"].lower()
    token_hits = [token for token in query_tokens if token in section_text]
    label = section["section_label"].lower()
    label_bonus = 0
    if label in {"abstract", "introduction", "model", "setup", "method", "results", "discussion", "conclusion"}:
        label_bonus = 1
    return len(token_hits) * 10 + label_bonus, token_hits


def snippet_bounds(section_text: str, tokens):
    lowered = section_text.lower()
    anchor = 0
    for token in tokens:
        found = lowered.find(token)
        if found != -1:
            anchor = found
            break
    start = max(0, anchor - 180)
    end = min(len(section_text), anchor + 320)
    while start > 0 and section_text[start - 1] not in "\n. ":
        start -= 1
    while end < len(section_text) and section_text[end - 1] not in "\n. ":
        end += 1
    return start, min(end, len(section_text))


def upgrade_evidence_spans(connection, paper_id: str, sections):
    mechanism_rows = connection.execute(
        """
        SELECT mechanism_instance_id, mechanism_label, mechanism_summary, evidence_confidence
        FROM mechanism_instances
        WHERE paper_id = ? AND lifecycle_status = 'active'
        ORDER BY mechanism_instance_id
        """,
        (paper_id,),
    ).fetchall()
    upgraded = 0
    for mechanism_instance_id, mechanism_label, mechanism_summary, evidence_confidence in mechanism_rows:
        query_tokens = significant_tokens(f"{mechanism_label} {mechanism_summary}")
        if not query_tokens:
            continue

        best_section = None
        best_score = 0
        best_hits = []
        for section in sections:
            score, hits = score_section_match(section, query_tokens)
            if score > best_score:
                best_score = score
                best_section = section
                best_hits = hits

        if best_section is None or best_score <= 0:
            continue

        start, end = snippet_bounds(best_section["content_text"], best_hits or query_tokens)
        snippet = best_section["content_text"][start:end].strip()
        if not snippet:
            continue

        # @context decision -- C07 only upgrades evidence spans when a parsed section contains
        # positive token overlap with the mechanism label/summary. Otherwise the C05 abstract-backed
        # fallback remains safer than inventing a section citation with no textual support.
        connection.execute(
            """
            DELETE FROM mechanism_evidence_spans
            WHERE mechanism_instance_id = ?
            """,
            (mechanism_instance_id,),
        )
        provenance = {
            "source_stage": "section_parse",
            "parser_version": "pypdf-rule-based-v1",
            "section_label": best_section["section_label"],
            "matched_tokens": best_hits,
            "evidence_confidence": evidence_confidence,
        }
        connection.execute(
            """
            INSERT INTO mechanism_evidence_spans (
              mechanism_instance_id,
              paper_id,
              section_id,
              evidence_kind,
              char_start,
              char_end,
              evidence_text,
              provenance_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mechanism_instance_id,
                paper_id,
                best_section["section_id"],
                "section_snippet",
                start,
                end,
                snippet,
                json.dumps(provenance, sort_keys=True),
            ),
        )
        upgraded += 1

    return upgraded


def target_papers(connection, explicit_paper_ids, limit):
    if explicit_paper_ids:
        rows = []
        for paper_id in explicit_paper_ids:
            row = connection.execute(
                """
                SELECT paper_id, pdf_path
                FROM papers
                WHERE paper_id = ?
                """,
                (paper_id,),
            ).fetchone()
            if row is not None:
                rows.append({"paper_id": row[0], "pdf_path": row[1]})
        return rows

    query = """
        SELECT paper_id, pdf_path
        FROM papers
        WHERE pdf_path IS NOT NULL AND trim(pdf_path) != ''
        ORDER BY paper_id
    """
    params = ()
    if limit is not None:
        query += " LIMIT ?"
        params = (limit,)
    return [
        {"paper_id": row[0], "pdf_path": row[1]}
        for row in connection.execute(query, params)
    ]


def process_papers(connection, papers, min_section_chars: int):
    processed = 0
    parsed = 0
    failed = 0
    sections_written = 0
    evidence_upgraded = 0

    connection.execute("BEGIN")
    try:
        for paper in papers:
            processed += 1
            pdf_path = Path(paper["pdf_path"]).resolve() if paper["pdf_path"] else None
            if pdf_path is None or not pdf_path.exists():
                record_parse_failure(
                    connection=connection,
                    paper_id=paper["paper_id"],
                    failure_type="pdf_missing",
                    failure_reason="pdf_path_missing_or_not_found",
                    source_path=str(pdf_path) if pdf_path else None,
                )
                failed += 1
                continue

            try:
                raw_text = load_pdf_text(pdf_path)
                parsed_sections = parse_sections(raw_text, min_section_chars=min_section_chars)
            except Exception as exc:
                record_parse_failure(
                    connection=connection,
                    paper_id=paper["paper_id"],
                    failure_type="section_parse_error",
                    failure_reason=str(exc),
                    source_path=str(pdf_path),
                )
                failed += 1
                continue

            stored_sections = replace_sections(
                connection=connection,
                paper_id=paper["paper_id"],
                sections=parsed_sections,
            )
            sections_written += len(stored_sections)
            evidence_upgraded += upgrade_evidence_spans(
                connection=connection,
                paper_id=paper["paper_id"],
                sections=stored_sections,
            )
            parsed += 1

        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "processed": processed,
        "parsed": parsed,
        "failed": failed,
        "sections_written": sections_written,
        "evidence_upgraded": evidence_upgraded,
    }


def main():
    args = parse_args()
    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    try:
        papers = target_papers(connection, args.paper_id, args.limit)
        summary = process_papers(
            connection=connection,
            papers=papers,
            min_section_chars=args.min_section_chars,
        )
    finally:
        connection.close()

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
