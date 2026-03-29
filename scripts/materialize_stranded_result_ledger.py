#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize the canonical Stranded Result Ledger.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="stranded-result-ledger-20260328")
    parser.add_argument("--shortlist-run-id", default="shortlist-materialization-20260328")
    parser.add_argument("--interpretation-source", choices=("selective", "enhanced_stranded", "diamond_stranded"), default="selective")
    parser.add_argument("--interpretation-run-id", default="selective-interpretation-ingestion-20260328")
    parser.add_argument("--stranding-run-id", default="stranding-score-materialization-20260328")
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def ensure_stranded_result_ledger_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS stranded_result_ledger (
          run_id TEXT NOT NULL,
          shortlist_run_id TEXT NOT NULL,
          interpretation_run_id TEXT NOT NULL,
          shortlist_id TEXT NOT NULL,
          publication_source_surface TEXT NOT NULL DEFAULT 'selective',
          publication_interpretation_run_id TEXT,
          publication_item_id TEXT,
          paper_id TEXT NOT NULL,
          published_at TEXT NOT NULL,
          home_domain TEXT NOT NULL,
          result_summary TEXT NOT NULL,
          why_stranded_or_unrealized TEXT NOT NULL,
          instrument_assumed TEXT NOT NULL,
          modern_equivalent TEXT NOT NULL,
          first_test TEXT NOT NULL,
          gap_to_close TEXT NOT NULL,
          priority_tier TEXT NOT NULL,
          relation_type TEXT NOT NULL,
          ledger_rank INTEGER NOT NULL,
          stranding_score REAL NOT NULL,
          confidence TEXT NOT NULL,
          rationale_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, shortlist_id),
          FOREIGN KEY (shortlist_run_id, shortlist_id) REFERENCES shortlist_items(run_id, shortlist_id) ON DELETE CASCADE,
          FOREIGN KEY (interpretation_run_id, shortlist_id) REFERENCES selective_interpretations(run_id, shortlist_id) ON DELETE CASCADE,
          FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
        )
        """
    )
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(stranded_result_ledger)").fetchall()}
    if "publication_source_surface" not in columns:
        connection.execute(
            """
            ALTER TABLE stranded_result_ledger
            ADD COLUMN publication_source_surface TEXT NOT NULL DEFAULT 'selective'
            """
        )
    if "publication_interpretation_run_id" not in columns:
        connection.execute(
            """
            ALTER TABLE stranded_result_ledger
            ADD COLUMN publication_interpretation_run_id TEXT
            """
        )
    if "publication_item_id" not in columns:
        connection.execute(
            """
            ALTER TABLE stranded_result_ledger
            ADD COLUMN publication_item_id TEXT
            """
        )


def priority_tier(stranding_score: float, confidence: str) -> str:
    confidence = confidence.lower()
    if stranding_score >= 0.3 and confidence in {"high", "medium"}:
        return "p1"
    if stranding_score >= 0.15:
        return "p2"
    return "p3"


def relation_type(classification: str) -> str:
    mapping = {
        "STRANDED_QFIN_RESULT": "direct",
        "TRANSLATION_CANDIDATE": "adaptation",
        "COMPOSITIONAL_CANDIDATE": "calibration",
    }
    return mapping.get(classification, "adaptation")


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Stranded Result Ledger",
        "",
        f"- entry count: `{len(rows)}`",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['ledger_rank']}. {row['paper_id']}",
                "",
                f"- publication item id: `{row['publication_item_id']}`",
                f"- publication source surface: `{row['publication_source_surface']}`",
                f"- date: `{row['published_at']}`",
                f"- home domain: `{row['home_domain']}`",
                f"- priority tier: `{row['priority_tier']}`",
                f"- relation type: `{row['relation_type']}`",
                f"- stranding score: `{row['stranding_score']}`",
                f"- confidence: `{row['confidence']}`",
                "",
                f"Result: {row['result_summary']}",
                "",
                f"Why stranded: {row['why_stranded_or_unrealized']}",
                "",
                f"Instrument assumed: {row['instrument_assumed']}",
                "",
                f"Modern equivalent: {row['modern_equivalent']}",
                "",
                f"First test: {row['first_test']}",
                "",
                f"Gap to close: {row['gap_to_close']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def fetch_selective_source_rows(connection: sqlite3.Connection, interpretation_run_id: str, shortlist_run_id: str, stranding_run_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
          si.shortlist_id,
          si.item_ref,
          interp.classification,
          interp.result_summary,
          interp.first_step,
          interp.instrument_assumed,
          interp.modern_equivalent,
          interp.why_stranded_or_unrealized,
          interp.gap_to_close,
          interp.confidence,
          COALESCE(p.published_at, 'unknown') AS published_at,
          COALESCE(p.primary_category, 'unknown') AS home_domain,
          COALESCE(ss.stranding_score, 0.0) AS stranding_score
        FROM selective_interpretations interp
        JOIN shortlist_items si
          ON si.run_id = interp.shortlist_run_id
         AND si.shortlist_id = interp.shortlist_id
        JOIN papers p
          ON p.paper_id = si.item_ref
        LEFT JOIN stranding_scores ss
          ON ss.run_id = ?
         AND ss.paper_id = si.item_ref
        WHERE interp.run_id = ?
          AND si.run_id = ?
          AND interp.classification = 'STRANDED_QFIN_RESULT'
          AND si.item_type = 'paper'
        ORDER BY ss.stranding_score DESC, p.published_at ASC, si.item_ref ASC
        """,
        (stranding_run_id, interpretation_run_id, shortlist_run_id),
    ).fetchall()


