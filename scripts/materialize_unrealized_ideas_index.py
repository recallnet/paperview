#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"

POSITIVE_CLASSIFICATIONS = {
    "TRANSLATION_CANDIDATE": 0.35,
    "COMPOSITIONAL_CANDIDATE": 0.3,
    "STRANDED_QFIN_RESULT": 0.25,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize the canonical Unrealized Ideas Index.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="unrealized-ideas-index-20260328")
    parser.add_argument("--shortlist-run-id", default="shortlist-materialization-20260328")
    parser.add_argument("--interpretation-source", choices=("selective", "enhanced_bridge", "enhanced_broadened", "diamond"), default="selective")
    parser.add_argument("--interpretation-run-id", default="selective-interpretation-ingestion-20260328")
    parser.add_argument("--validation-interpretation-run-id", default="selective-interpretation-ingestion-20260328")
    parser.add_argument("--holdout-run-id", default="holdout-echo-materialization-20260328")
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--max-realized-market-leakage", type=float, default=0.999999)
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


def ensure_unrealized_idea_index_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS unrealized_idea_index (
          run_id TEXT NOT NULL,
          shortlist_run_id TEXT NOT NULL,
          interpretation_run_id TEXT NOT NULL,
          holdout_run_id TEXT NOT NULL,
          shortlist_id TEXT NOT NULL,
          publication_source_surface TEXT NOT NULL DEFAULT 'selective',
          publication_interpretation_run_id TEXT,
          publication_item_id TEXT,
          item_type TEXT NOT NULL,
          item_ref TEXT NOT NULL,
          title TEXT NOT NULL,
          classification TEXT NOT NULL,
          index_rank INTEGER NOT NULL,
          index_score REAL NOT NULL,
          domain_far_score REAL NOT NULL,
          holdout_echo_score REAL NOT NULL,
          realized_market_leakage_score REAL NOT NULL,
          rationale_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, shortlist_id),
          FOREIGN KEY (shortlist_run_id, shortlist_id) REFERENCES shortlist_items(run_id, shortlist_id) ON DELETE CASCADE,
          FOREIGN KEY (interpretation_run_id, shortlist_id) REFERENCES selective_interpretations(run_id, shortlist_id) ON DELETE CASCADE
        )
        """
    )
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(unrealized_idea_index)").fetchall()
    }
    if "publication_source_surface" not in columns:
        connection.execute(
            """
            ALTER TABLE unrealized_idea_index
            ADD COLUMN publication_source_surface TEXT NOT NULL DEFAULT 'selective'
            """
        )
    if "publication_interpretation_run_id" not in columns:
        connection.execute(
            """
            ALTER TABLE unrealized_idea_index
            ADD COLUMN publication_interpretation_run_id TEXT
            """
        )
    if "publication_item_id" not in columns:
        connection.execute(
            """
            ALTER TABLE unrealized_idea_index
            ADD COLUMN publication_item_id TEXT
            """
        )


def resolve_source_paper_ids(summary_json: str, echoes: list[sqlite3.Row], item_type: str, item_ref: str) -> list[str]:
    summary = json.loads(summary_json or "{}")
    source_ids = []
    if echoes:
        try:
            source_ids = json.loads(echoes[0]["source_paper_ids_json"] or "[]")
        except json.JSONDecodeError:
            source_ids = []
    if not source_ids:
        source_ids = summary.get("representative_papers", [])
    if not source_ids and item_type == "paper":
        source_ids = [item_ref]
    # @context requirement -- Source-paper resolution must follow the same representative-paper
    # contract used by packets and holdout echoes. If this drifts, the publication-stage index will
    # silently rank a different evidence base than the validated shortlist and holdout stages.
    deduped = []
    seen = set()
    for paper_id in source_ids:
        if paper_id in seen:
            continue
        deduped.append(paper_id)
        seen.add(paper_id)
    return deduped


def realized_market_leakage(connection: sqlite3.Connection, membership_run_id: str, source_paper_ids: list[str]) -> float:
    if not source_paper_ids:
        return 0.0
    placeholders = ",".join("?" for _ in source_paper_ids)
    rows = connection.execute(
        f"""
        SELECT COUNT(*) AS realized_count
        FROM corpus_memberships
        WHERE run_id = ?
          AND corpus_id = 'realized_market'
          AND paper_id IN ({placeholders})
        """,
        (membership_run_id, *source_paper_ids),
    ).fetchone()
    realized_count = int(rows["realized_count"] or 0)
    return round(realized_count / len(source_paper_ids), 6)


def shortlist_rank_score(shortlist_rank: int) -> float:
    if shortlist_rank <= 0:
        return 0.0
    return round(1.0 / shortlist_rank, 6)


def index_score(shortlist_rank: int, classification: str, holdout_echo_score: float, leakage_score: float) -> float:
    domain_far_score = max(0.0, 1.0 - leakage_score)
    classification_bonus = POSITIVE_CLASSIFICATIONS.get(classification, 0.0)
    # @context decision -- The first index layer ranks only over canonical shortlist, interpretation,
    # and validation evidence. Using shortlist rank plus holdout echo and domain-far reward keeps the
    # publication surface aligned with map-first discovery instead of inventing a parallel score.
    return round(
        shortlist_rank_score(shortlist_rank) * 0.25
        + classification_bonus
        + holdout_echo_score * 0.5
        + domain_far_score * 0.75,
        6,
    )


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Unrealized Ideas Index",
        "",
        f"- entry count: `{len(rows)}`",
        "",
    ]
    for row in rows:
        echoes = row["rationale"]["top_holdout_echoes"]
        lines.extend(
            [
                f"## {row['index_rank']}. {row['title']}",
                "",
                f"- publication item id: `{row['publication_item_id']}`",
                f"- publication source surface: `{row['publication_source_surface']}`",
                f"- shortlist id: `{row['shortlist_id']}`",
                f"- classification: `{row['classification']}`",
                f"- item type: `{row['item_type']}`",
                f"- index score: `{row['index_score']}`",
                f"- domain-far score: `{row['domain_far_score']}`",
                f"- holdout echo score: `{row['holdout_echo_score']}`",
                f"- realized-market leakage: `{row['realized_market_leakage_score']}`",
                f"- confidence: `{row['confidence']}`",
                "",
                f"Result: {row['result_summary']}",
                "",
                f"Why unrealized: {row['why_stranded_or_unrealized']}",
                "",
                f"Modern equivalent: {row['modern_equivalent']}",
                "",
                f"First step: {row['first_step']}",
                "",
                "Top holdout echoes:",
            ]
        )
        for echo in echoes:
            lines.append(f"- `{echo['paper_id']}` | {echo['title']} | echo `{echo['echo_score']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def fetch_selective_source_rows(connection: sqlite3.Connection, interpretation_run_id: str, shortlist_run_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
          si.shortlist_id,
          si.item_type,
          si.item_ref,
          si.shortlist_rank,
          si.score AS shortlist_score,
          rp.title,
          rp.summary_json,
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
        JOIN review_packets rp
          ON rp.run_id = si.packet_run_id
         AND rp.packet_kind = si.packet_kind
         AND rp.item_ref = si.packet_item_ref
        WHERE interp.run_id = ?
          AND si.run_id = ?
        ORDER BY si.shortlist_rank ASC, si.shortlist_id ASC
        """,
        (interpretation_run_id, shortlist_run_id),
    ).fetchall()


