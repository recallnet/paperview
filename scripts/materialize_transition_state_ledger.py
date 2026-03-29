#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"

PATTERN_TO_PAIR_KEY = {
    "near_transition_queue_refill": "queue_value_passive_quoting__refill_lag_local_shock",
    "near_transition_auction_refill": "auction_parimutuel_design__refill_lag_local_shock",
    "near_transition_auction_queue": "auction_parimutuel_design__queue_value_passive_quoting",
    "near_transition_maker_queue": "maker_stress_inventory_retreat__queue_value_passive_quoting",
    "near_transition_parity_repair": "parity_propagation__refill_lag_local_shock",
}
POSITIVE_CLASSIFICATIONS = {
    "TRANSLATION_CANDIDATE": "adaptation",
    "COMPOSITIONAL_CANDIDATE": "calibration",
    "STRANDED_QFIN_RESULT": "direct",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize the canonical Transition-State Microstructure Ledger.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="transition-state-ledger-20260328")
    parser.add_argument("--candidate-run-id", default="transition-state-candidate-materialization-20260328")
    parser.add_argument("--shortlist-run-id", default="shortlist-materialization-20260328")
    parser.add_argument("--interpretation-source", choices=("selective", "enhanced_transition"), default="selective")
    parser.add_argument("--interpretation-run-id", default="selective-interpretation-ingestion-20260328")
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


def ensure_transition_state_ledger_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS transition_state_ledger (
          run_id TEXT NOT NULL,
          candidate_run_id TEXT NOT NULL,
          shortlist_run_id TEXT NOT NULL,
          interpretation_run_id TEXT NOT NULL,
          pattern_id TEXT NOT NULL,
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
          transition_state_score REAL NOT NULL,
          confidence TEXT NOT NULL,
          rationale_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, pattern_id),
          FOREIGN KEY (pattern_id) REFERENCES agitator_patterns(pattern_id) ON DELETE CASCADE,
          FOREIGN KEY (shortlist_run_id, shortlist_id) REFERENCES shortlist_items(run_id, shortlist_id) ON DELETE CASCADE,
          FOREIGN KEY (interpretation_run_id, shortlist_id) REFERENCES selective_interpretations(run_id, shortlist_id) ON DELETE CASCADE,
          FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
        )
        """
    )
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(transition_state_ledger)").fetchall()
    }
    if "publication_source_surface" not in columns:
        connection.execute(
            """
            ALTER TABLE transition_state_ledger
            ADD COLUMN publication_source_surface TEXT NOT NULL DEFAULT 'selective'
            """
        )
    if "publication_interpretation_run_id" not in columns:
        connection.execute(
            """
            ALTER TABLE transition_state_ledger
            ADD COLUMN publication_interpretation_run_id TEXT
            """
        )
    if "publication_item_id" not in columns:
        connection.execute(
            """
            ALTER TABLE transition_state_ledger
            ADD COLUMN publication_item_id TEXT
            """
        )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_transition_state_ledger_run_rank
        ON transition_state_ledger (run_id, ledger_rank)
        """
    )


def priority_tier(transition_state_score: float, confidence: str) -> str:
    confidence = confidence.lower()
    if transition_state_score >= 0.65 and confidence in {"high", "medium"}:
        return "p1"
    if transition_state_score >= 0.45:
        return "p2"
    return "p3"


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Transition-State Microstructure Ledger",
        "",
        f"- entry count: `{len(rows)}`",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['ledger_rank']}. {row['pattern_label']}",
                "",
                f"- publication item id: `{row['publication_item_id']}`",
                f"- publication source surface: `{row['publication_source_surface']}`",
                f"- shortlist id: `{row['shortlist_id']}`",
                f"- representative paper: `{row['paper_id']}`",
                f"- date: `{row['published_at']}`",
                f"- home domain: `{row['home_domain']}`",
                f"- priority tier: `{row['priority_tier']}`",
                f"- relation type: `{row['relation_type']}`",
                f"- transition-state score: `{row['transition_state_score']}`",
                f"- confidence: `{row['confidence']}`",
                "",
                f"Result: {row['result_summary']}",
                "",
                f"Why unrealized: {row['why_stranded_or_unrealized']}",
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