def fetch_enhanced_source_rows(connection: sqlite3.Connection, interpretation_run_id: str, stranding_run_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
          ei.batch_item_id,
          ei.source_ref AS paper_id,
          ei.family_rank,
          ei.classification,
          ei.result_summary,
          ei.first_step,
          ei.instrument_assumed,
          ei.modern_equivalent,
          ei.why_stranded_or_unrealized,
          ei.gap_to_close,
          ei.confidence,
          COALESCE(p.published_at, 'unknown') AS published_at,
          COALESCE(p.primary_category, 'unknown') AS home_domain,
          COALESCE(ss.stranding_score, 0.0) AS stranding_score
        FROM enhanced_interpretations ei
        JOIN papers p
          ON p.paper_id = ei.source_ref
        LEFT JOIN stranding_scores ss
          ON ss.run_id = ?
         AND ss.paper_id = ei.source_ref
        WHERE ei.run_id = ?
          AND ei.operator_family = 'stranded_qfin'
          AND ei.classification = 'STRANDED_QFIN_RESULT'
        ORDER BY ss.stranding_score DESC, ei.family_rank ASC, ei.source_ref ASC
        """,
        (stranding_run_id, interpretation_run_id),
    ).fetchall()


def fetch_diamond_source_rows(connection: sqlite3.Connection, interpretation_run_id: str, stranding_run_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
          di.batch_item_id,
          di.source_ref AS paper_id,
          di.shortlist_rank AS family_rank,
          di.classification,
          di.result_summary,
          di.first_test,
          di.instrument_assumed,
          di.modern_equivalent,
          di.why_stranded_or_unrealized,
          di.gap_to_close,
          di.confidence,
          COALESCE(p.published_at, 'unknown') AS published_at,
          COALESCE(p.primary_category, 'unknown') AS home_domain,
          COALESCE(ss.stranding_score, 0.0) AS stranding_score
        FROM diamond_interpretations di
        JOIN papers p
          ON p.paper_id = di.source_ref
        LEFT JOIN stranding_scores ss
          ON ss.run_id = ?
         AND ss.paper_id = di.source_ref
        WHERE di.run_id = ?
          AND di.lane_family = 'stranded_qfin'
          AND di.classification = 'STRANDED_QFIN_RESULT'
        ORDER BY ss.stranding_score DESC, di.shortlist_rank ASC, di.batch_item_id ASC
        """,
        (stranding_run_id, interpretation_run_id),
    ).fetchall()


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_stranded_result_ledger_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "stranded_result_ledger",
            "started",
            {
                "shortlist_run_id": args.shortlist_run_id,
                "interpretation_source": args.interpretation_source,
                "interpretation_run_id": args.interpretation_run_id,
                "stranding_run_id": args.stranding_run_id,
            },
        )
        if args.interpretation_source == "selective":
            source_rows = fetch_selective_source_rows(
                connection, args.interpretation_run_id, args.shortlist_run_id, args.stranding_run_id
            )
        elif args.interpretation_source == "enhanced_stranded":
            source_rows = fetch_enhanced_source_rows(connection, args.interpretation_run_id, args.stranding_run_id)
        else:
            source_rows = fetch_diamond_source_rows(connection, args.interpretation_run_id, args.stranding_run_id)

        # @context decision -- The ledger is intentionally narrower than the broader index: it only
        # publishes interpreted stranded q-fin paper rows. That preserves the ledger as a practical
        # execution surface instead of letting bridges and compositions swamp the q-fin result view.
        connection.execute("DELETE FROM stranded_result_ledger WHERE run_id = ?", (args.run_id,))

        rows = []
        for rank, row in enumerate(source_rows, start=1):
            ledger_row = {
                "publication_source_surface": (
                    "selective"
                    if args.interpretation_source == "selective"
                    else "enhanced_interpretation" if args.interpretation_source == "enhanced_stranded" else "diamond_interpretation"
                ),
                "publication_interpretation_run_id": args.interpretation_run_id,
                "publication_item_id": row["shortlist_id"] if args.interpretation_source == "selective" else row["batch_item_id"],
                "shortlist_id": row["shortlist_id"] if args.interpretation_source == "selective" else row["batch_item_id"],
                "paper_id": row["item_ref"] if args.interpretation_source == "selective" else row["paper_id"],
                "published_at": row["published_at"],
                "home_domain": row["home_domain"],
                "result_summary": row["result_summary"],
                "why_stranded_or_unrealized": row["why_stranded_or_unrealized"],
                "instrument_assumed": row["instrument_assumed"],
                "modern_equivalent": row["modern_equivalent"],
                "first_test": row["first_step"] if args.interpretation_source != "diamond_stranded" else row["first_test"],
                "gap_to_close": row["gap_to_close"],
                "priority_tier": priority_tier(float(row["stranding_score"] or 0.0), row["confidence"]),
                "relation_type": relation_type(row["classification"]),
                "ledger_rank": rank,
                "stranding_score": round(float(row["stranding_score"] or 0.0), 6),
                "confidence": row["confidence"],
                "rationale": {
                    "classification": row["classification"],
                    "publication_item_id": row["shortlist_id"] if args.interpretation_source == "selective" else row["batch_item_id"],
                },
            }
            connection.execute(
                """
                INSERT INTO stranded_result_ledger (
                  run_id,
                  shortlist_run_id,
                  interpretation_run_id,
                  shortlist_id,
                  publication_source_surface,
                  publication_interpretation_run_id,
                  publication_item_id,
                  paper_id,
                  published_at,
                  home_domain,
                  result_summary,
                  why_stranded_or_unrealized,
                  instrument_assumed,
                  modern_equivalent,
                  first_test,
                  gap_to_close,
                  priority_tier,
                  relation_type,
                  ledger_rank,
                  stranding_score,
                  confidence,
                  rationale_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.run_id,
                    args.shortlist_run_id,
                    args.interpretation_run_id,
                    ledger_row["shortlist_id"],
                    ledger_row["publication_source_surface"],
                    ledger_row["publication_interpretation_run_id"],
                    ledger_row["publication_item_id"],
                    ledger_row["paper_id"],
                    ledger_row["published_at"],
                    ledger_row["home_domain"],
                    ledger_row["result_summary"],
                    ledger_row["why_stranded_or_unrealized"],
                    ledger_row["instrument_assumed"],
                    ledger_row["modern_equivalent"],
                    ledger_row["first_test"],
                    ledger_row["gap_to_close"],
                    ledger_row["priority_tier"],
                    ledger_row["relation_type"],
                    ledger_row["ledger_rank"],
                    ledger_row["stranding_score"],
                    ledger_row["confidence"],
                    json.dumps(ledger_row["rationale"], sort_keys=True),
                ),
            )
            rows.append(ledger_row)

        jsonl_path = output_dir / "stranded_result_ledger.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown_path = output_dir / "stranded_result_ledger.md"
        markdown_path.write_text(render_markdown(rows), encoding="utf-8")

        metrics = {
            "run_id": args.run_id,
            "shortlist_run_id": args.shortlist_run_id,
            "interpretation_source": args.interpretation_source,
            "interpretation_run_id": args.interpretation_run_id,
            "stranding_run_id": args.stranding_run_id,
            "entry_count": len(rows),
            "counts_by_priority_tier": {
                tier: sum(1 for row in rows if row["priority_tier"] == tier)
                for tier in ("p1", "p2", "p3")
            },
            "top_ranked_paper_id": rows[0]["paper_id"] if rows else None,
            "top_ranked_publication_item_id": rows[0]["publication_item_id"] if rows else None,
        }
        metrics_path = output_dir / "stranded_result_ledger_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "stranded_result_ledger", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
