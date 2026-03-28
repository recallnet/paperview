#!/usr/bin/env python3

import argparse
import json
import re
import sqlite3
from datetime import date
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_CORPUS_CONFIG_PATH = ROOT / "configs" / "corpus.yaml"
AMBIGUOUS_MARKET_KEYWORDS = {"option", "options"}
MARKET_DISAMBIGUATION_TERMS = {
    "arbitrage",
    "derivative",
    "derivatives",
    "hedge",
    "hedging",
    "liquidity",
    "market",
    "market maker",
    "option pricing",
    "portfolio",
    "price",
    "pricing",
    "trade",
    "trading",
    "venue",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Materialize canonical corpus memberships for discovery, realized-market, stranded-alpha, and holdout slices."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--corpus-config-path", default=str(DEFAULT_CORPUS_CONFIG_PATH))
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def category_prefix_match(categories: list[str], prefixes: list[str]) -> bool:
    lowered = [item.lower() for item in categories]
    for prefix in prefixes:
        prefix_lower = prefix.lower()
        if any(item == prefix_lower or item.startswith(prefix_lower + ".") for item in lowered):
            return True
    return False


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = (text or "").lower()
    # @context risk -- realized-market membership is an anti-realization boundary, so naive substring
    # matching leaks generic optimization/control papers via words like "optional" or "optimization".
    # Boundary-aware regex matching keeps sparse market cues usable without turning the firewall into
    # an everything-before-2024 bucket.
    hits = []
    for keyword in keywords:
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        if not re.search(pattern, lowered):
            continue
        if keyword.lower() in AMBIGUOUS_MARKET_KEYWORDS and not any(
            term in lowered for term in MARKET_DISAMBIGUATION_TERMS
        ):
            continue
        if re.search(pattern, lowered):
            hits.append(keyword)
    return hits


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def decode_categories(raw_categories: str | None, primary_category: str | None) -> list[str]:
    categories: list[str] = []
    if raw_categories:
        try:
            payload = json.loads(raw_categories)
        except json.JSONDecodeError:
            payload = [raw_categories]
        if isinstance(payload, list):
            categories.extend(str(item) for item in payload)
        else:
            categories.append(str(payload))
    if primary_category:
        categories.insert(0, primary_category)
    seen = set()
    deduped = []
    for item in categories:
        cleaned = " ".join(str(item).split())
        if cleaned and cleaned not in seen:
            deduped.append(cleaned)
            seen.add(cleaned)
    return deduped


def build_memberships(connection: sqlite3.Connection, config: dict) -> list[tuple]:
    discovery_end = parse_iso_date(config["time_firewall"]["discovery_end"])
    holdout_start = parse_iso_date(config["time_firewall"]["holdout_start"])
    rows = connection.execute(
        """
        SELECT paper_id, title, abstract, categories_json, primary_category, published_at
        FROM papers
        ORDER BY paper_id
        """
    ).fetchall()
    membership_rows = []
    for row in rows:
        paper_date = parse_iso_date(row["published_at"])
        categories = decode_categories(row["categories_json"], row["primary_category"])
        text = f"{row['title'] or ''}\n{row['abstract'] or ''}"
        if discovery_end and paper_date and paper_date <= discovery_end:
            membership_rows.append(
                (
                    row["paper_id"],
                    "discovery",
                    "time_firewall",
                    json.dumps({"published_at": row["published_at"]}, sort_keys=True),
                )
            )

        realized_cfg = config["corpus_memberships"]["realized_market"]
        realized_keyword_hits = keyword_hits(text, realized_cfg.get("keywords", []))
        realized_category_match = category_prefix_match(categories, realized_cfg.get("category_prefixes", []))
        # @context decision -- realized-market membership must represent explicit market discourse,
        # not the entire pre-2024 q-fin archive. Category membership alone is too broad for the
        # anti-realization firewall, so the slice now requires concrete realized-market language and
        # only carries category matches as supporting rationale.
        if (
            discovery_end
            and paper_date
            and paper_date <= discovery_end
            and bool(realized_keyword_hits)
        ):
            membership_rows.append(
                (
                    row["paper_id"],
                    "realized_market",
                    "keyword_discourse",
                    json.dumps(
                        {
                            "published_at": row["published_at"],
                            "category_match": realized_category_match,
                            "keyword_hits": realized_keyword_hits,
                        },
                        sort_keys=True,
                    ),
                )
            )

        stranded_cfg = config["corpus_memberships"]["stranded_alpha"]
        stranded_start = parse_iso_date(stranded_cfg["start_date"])
        if (
            discovery_end
            and stranded_start
            and paper_date
            and stranded_start <= paper_date <= discovery_end
            and category_prefix_match(categories, stranded_cfg.get("category_prefixes", []))
        ):
            membership_rows.append(
                (
                    row["paper_id"],
                    "stranded_alpha",
                    "category_and_date",
                    json.dumps({"published_at": row["published_at"]}, sort_keys=True),
                )
            )

        holdout_cfg = config["corpus_memberships"]["holdout"]
        holdout_keyword_hits = keyword_hits(text, holdout_cfg.get("keywords", []))
        holdout_category_match = category_prefix_match(categories, holdout_cfg.get("category_prefixes", []))
        if (
            holdout_start
            and paper_date
            and paper_date >= holdout_start
            and (holdout_category_match or bool(holdout_keyword_hits))
        ):
            membership_rows.append(
                (
                    row["paper_id"],
                    "holdout",
                    "category_or_keyword",
                    json.dumps(
                        {
                            "published_at": row["published_at"],
                            "category_match": holdout_category_match,
                            "keyword_hits": holdout_keyword_hits,
                        },
                        sort_keys=True,
                    ),
                )
            )
    return membership_rows


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    config = load_yaml(Path(args.corpus_config_path).resolve())
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        log_run_event(
            connection,
            args.run_id,
            "corpus_memberships",
            "started",
            {"corpus_config_path": str(Path(args.corpus_config_path).resolve())},
        )
        rows = build_memberships(connection, config)
        connection.execute("DELETE FROM corpus_memberships WHERE run_id = ?", (args.run_id,))
        connection.executemany(
            """
            INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source, rationale_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(args.run_id, *row) for row in rows],
        )
        counts = dict(
            connection.execute(
                """
                SELECT corpus_id, count(*)
                FROM corpus_memberships
                WHERE run_id = ?
                GROUP BY corpus_id
                """,
                (args.run_id,),
            ).fetchall()
        )
        metrics = {
            "run_id": args.run_id,
            "membership_count": len(rows),
            "corpus_counts": counts,
        }
        metrics_path = output_dir / "corpus_membership_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(
            connection,
            args.run_id,
            "corpus_memberships",
            "completed",
            {"metrics_path": str(metrics_path), **metrics},
        )
        connection.commit()
    finally:
        connection.close()

    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