def fetch_enhanced_bridge_source_rows(connection: sqlite3.Connection, interpretation_run_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
          ei.batch_item_id,
          ei.source_ref AS pair_key,
          ei.family_rank,
          ei.source_score,
          rp.title,
          rp.summary_json,
          ei.classification,
          ei.result_summary,
          ei.first_step,
          ei.instrument_assumed,
          ei.modern_equivalent,
          ei.why_stranded_or_unrealized,
          ei.gap_to_close,
          ei.confidence
        FROM enhanced_interpretations ei
        JOIN review_packets rp
          ON rp.run_id = ei.source_run_id
         AND rp.packet_kind = 'bridge'
         AND rp.item_ref = ei.source_ref
        WHERE ei.run_id = ?
          AND ei.operator_family = 'bridge'
        ORDER BY ei.family_rank ASC, ei.batch_item_id ASC
        """,
        (interpretation_run_id,),
    ).fetchall()


def fetch_enhanced_broadened_source_rows(connection: sqlite3.Connection, interpretation_run_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
          ei.batch_item_id,
          ei.source_ref AS pair_key,
          ei.family_rank,
          ei.source_score,
          ei.packet_title AS title,
          ei.classification,
          ei.result_summary,
          ei.first_step,
          ei.instrument_assumed,
          ei.modern_equivalent,
          ei.why_stranded_or_unrealized,
          ei.gap_to_close,
          ei.confidence,
          ei.operator_family,
          ei.source_kind,
          ei.source_run_id
        FROM enhanced_interpretations ei
        WHERE ei.run_id = ?
          AND ei.operator_family NOT IN ('stranded_qfin', 'transition_state')
          AND ei.classification IN ('TRANSLATION_CANDIDATE', 'COMPOSITIONAL_CANDIDATE')
        ORDER BY ei.family_rank ASC, ei.operator_family ASC, ei.batch_item_id ASC
        """,
        (interpretation_run_id,),
    ).fetchall()


