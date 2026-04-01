#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
NON_CONTENT_LABEL_RE = re.compile(
    r"(front[_ ]?matter|references?|acknowledg|appendix|bibliography|abstract)",
    re.IGNORECASE,
)
SURPRISE_HINT_RE = re.compile(
    r"(conclusion|conclusions|discussion|summary|future work|limitation|limitations|implication|implications|remark|takeaway|finding|findings)",
    re.IGNORECASE,
)
MECHANISM_HINT_RE = re.compile(
    r"(results?|empirical|numerical|simulation|experiment|analysis|evidence|evaluation|case study|order book|dynamics)",
    re.IGNORECASE,
)
REGIME_HINT_RE = re.compile(
    r"(introduction|background|institutional|setting|market design|design|model|assumption|constraint|data|dataset|preliminar|notation|framework|environment)",
    re.IGNORECASE,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Materialize canonical text views for embedding-first discovery."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="text-views-materialization-20260328")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def tokenize_estimate(text: str) -> int:
    return len((text or "").split())


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def decode_categories(raw_categories: str | None) -> list[str]:
    if not raw_categories:
        return []
    try:
        payload = json.loads(raw_categories)
    except json.JSONDecodeError:
        return [normalize_text(raw_categories)] if normalize_text(raw_categories) else []
    if isinstance(payload, list):
        return [normalize_text(str(item)) for item in payload if normalize_text(str(item))]
    text = normalize_text(str(payload))
    return [text] if text else []


def is_content_section(label: str, text: str) -> bool:
    signal = normalize_text(f"{label} {text[:160]}")
    if not signal:
        return False
    return NON_CONTENT_LABEL_RE.search(signal) is None


def render_sections(sections: list[dict], limit: int) -> str:
    rendered = []
    for item in sections[:limit]:
        label = normalize_text(item["label"]) or "section"
        text = normalize_text(item["text"])
        if text:
            rendered.append(f"[{label}] {text}")
    return normalize_text("\n".join(rendered))


def ranked_bucket_sections(section_snippets: list[dict], bucket: str) -> list[dict]:
    content_sections = [
        item
        for item in section_snippets
        if is_content_section(item.get("label", ""), item.get("text", ""))
    ]
    if not content_sections:
        return []

    ranked: list[tuple[int, int, dict]] = []
    total = len(content_sections)
    for idx, item in enumerate(content_sections):
        signal = normalize_text(f"{item.get('label', '')} {item.get('text', '')[:240]}")
        lead_bonus = 3 if idx < min(2, total) else 0
        tail_bonus = 3 if idx >= max(0, total - 2) else 0
        middle_bonus = 2 if 0 < idx < total - 1 else 0

        if bucket == "surprise":
            score = (8 if SURPRISE_HINT_RE.search(signal) else 0) + tail_bonus + middle_bonus
        elif bucket == "mechanism":
            score = (8 if MECHANISM_HINT_RE.search(signal) else 0) + middle_bonus + (1 if idx >= 1 else 0)
        elif bucket == "regime":
            score = (8 if REGIME_HINT_RE.search(signal) else 0) + lead_bonus
        else:
            score = 1
        ranked.append((score, -idx, item))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = [item for score, _, item in ranked if score > 0]
    if selected:
        return sorted(selected, key=lambda item: item["order"])

    # @context decision -- section labels in the corpus are often malformed (`e`, `t∑`, `n∑`).
    # Discovery cannot depend on clean labels, so each section bucket falls back to position-aware
    # slices over non-reference sections rather than title/abstract backstops.
    if bucket == "surprise":
        return content_sections[max(0, total - 2) :]
    if bucket == "mechanism":
        start = 1 if total > 2 else 0
        stop = total - 1 if total > 2 else total
        return content_sections[start:stop] or content_sections[: min(2, total)]
    if bucket == "regime":
        return content_sections[: min(2, total)]
    return content_sections


def build_section_derived_views(section_snippets: list[dict]) -> dict[str, str]:
    content_sections = [
        item
        for item in section_snippets
        if is_content_section(item.get("label", ""), item.get("text", ""))
    ]
    return {
        "surprise_sections": render_sections(ranked_bucket_sections(content_sections, "surprise"), limit=3),
        "mechanism_sections": render_sections(ranked_bucket_sections(content_sections, "mechanism"), limit=3),
        "regime_sections": render_sections(ranked_bucket_sections(content_sections, "regime"), limit=3),
        "all_sections": render_sections(content_sections, limit=6),
    }


def load_source_rows(connection: sqlite3.Connection, limit: int | None) -> list[dict]:
    sql = """
        SELECT
          p.paper_id,
          p.title,
          p.abstract,
          p.categories_json,
          p.primary_category,
          p.literature_family,
          p.evaluation_split
        FROM papers p
        WHERE p.abstract IS NOT NULL
          AND trim(p.abstract) != ''
        ORDER BY p.paper_id
    """
    params: tuple[object, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)
    paper_rows = connection.execute(sql, params).fetchall()
    paper_ids = [row["paper_id"] for row in paper_rows]
    if not paper_ids:
        return []

    placeholders = ",".join("?" for _ in paper_ids)
    section_rows = connection.execute(
        f"""
        SELECT
          paper_id,
          section_label,
          section_order,
          content_text
        FROM paper_sections
        WHERE paper_id IN ({placeholders})
        ORDER BY paper_id, section_order
        """,
        paper_ids,
    ).fetchall()

    section_map = defaultdict(list)
    for row in section_rows:
        text = normalize_text(row["content_text"])
        if not text:
            continue
        section_map[row["paper_id"]].append(
            {
                "label": normalize_text(row["section_label"]),
                "order": row["section_order"],
                "text": text[:1400],
            }
        )

    source_rows = []
    for row in paper_rows:
        categories = decode_categories(row["categories_json"])
        primary_category = normalize_text(row["primary_category"])
        if primary_category and primary_category not in categories:
            categories.insert(0, primary_category)
        sections = section_map.get(row["paper_id"], [])[:4]
        section_view = "\n".join(f"[{item['label']}] {item['text']}" for item in sections)
        source_rows.append(
            {
                "paper_id": row["paper_id"],
                "title": normalize_text(row["title"]),
                "abstract": normalize_text(row["abstract"]),
                "primary_category": primary_category,
                "categories": categories,
                "literature_family": normalize_text(row["literature_family"]),
                "evaluation_split": normalize_text(row["evaluation_split"]),
                "section_view": normalize_text(section_view),
                "section_snippets": sections,
            }
        )
    return source_rows


def build_text_views(source_rows: list[dict]) -> list[dict]:
    view_rows: list[dict] = []
    for row in source_rows:
        category_string = normalize_text(
            " ".join(
                item
                for item in row["categories"]
                + [row["literature_family"], row["evaluation_split"]]
                if normalize_text(item)
            )
        )
        title = row["title"]
        abstract = row["abstract"]
        section_text = row["section_view"]
        section_views = build_section_derived_views(row.get("section_snippets", []))
        raw_views = {
            "title_abs": normalize_text(f"{title}\n{abstract}"),
            "abs_only": abstract,
            "title_abs_cats": normalize_text(f"{title}\n{abstract}\n{category_string}"),
            "title_only": title,
            "category_string": category_string,
            # @context requirement -- this view is the bridge between metadata-first mapping and
            # later selective full-text follow-up. It must prefer section snippets when they
            # exist, but fall back to the abstract so every eligible paper stays embeddable.
            "section_or_abs": normalize_text(f"{title}\n{section_text or abstract}"),
            **section_views,
        }
        for view_type, text in raw_views.items():
            text = normalize_text(text)
            view_rows.append(
                {
                    "paper_id": row["paper_id"],
                    "view_type": view_type,
                    "text": text,
                    "token_estimate": tokenize_estimate(text),
                    "text_sha256": sha256_text(text),
                }
            )
    return view_rows


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def upsert_text_views(connection: sqlite3.Connection, view_rows: list[dict]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for row in view_rows:
        existing = connection.execute(
            """
            SELECT text_sha256
            FROM text_views
            WHERE paper_id = ? AND view_type = ?
            """,
            (row["paper_id"], row["view_type"]),
        ).fetchone()
        if existing is None:
            inserted += 1
        elif existing["text_sha256"] != row["text_sha256"]:
            updated += 1
        connection.execute(
            """
            INSERT INTO text_views (paper_id, view_type, text, token_estimate, text_sha256)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(paper_id, view_type) DO UPDATE SET
              text = excluded.text,
              token_estimate = excluded.token_estimate,
              text_sha256 = excluded.text_sha256
            """,
            (
                row["paper_id"],
                row["view_type"],
                row["text"],
                row["token_estimate"],
                row["text_sha256"],
            ),
        )
    return inserted, updated


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        log_run_event(
            connection,
            args.run_id,
            "text_views",
            "started",
            {"db_path": str(db_path), "limit": args.limit},
        )
        source_rows = load_source_rows(connection, args.limit)
        view_rows = build_text_views(source_rows)
        inserted, updated = upsert_text_views(connection, view_rows)
        metrics = {
            "run_id": args.run_id,
            "paper_count": len(source_rows),
            "view_count": len(view_rows),
            "inserted": inserted,
            "updated": updated,
            "view_types": sorted({row["view_type"] for row in view_rows}),
            "section_backed_paper_count": sum(1 for row in source_rows if row["section_view"]),
        }
        metrics_path = output_dir / "text_view_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(
            connection,
            args.run_id,
            "text_views",
            "completed",
            {"metrics_path": str(metrics_path), **metrics},
        )
        connection.commit()
    finally:
        connection.close()

    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