def fetch_best_interpretation_by_pair(connection: sqlite3.Connection, shortlist_run_id: str, interpretation_run_id: str) -> dict[str, sqlite3.Row]:
    rows = connection.execute(
        """
        SELECT
          si.shortlist_id,
          si.shortlist_rank,
          si.packet_kind,
          si.packet_item_ref,
          interp.classification,
          interp.result_summary,
          interp.first_step,
          interp.instrument_assumed,
          interp.modern_equivalent,
          interp.why_stranded_or_unrealized,
          interp.gap_to_close,
          interp.confidence
        FROM selective_interpretations interp
        JOIN shortlist_items si
          ON si.run_id = interp.shortlist_run_id
         AND si.shortlist_id = interp.shortlist_id
        WHERE interp.run_id = ?
          AND si.run_id = ?
        ORDER BY si.shortlist_rank ASC, si.shortlist_id ASC
        """,
        (interpretation_run_id, shortlist_run_id),
    ).fetchall()
    best_by_pair: dict[str, sqlite3.Row] = {}
    for row in rows:
        if row["classification"] not in POSITIVE_CLASSIFICATIONS:
            continue
        pair_key = row["packet_item_ref"]
        current = best_by_pair.get(pair_key)
        if current is None or int(row["shortlist_rank"]) < int(current["shortlist_rank"]):
            best_by_pair[pair_key] = row
    return best_by_pair