def fetch_diamond_source_rows(connection: sqlite3.Connection, interpretation_run_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
          di.batch_item_id,
          di.lane_family,
          di.operator_family,
          di.source_kind,
          di.source_run_id,
          di.source_ref,
          di.shortlist_rank,
          di.source_score,
          di.diamond_score,
          di.packet_title AS title,
          di.classification,
          di.result_summary,
          di.first_test,
          di.instrument_assumed,
          di.modern_equivalent,
          di.why_stranded_or_unrealized,
          di.gap_to_close,
          di.confidence
        FROM diamond_interpretations di
        WHERE di.run_id = ?
          AND di.lane_family NOT IN ('stranded_qfin', 'transition_state')
          AND di.classification IN ('TRANSLATION_CANDIDATE', 'COMPOSITIONAL_CANDIDATE')
        ORDER BY di.shortlist_rank ASC, di.batch_item_id ASC
        """,
        (interpretation_run_id,),
    ).fetchall()


def fetch_pair_representative_papers(
    connection: sqlite3.Connection,
    source_kind: str,
    source_run_id: str,
    pair_key: str,
) -> list[str]:
    anchors = pair_key.split("__", 1)
    if len(anchors) != 2:
        return []
    source_anchor_id, target_anchor_id = anchors
    if source_kind == "bridge_candidate_pair":
        table_name = "bridge_candidates"
        score_column = "bridge_score"
        rank_column = "bridge_rank"
    elif source_kind == "composition_candidate_pair":
        table_name = "composition_candidates"
        score_column = "composition_score"
        rank_column = "composition_rank"
    else:
        return []
    rows = connection.execute(
        f"""
        SELECT paper_id
        FROM {table_name}
        WHERE run_id = ?
          AND source_anchor_id = ?
          AND target_anchor_id = ?
        ORDER BY {score_column} DESC, {rank_column} ASC, paper_id ASC
        LIMIT 5
        """,
        (source_run_id, source_anchor_id, target_anchor_id),
    ).fetchall()
    return [row["paper_id"] for row in rows]


def resolve_diamond_source_paper_ids(connection: sqlite3.Connection, row: sqlite3.Row) -> list[str]:
    if row["source_kind"] in {"bridge_candidate_pair", "composition_candidate_pair"}:
        return fetch_pair_representative_papers(
            connection,
            row["source_kind"],
            row["source_run_id"],
            row["source_ref"],
        )
    if row["source_kind"] in {
        "transition_state_candidate",
        "state_graph_candidate",
        "participant_pathology_candidate",
        "stranded_resurfacing_candidate",
    }:
        return [row["source_ref"]]
    return []


def fetch_validation_echoes_by_pair(
    connection: sqlite3.Connection,
    shortlist_run_id: str,
    validation_interpretation_run_id: str,
    holdout_run_id: str,
    pair_key: str,
) -> tuple[sqlite3.Row | None, list[sqlite3.Row]]:
    rows = connection.execute(
        """
        SELECT
          si.shortlist_id,
          si.shortlist_rank,
          he.holdout_paper_id,
          he.echo_score,
          he.echo_rank,
          he.source_paper_ids_json,
          COALESCE(p.title, he.holdout_paper_id) AS holdout_title
        FROM shortlist_items si
        JOIN selective_interpretations interp
          ON interp.shortlist_run_id = si.run_id
         AND interp.shortlist_id = si.shortlist_id
        JOIN holdout_echoes he
          ON he.interpretation_run_id = interp.run_id
         AND he.shortlist_id = interp.shortlist_id
        JOIN papers p
          ON p.paper_id = he.holdout_paper_id
        WHERE si.run_id = ?
          AND interp.run_id = ?
          AND he.run_id = ?
          AND si.packet_item_ref = ?
        ORDER BY si.shortlist_rank ASC, he.echo_rank ASC, he.holdout_paper_id ASC
        """,
        (shortlist_run_id, validation_interpretation_run_id, holdout_run_id, pair_key),
    ).fetchall()
    if not rows:
        return None, []
    return rows[0], rows


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_unrealized_idea_index_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "unrealized_ideas_index",
            "started",
            {
                "shortlist_run_id": args.shortlist_run_id,
                "interpretation_source": args.interpretation_source,
                "interpretation_run_id": args.interpretation_run_id,
                "validation_interpretation_run_id": args.validation_interpretation_run_id,
                "holdout_run_id": args.holdout_run_id,
                "membership_run_id": args.membership_run_id,
                "max_realized_market_leakage": args.max_realized_market_leakage,
            },
        )

        ranked_rows = []
        if args.interpretation_source == "selective":
            source_rows = fetch_selective_source_rows(connection, args.interpretation_run_id, args.shortlist_run_id)
            for row in source_rows:
                classification = row["classification"]
                if classification not in POSITIVE_CLASSIFICATIONS:
                    continue
                validation_row, echoes = fetch_validation_echoes_by_pair(
                    connection,
                    args.shortlist_run_id,
                    args.interpretation_run_id,
                    args.holdout_run_id,
                    row["item_ref"],
                )
                if not echoes:
                    continue

                source_paper_ids = resolve_source_paper_ids(row["summary_json"], echoes, row["item_type"], row["item_ref"])
                leakage_score = realized_market_leakage(connection, args.membership_run_id, source_paper_ids)
                domain_far_score = round(max(0.0, 1.0 - leakage_score), 6)
                # @context risk -- Fully leaked rows are still useful upstream as canonical shortlist and
                # interpretation evidence, but publishing them into the Unrealized Ideas Index would
                # break the product contract: this surface is supposed to be mechanism-close and domain-far.
                if leakage_score >= float(args.max_realized_market_leakage):
                    continue
                top_holdout_echoes = [
                    {
                        "paper_id": echo["holdout_paper_id"],
                        "title": echo["holdout_title"],
                        "echo_score": round(float(echo["echo_score"] or 0.0), 6),
                    }
                    for echo in echoes[:3]
                ]
                holdout_echo_score = round(
                    sum(float(item["echo_score"]) for item in top_holdout_echoes) / len(top_holdout_echoes),
                    6,
                )
                ranked_rows.append(
                    {
                        "publication_source_surface": "selective",
                        "publication_interpretation_run_id": args.interpretation_run_id,
                        "publication_item_id": row["shortlist_id"],
                        "shortlist_id": row["shortlist_id"],
                        "item_type": row["item_type"],
                        "item_ref": row["item_ref"],
                        "title": row["title"],
                        "classification": classification,
                        "shortlist_rank": int(row["shortlist_rank"]),
                        "shortlist_score": round(float(row["shortlist_score"] or 0.0), 6),
                        "holdout_echo_score": holdout_echo_score,
                        "realized_market_leakage_score": leakage_score,
                        "domain_far_score": domain_far_score,
                        "result_summary": row["result_summary"],
                        "first_step": row["first_step"],
                        "instrument_assumed": row["instrument_assumed"],
                        "modern_equivalent": row["modern_equivalent"],
                        "why_stranded_or_unrealized": row["why_stranded_or_unrealized"],
                        "gap_to_close": row["gap_to_close"],
                        "confidence": row["confidence"],
                        "rationale": {
                            "validation_shortlist_id": validation_row["shortlist_id"] if validation_row else row["shortlist_id"],
                            "shortlist_rank_score": shortlist_rank_score(int(row["shortlist_rank"])),
                            "classification_bonus": POSITIVE_CLASSIFICATIONS[classification],
                            "source_paper_ids": source_paper_ids,
                            "top_holdout_echoes": top_holdout_echoes,
                        },
                    }
                )
        elif args.interpretation_source == "enhanced_bridge":
            source_rows = fetch_enhanced_bridge_source_rows(connection, args.interpretation_run_id)
            for row in source_rows:
                classification = row["classification"]
                if classification not in POSITIVE_CLASSIFICATIONS:
                    continue
                validation_row, echoes = fetch_validation_echoes_by_pair(
                    connection,
                    args.shortlist_run_id,
                    args.validation_interpretation_run_id,
                    args.holdout_run_id,
                    row["pair_key"],
                )
                if not echoes or validation_row is None:
                    continue
                # @context decision -- The first S24 rematerialized index slice publishes enhanced
                # bridge interpretations only when they can still be tied back to the existing
                # shortlist-backed holdout echo surface by shared pairing key. That keeps the new
                # publication rows truthfully grounded in real validation evidence while S24
                # incrementally upgrades the downstream publication surfaces.
                source_paper_ids = resolve_source_paper_ids(row["summary_json"], echoes, "bridge", row["pair_key"])
                leakage_score = realized_market_leakage(connection, args.membership_run_id, source_paper_ids)
                domain_far_score = round(max(0.0, 1.0 - leakage_score), 6)
                if leakage_score >= float(args.max_realized_market_leakage):
                    continue
                top_holdout_echoes = [
                    {
                        "paper_id": echo["holdout_paper_id"],
                        "title": echo["holdout_title"],
                        "echo_score": round(float(echo["echo_score"] or 0.0), 6),
                    }
                    for echo in echoes[:3]
                ]
                holdout_echo_score = round(
                    sum(float(item["echo_score"]) for item in top_holdout_echoes) / len(top_holdout_echoes),
                    6,
                )
                ranked_rows.append(
                    {
                        "publication_source_surface": "enhanced_interpretation",
                        "publication_interpretation_run_id": args.interpretation_run_id,
                        "publication_item_id": row["batch_item_id"],
                        "shortlist_id": validation_row["shortlist_id"],
                        "item_type": "bridge",
                        "item_ref": row["pair_key"],
                        "title": row["title"],
                        "classification": classification,
                        "shortlist_rank": int(row["family_rank"]),
                        "shortlist_score": round(float(row["source_score"] or 0.0), 6),
                        "holdout_echo_score": holdout_echo_score,
                        "realized_market_leakage_score": leakage_score,
                        "domain_far_score": domain_far_score,
                        "result_summary": row["result_summary"],
                        "first_step": row["first_step"],
                        "instrument_assumed": row["instrument_assumed"],
                        "modern_equivalent": row["modern_equivalent"],
                        "why_stranded_or_unrealized": row["why_stranded_or_unrealized"],
                        "gap_to_close": row["gap_to_close"],
                        "confidence": row["confidence"],
                        "rationale": {
                            "validation_shortlist_id": validation_row["shortlist_id"],
                            "shortlist_rank_score": shortlist_rank_score(int(row["family_rank"])),
                            "classification_bonus": POSITIVE_CLASSIFICATIONS[classification],
                            "source_paper_ids": source_paper_ids,
                            "top_holdout_echoes": top_holdout_echoes,
                        },
                    }
                )
        elif args.interpretation_source == "enhanced_broadened":
            source_rows = fetch_enhanced_broadened_source_rows(connection, args.interpretation_run_id)
            for row in source_rows:
                classification = row["classification"]
                if classification not in POSITIVE_CLASSIFICATIONS:
                    continue
                source_paper_ids = fetch_pair_representative_papers(
                    connection,
                    row["source_kind"],
                    row["source_run_id"],
                    row["pair_key"],
                )
                leakage_score = realized_market_leakage(connection, args.membership_run_id, source_paper_ids)
                domain_far_score = round(max(0.0, 1.0 - leakage_score), 6)
                if leakage_score >= float(args.max_realized_market_leakage):
                    continue
                # @context decision -- The broadened S27 index publishes new lane findings even when
                # they do not map back to the old shortlist-backed holdout surface. Otherwise the
                # publication layer would silently erase the early-market broadening pass and keep the
                # index centered on the legacy validated bridge slice.
                ranked_rows.append(
                    {
                        "publication_source_surface": "enhanced_interpretation",
                        "publication_interpretation_run_id": args.interpretation_run_id,
                        "publication_item_id": row["batch_item_id"],
                        "shortlist_id": row["batch_item_id"],
                        "item_type": row["operator_family"],
                        "item_ref": row["pair_key"],
                        "title": row["title"],
                        "classification": classification,
                        "shortlist_rank": int(row["family_rank"]),
                        "shortlist_score": round(float(row["source_score"] or 0.0), 6),
                        "holdout_echo_score": 0.0,
                        "realized_market_leakage_score": leakage_score,
                        "domain_far_score": domain_far_score,
                        "result_summary": row["result_summary"],
                        "first_step": row["first_step"],
                        "instrument_assumed": row["instrument_assumed"],
                        "modern_equivalent": row["modern_equivalent"],
                        "why_stranded_or_unrealized": row["why_stranded_or_unrealized"],
                        "gap_to_close": row["gap_to_close"],
                        "confidence": row["confidence"],
                        "rationale": {
                            "lane_family": row["operator_family"],
                            "shortlist_rank_score": shortlist_rank_score(int(row["family_rank"])),
                            "classification_bonus": POSITIVE_CLASSIFICATIONS[classification],
                            "source_paper_ids": source_paper_ids,
                            "top_holdout_echoes": [],
                        },
                    }
                )
        else:
            source_rows = fetch_diamond_source_rows(connection, args.interpretation_run_id)
            for row in source_rows:
                classification = row["classification"]
                if classification not in POSITIVE_CLASSIFICATIONS:
                    continue
                source_paper_ids = resolve_diamond_source_paper_ids(connection, row)
                leakage_score = realized_market_leakage(connection, args.membership_run_id, source_paper_ids)
                domain_far_score = round(max(0.0, 1.0 - leakage_score), 6)
                if leakage_score >= float(args.max_realized_market_leakage):
                    continue
                ranked_rows.append(
                    {
                        "publication_source_surface": "diamond_interpretation",
                        "publication_interpretation_run_id": args.interpretation_run_id,
                        "publication_item_id": row["batch_item_id"],
                        "shortlist_id": row["batch_item_id"],
                        "item_type": row["lane_family"],
                        "item_ref": row["source_ref"],
                        "title": row["title"],
                        "classification": classification,
                        "shortlist_rank": int(row["shortlist_rank"]),
                        "shortlist_score": round(float(row["diamond_score"] or row["source_score"] or 0.0), 6),
                        "holdout_echo_score": 0.0,
                        "realized_market_leakage_score": leakage_score,
                        "domain_far_score": domain_far_score,
                        "result_summary": row["result_summary"],
                        "first_step": row["first_test"],
                        "instrument_assumed": row["instrument_assumed"],
                        "modern_equivalent": row["modern_equivalent"],
                        "why_stranded_or_unrealized": row["why_stranded_or_unrealized"],
                        "gap_to_close": row["gap_to_close"],
                        "confidence": row["confidence"],
                        "rationale": {
                            "lane_family": row["lane_family"],
                            "operator_family": row["operator_family"],
                            "shortlist_rank_score": shortlist_rank_score(int(row["shortlist_rank"])),
                            "classification_bonus": POSITIVE_CLASSIFICATIONS[classification],
                            "source_paper_ids": source_paper_ids,
                            "top_holdout_echoes": [],
                        },
                    }
                )

        ranked_rows.sort(
            key=lambda item: (
                -index_score(
                    item["shortlist_rank"],
                    item["classification"],
                    item["holdout_echo_score"],
                    item["realized_market_leakage_score"],
                ),
                -item["domain_far_score"],
                -item["holdout_echo_score"],
                item["shortlist_id"],
            )
        )

        connection.execute("DELETE FROM unrealized_idea_index WHERE run_id = ?", (args.run_id,))

        jsonl_rows = []
        for rank, item in enumerate(ranked_rows, start=1):
            item["index_rank"] = rank
            item["index_score"] = index_score(
                item["shortlist_rank"],
                item["classification"],
                item["holdout_echo_score"],
                item["realized_market_leakage_score"],
            )
            connection.execute(
                """
                INSERT INTO unrealized_idea_index (
                  run_id,
                  shortlist_run_id,
                  interpretation_run_id,
                  holdout_run_id,
                  shortlist_id,
                  publication_source_surface,
                  publication_interpretation_run_id,
                  publication_item_id,
                  item_type,
                  item_ref,
                  title,
                  classification,
                  index_rank,
                  index_score,
                  domain_far_score,
                  holdout_echo_score,
                  realized_market_leakage_score,
                  rationale_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.run_id,
                    args.shortlist_run_id,
                    args.validation_interpretation_run_id if args.interpretation_source == "enhanced_bridge" else args.interpretation_run_id,
                    args.holdout_run_id,
                    item["shortlist_id"],
                    item["publication_source_surface"],
                    item["publication_interpretation_run_id"],
                    item["publication_item_id"],
                    item["item_type"],
                    item["item_ref"],
                    item["title"],
                    item["classification"],
                    rank,
                    item["index_score"],
                    item["domain_far_score"],
                    item["holdout_echo_score"],
                    item["realized_market_leakage_score"],
                    json.dumps(item["rationale"], sort_keys=True),
                ),
            )
            jsonl_rows.append(item)

        jsonl_path = output_dir / "unrealized_ideas_index.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for item in jsonl_rows:
                handle.write(json.dumps(item, sort_keys=True) + "\n")

        markdown_path = output_dir / "unrealized_ideas_index.md"
        markdown_path.write_text(render_markdown(jsonl_rows), encoding="utf-8")

        metrics = {
            "run_id": args.run_id,
            "shortlist_run_id": args.shortlist_run_id,
            "interpretation_run_id": args.interpretation_run_id,
            "interpretation_source": args.interpretation_source,
            "validation_interpretation_run_id": args.validation_interpretation_run_id,
            "holdout_run_id": args.holdout_run_id,
            "max_realized_market_leakage": float(args.max_realized_market_leakage),
            "entry_count": len(jsonl_rows),
            "counts_by_classification": {
                classification: sum(1 for row in jsonl_rows if row["classification"] == classification)
                for classification in sorted(POSITIVE_CLASSIFICATIONS)
            },
            "top_ranked_shortlist_id": jsonl_rows[0]["shortlist_id"] if jsonl_rows else None,
            "top_ranked_publication_item_id": jsonl_rows[0]["publication_item_id"] if jsonl_rows else None,
        }
        metrics_path = output_dir / "unrealized_ideas_index_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "unrealized_ideas_index", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