def fetch_best_enhanced_transition_by_pattern(connection: sqlite3.Connection, interpretation_run_id: str) -> dict[str, sqlite3.Row]:
    rows = connection.execute(
        """
        SELECT
          batch_item_id,
          source_ref,
          family_rank,
          classification,
          result_summary,
          first_step,
          instrument_assumed,
          modern_equivalent,
          why_stranded_or_unrealized,
          gap_to_close,
          confidence
        FROM enhanced_interpretations
        WHERE run_id = ?
          AND operator_family = 'transition_state'
        ORDER BY family_rank ASC, batch_item_id ASC
        """,
        (interpretation_run_id,),
    ).fetchall()
    best_by_pattern: dict[str, sqlite3.Row] = {}
    for row in rows:
        if row["classification"] not in POSITIVE_CLASSIFICATIONS:
            continue
        pattern_id = row["source_ref"]
        current = best_by_pattern.get(pattern_id)
        if current is None or int(row["family_rank"]) < int(current["family_rank"]):
            best_by_pattern[pattern_id] = row
    return best_by_pattern


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_transition_state_ledger_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "transition_state_ledger",
            "started",
            {
                "candidate_run_id": args.candidate_run_id,
                "shortlist_run_id": args.shortlist_run_id,
                "interpretation_source": args.interpretation_source,
                "interpretation_run_id": args.interpretation_run_id,
            },
        )

        if args.interpretation_source == "selective":
            best_by_pair = fetch_best_interpretation_by_pair(connection, args.shortlist_run_id, args.interpretation_run_id)
            best_by_pattern = {}
        else:
            best_by_pair = {}
            best_by_pattern = fetch_best_enhanced_transition_by_pattern(connection, args.interpretation_run_id)
        connection.execute("DELETE FROM transition_state_ledger WHERE run_id = ?", (args.run_id,))

        rows = connection.execute(
            """
            SELECT
              tc.pattern_id,
              tc.paper_id,
              tc.transition_state_rank,
              tc.transition_state_candidate_score,
              tc.rationale_json,
              ap.label AS pattern_label,
              p.published_at,
              p.primary_category
            FROM transition_state_candidates tc
            JOIN agitator_patterns ap
              ON ap.pattern_id = tc.pattern_id
            JOIN papers p
              ON p.paper_id = tc.paper_id
            WHERE tc.run_id = ?
              AND tc.transition_state_rank = 1
            ORDER BY tc.transition_state_candidate_score DESC, tc.pattern_id ASC
            """,
            (args.candidate_run_id,),
        ).fetchall()

        ledger_rows = []
        for row in rows:
            rationale = json.loads(row["rationale_json"] or "{}")
            if args.interpretation_source == "selective":
                pair_key = PATTERN_TO_PAIR_KEY.get(row["pattern_id"])
                if not pair_key:
                    continue
                interpretation = best_by_pair.get(pair_key)
                if interpretation is None:
                    continue
                publication_source_surface = "selective"
                publication_item_id = interpretation["shortlist_id"]
                shortlist_id = interpretation["shortlist_id"]
                rationale_keys = {
                    "classification": interpretation["classification"],
                    "packet_kind": interpretation["packet_kind"],
                    "pair_key": pair_key,
                }
            else:
                interpretation = best_by_pattern.get(row["pattern_id"])
                if interpretation is None:
                    continue
                publication_source_surface = "enhanced_interpretation"
                publication_item_id = interpretation["batch_item_id"]
                shortlist_id = interpretation["batch_item_id"]
                # @context decision -- The S24 rematerialized transition ledger stays narrower than
                # the full S19 candidate queue: it only publishes patterns that already survived the
                # explicit S23 enhanced transition interpretation path. This preserves the ledger as
                # a publication surface over accepted transition-state theses rather than silently
                # promoting raw candidate rows.
                rationale_keys = {
                    "classification": interpretation["classification"],
                    "operator_family": "transition_state",
                    "pattern_id": row["pattern_id"],
                }
            # @context decision -- Transition-state publication always binds accepted interpretation
            # text to the live S19 representative-paper score for the same pattern. The publication
            # row is invalid if either side is missing, because otherwise the ledger would drift away
            # from the canonical operator evidence that selected the paper in the first place.
            ledger_rows.append(
                {
                    "pattern_id": row["pattern_id"],
                    "pattern_label": row["pattern_label"],
                    "publication_source_surface": publication_source_surface,
                    "publication_interpretation_run_id": args.interpretation_run_id,
                    "publication_item_id": publication_item_id,
                    "shortlist_id": shortlist_id,
                    "paper_id": row["paper_id"],
                    "published_at": row["published_at"] or "unknown",
                    "home_domain": row["primary_category"] or "unknown",
                    "result_summary": interpretation["result_summary"],
                    "why_stranded_or_unrealized": interpretation["why_stranded_or_unrealized"],
                    "instrument_assumed": interpretation["instrument_assumed"],
                    "modern_equivalent": interpretation["modern_equivalent"],
                    "first_test": interpretation["first_step"],
                    "gap_to_close": interpretation["gap_to_close"],
                    "priority_tier": priority_tier(float(row["transition_state_candidate_score"] or 0.0), interpretation["confidence"]),
                    "relation_type": POSITIVE_CLASSIFICATIONS[interpretation["classification"]],
                    "transition_state_score": round(float(row["transition_state_candidate_score"] or 0.0), 6),
                    "confidence": interpretation["confidence"],
                    "rationale": {
                        **rationale_keys,
                        "publication_item_id": publication_item_id,
                        "transition_state_rank": int(row["transition_state_rank"]),
                        "pattern_label": row["pattern_label"],
                        "feature_snapshot": rationale,
                    },
                }
            )

        ledger_rows.sort(key=lambda item: (-item["transition_state_score"], item["pattern_id"]))

        for rank, row in enumerate(ledger_rows, start=1):
            row["ledger_rank"] = rank
            connection.execute(
                """
                INSERT INTO transition_state_ledger (
                  run_id,
                  candidate_run_id,
                  shortlist_run_id,
                  interpretation_run_id,
                  pattern_id,
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
                  transition_state_score,
                  confidence,
                  rationale_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.run_id,
                    args.candidate_run_id,
                    args.shortlist_run_id,
                    args.interpretation_run_id,
                    row["pattern_id"],
                    row["shortlist_id"],
                    row["publication_source_surface"],
                    row["publication_interpretation_run_id"],
                    row["publication_item_id"],
                    row["paper_id"],
                    row["published_at"],
                    row["home_domain"],
                    row["result_summary"],
                    row["why_stranded_or_unrealized"],
                    row["instrument_assumed"],
                    row["modern_equivalent"],
                    row["first_test"],
                    row["gap_to_close"],
                    row["priority_tier"],
                    row["relation_type"],
                    row["ledger_rank"],
                    row["transition_state_score"],
                    row["confidence"],
                    json.dumps(row["rationale"], sort_keys=True),
                ),
            )

        jsonl_path = output_dir / "transition_state_ledger.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in ledger_rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown_path = output_dir / "transition_state_ledger.md"
        markdown_path.write_text(render_markdown(ledger_rows), encoding="utf-8")

        metrics = {
            "run_id": args.run_id,
            "candidate_run_id": args.candidate_run_id,
            "shortlist_run_id": args.shortlist_run_id,
            "interpretation_source": args.interpretation_source,
            "interpretation_run_id": args.interpretation_run_id,
            "entry_count": len(ledger_rows),
            "counts_by_priority_tier": {
                tier: sum(1 for row in ledger_rows if row["priority_tier"] == tier)
                for tier in ("p1", "p2", "p3")
            },
            "top_ranked_pattern_id": ledger_rows[0]["pattern_id"] if ledger_rows else None,
            "top_ranked_publication_item_id": ledger_rows[0]["publication_item_id"] if ledger_rows else None,
        }
        metrics_path = output_dir / "transition_state_ledger_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "transition_state_ledger", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
