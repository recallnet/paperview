#!/usr/bin/env python3

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"
DEFAULT_EDGE_VERSION = "edge-card-v1"
DEFAULT_RUN_KIND = "edge_card_generation"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate edge-card-first outputs from ranked candidate families."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--schema-sql-path", default=str(DEFAULT_SCHEMA_SQL_PATH))
    parser.add_argument("--ranking-run-id", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--edge-version", default=DEFAULT_EDGE_VERSION)
    parser.add_argument("--max-edge-cards", type=int, default=10)
    parser.add_argument("--max-almost-there", type=int, default=10)
    parser.add_argument("--max-suppressed", type=int, default=10)
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def parse_json_object(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {}


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))
    # @context requirement -- The checked-in schema is not enough for older
    # live SQLite files because `CREATE TABLE IF NOT EXISTS` will not backfill
    # newly added edge columns. The edge-card path must materialize those
    # columns locally before it can query them safely.
    required_columns = {
        "invariant_type": "TEXT NOT NULL DEFAULT 'other'",
        "invariant_statement": "TEXT",
        "market_object": "TEXT",
        "trigger_window": "TEXT",
        "market_lifecycle_phase": "TEXT NOT NULL DEFAULT 'unknown'",
        "wrong_actor": "TEXT",
        "why_wrong": "TEXT",
        "why_persistence": "TEXT",
        "closure_mechanism": "TEXT",
        "death_condition": "TEXT",
        "executor_gap": "TEXT",
        "cheap_validation_step": "TEXT",
        "fast_falsifier": "TEXT",
        "novelty_reason": "TEXT",
        "composition_opportunity": "TEXT",
        "edge_confidence": "TEXT NOT NULL DEFAULT 'speculative'",
    }
    existing = {row[1] for row in connection.execute("PRAGMA table_info(mechanism_instances)")}
    for column_name, ddl_fragment in required_columns.items():
        if column_name not in existing:
            connection.execute(
                f"ALTER TABLE mechanism_instances ADD COLUMN {column_name} {ddl_fragment}"
            )


def ensure_run(connection, run_id: str | None, ranking_run_id: str, edge_version: str):
    resolved_run_id = run_id or f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    config = {
        "ranking_run_id": ranking_run_id,
        "edge_version": edge_version,
    }
    existing = connection.execute("SELECT run_id FROM extraction_runs WHERE run_id = ?", (resolved_run_id,)).fetchone()
    if existing is None:
        connection.execute(
            """
            INSERT INTO extraction_runs (
              run_id, run_kind, model_name, prompt_version, config_json, started_at, run_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_run_id,
                DEFAULT_RUN_KIND,
                ranking_run_id,
                edge_version,
                json.dumps(config, sort_keys=True),
                now_utc(),
                "running",
            ),
        )
    else:
        connection.execute(
            """
            UPDATE extraction_runs
            SET run_kind = ?, model_name = ?, prompt_version = ?, config_json = ?, run_status = ?, completed_at = NULL
            WHERE run_id = ?
            """,
            (
                DEFAULT_RUN_KIND,
                ranking_run_id,
                edge_version,
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def clear_existing_run_rows(connection, run_id: str):
    # @context requirement -- Edge-card reruns must be idempotent. If bucket
    # assignment logic changes between runs, old rows under the same `run_id`
    # otherwise linger beside the new inserts and make the DB disagree with the
    # regenerated markdown/json artifacts.
    connection.execute("DELETE FROM edge_cards WHERE run_id = ?", (run_id,))


def load_ranked_rows(connection, ranking_run_id: str):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          cfr.candidate_family_ranking_id,
          cfr.candidate_family_id,
          cfr.family_rank,
          cfr.gate_status,
          cfr.final_priority_score,
          cfr.base_utility_score,
          cfr.diversity_penalty_score,
          cfr.rationale_json,
          cf.family_name,
          cf.family_status,
          cf.family_summary,
          cf.family_json
        FROM candidate_family_rankings cfr
        JOIN candidate_families cf
          ON cf.candidate_family_id = cfr.candidate_family_id
        WHERE cfr.run_id = ?
        ORDER BY cfr.family_rank
        """,
        (ranking_run_id,),
    ).fetchall()
    return [{**dict(row), "family_json": parse_json_object(row["family_json"]), "rationale_json": parse_json_object(row["rationale_json"])} for row in rows]


def load_member_support(connection, ranking_run_id: str, family_ids):
    if not family_ids:
        return {}
    connection.row_factory = sqlite3.Row
    placeholders = ", ".join("?" for _ in family_ids)
    rows = connection.execute(
        f"""
        SELECT
          cfm.candidate_family_id,
          aqh.adjusted_score,
          qch.lexical_distance_score,
          qch.structural_similarity_score,
          qch.transfer_plausibility_score,
          qch.blocker_penalty_score,
          qch.source_paper_id,
          qch.candidate_paper_id,
          p.title,
          p.published_at,
          pe.validation_status AS extraction_validation_status,
          mi.mechanism_instance_id,
          mi.mechanism_label,
          mi.mechanism_summary,
          mi.mechanism_json,
          mi.invariant_type,
          mi.invariant_statement,
          mi.market_object,
          mi.trigger_window,
          mi.market_lifecycle_phase,
          mi.wrong_actor,
          mi.why_wrong,
          mi.why_persistence,
          mi.closure_mechanism,
          mi.death_condition,
          mi.executor_gap,
          mi.cheap_validation_step,
          mi.fast_falsifier,
          mi.novelty_reason,
          mi.composition_opportunity,
          mi.edge_confidence
        FROM candidate_family_members cfm
        JOIN adjudicated_queryless_hits aqh
          ON aqh.adjudicated_queryless_hit_id = cfm.adjudicated_queryless_hit_id
        JOIN queryless_candidate_hits qch
          ON qch.queryless_candidate_hit_id = aqh.queryless_candidate_hit_id
        JOIN mechanism_instances mi
          ON mi.mechanism_instance_id = aqh.candidate_mechanism_instance_id
        JOIN papers p
          ON p.paper_id = mi.paper_id
        LEFT JOIN paper_extractions pe
          ON pe.extraction_id = mi.source_extraction_id
        WHERE cfm.run_id = ?
          AND cfm.candidate_family_id IN ({placeholders})
        ORDER BY cfm.candidate_family_id, aqh.adjusted_score DESC
        """,
        (ranking_run_id, *family_ids),
    ).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["candidate_family_id"]].append(dict(row))
    return grouped


def classify_bucket(row):
    # @context decision -- The reset product surface is judged on actionable edge
    # cards, almost-there candidates, and explicit suppressions. Known
    # `research_dead_end_worth_excluding` families must not populate the edge-card
    # surface at all. We must preserve ranking truth here: a family that the
    # scorer marked `suppressed` should stay suppressed in the operator artifact,
    # otherwise the surface lies about what the pipeline actually passed.
    insight_type = row["family_json"].get("candidate_insight_type", "unknown")
    suppression_gates = {
        reason.get("gate")
        for reason in row["family_json"].get("suppression_reasons", [])
        if isinstance(reason, dict)
    }
    if insight_type == "research_dead_end_worth_excluding":
        return None
    if {
        "failed_explicit_transfer_path",
        "failed_semantic_validity",
    }.issubset(suppression_gates):
        return None
    if row["gate_status"] == "passed":
        return "top_edge"
    if row["gate_status"] in {"blocked", "almost_there"}:
        return "almost_there"
    if row["gate_status"] in {"suppressed", "rejected"}:
        return "suppressed"
    return "suppressed"


def select_target_rows(ranked_rows, limits):
    # @context decision -- Edge-card generation should only load member support
    # for the families it will actually emit. Pulling every ranked family member
    # defeats the reset by making the final artifact path scale with the full
    # suppressed universe instead of the operator-facing surface.
    grouped = {"top_edge": [], "almost_there": [], "suppressed": []}
    for row in ranked_rows:
        bucket = classify_bucket(row)
        if bucket is None:
            continue
        if len(grouped[bucket]) >= limits[bucket]:
            continue
        grouped[bucket].append(row)
    return grouped


def select_rejected_rows(ranked_rows, limit):
    rejected = []
    for row in ranked_rows:
        insight_type = row["family_json"].get("candidate_insight_type", "unknown")
        suppression_gates = {
            reason.get("gate")
            for reason in row["family_json"].get("suppression_reasons", [])
            if isinstance(reason, dict)
        }
        if insight_type == "research_dead_end_worth_excluding" or {
            "failed_explicit_transfer_path",
            "failed_semantic_validity",
        }.issubset(suppression_gates):
            rejected.append(row)
        if len(rejected) >= limit:
            break
    return rejected


def build_edge_payload(row, members):
    representative = members[0] if members else {}
    support_ids = sorted({member["candidate_paper_id"] for member in members[:5] if member.get("candidate_paper_id")})
    suppression_reasons = row["family_json"].get("suppression_reasons", [])
    field_provenance = {
        field_name: (
            "explicit_from_model" if representative.get(field_name) else "missing"
        )
        for field_name in (
            "invariant_statement",
            "market_object",
            "trigger_window",
            "wrong_actor",
            "why_wrong",
            "why_persistence",
            "closure_mechanism",
            "death_condition",
            "executor_gap",
            "cheap_validation_step",
            "fast_falsifier",
            "novelty_reason",
            "composition_opportunity",
        )
    }
    return {
        "family_name": row["family_name"],
        "family_summary": row["family_summary"],
        "gate_status": row["gate_status"],
        "priority_score": row["final_priority_score"],
        "supporting_paper_ids": support_ids,
        "representative_mechanism_instance_id": representative.get("mechanism_instance_id"),
        "broken_relation_or_stress": representative.get("invariant_statement"),
        "market_object": representative.get("market_object"),
        "trigger_window": representative.get("trigger_window"),
        "wrong_actor": representative.get("wrong_actor"),
        "why_wrong": representative.get("why_wrong"),
        "why_persistence": representative.get("why_persistence"),
        "closure_mechanism": representative.get("closure_mechanism"),
        "death_condition": representative.get("death_condition"),
        "executor_gap": representative.get("executor_gap"),
        "cheap_validation_step": representative.get("cheap_validation_step"),
        "fast_falsifier": representative.get("fast_falsifier"),
        "novelty_reason": representative.get("novelty_reason"),
        "field_provenance": field_provenance,
        "composition_opportunity": representative.get("composition_opportunity"),
        "confidence": representative.get("edge_confidence") or "speculative",
        "lexically_far_from_qfin": representative.get("lexical_distance_score", 0) >= 0.45,
        "suppression_reasons": suppression_reasons,
        "member_snapshots": [
            {
                "paper_id": member["candidate_paper_id"],
                "title": member["title"],
                "mechanism_instance_id": member["mechanism_instance_id"],
                "mechanism_label": member["mechanism_label"],
                "mechanism_summary": member["mechanism_summary"],
                "lexical_distance_score": member["lexical_distance_score"],
                "transfer_plausibility_score": member["transfer_plausibility_score"],
            }
            for member in members[:5]
        ],
    }


def build_rejection_payload(row, members):
    representative = members[0] if members else {}
    mechanism_json = parse_json_object(representative.get("mechanism_json"))
    return {
        "family_name": row["family_name"],
        "paper_id": representative.get("candidate_paper_id"),
        "title": representative.get("title"),
        "rejection_reasons": row["family_json"].get("suppression_reasons", []),
        "semantic_failure_reasons": row["family_json"].get("semantic_failure_reasons", []),
        "extraction_completeness_status": representative.get("extraction_validation_status") or "unknown",
        "provenance_summary": mechanism_json.get("field_provenance", {}),
    }


def render_markdown(run_id: str, grouped_cards: dict[str, list[dict]], output_dir: Path):
    lines = [
        f"# Edge Card Checkpoint `{run_id}`",
        "",
        "## Top 10 Edge Cards",
    ]
    for bucket, title in (
        ("top_edge", "Top 10 Edge Cards"),
        ("almost_there", "Top 10 Almost-There Cards"),
        ("suppressed", "Top 10 Suppressed Candidates"),
    ):
        if bucket != "top_edge":
            lines.extend(["", f"## {title}"])
        cards = grouped_cards.get(bucket, [])
        if not cards:
            lines.append("- none")
            continue
        for card in cards:
            lines.extend(
                [
                    f"- `{card['family_name']}`",
                    f"  broken relation / stress: {card['broken_relation_or_stress']}",
                    f"  market object: {card['market_object']}",
                    f"  wrong actor: {card['wrong_actor']}",
                    f"  persistence reason: {card['why_persistence']}",
                    f"  death condition: {card['death_condition']}",
                    f"  executor gap: {card['executor_gap']}",
                    f"  cheap test: {card['cheap_validation_step']}",
                    f"  fast falsifier: {card['fast_falsifier']}",
                    f"  supporting papers: {', '.join(card['supporting_paper_ids']) or 'none'}",
                ]
            )
            if card["suppression_reasons"]:
                lines.append(f"  suppression reasons: {json.dumps(card['suppression_reasons'], sort_keys=True)}")
    path = output_dir / "edge_cards.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def render_rejection_report(run_id: str, rejections: list[dict], output_dir: Path):
    lines = [f"# Rejection Report `{run_id}`", ""]
    if not rejections:
        lines.append("- none")
    for row in rejections:
        lines.extend(
            [
                f"- `{row['family_name']}`",
                f"  paper id: {row.get('paper_id') or 'unknown'}",
                f"  title: {row.get('title') or 'unknown'}",
                f"  rejection reasons: {json.dumps(row.get('rejection_reasons', []), sort_keys=True)}",
                f"  semantic failure reasons: {json.dumps(row.get('semantic_failure_reasons', []), sort_keys=True)}",
                f"  extraction completeness: {row.get('extraction_completeness_status') or 'unknown'}",
                f"  provenance: {json.dumps(row.get('provenance_summary', {}), sort_keys=True)}",
            ]
        )
    path = output_dir / "rejection_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "rejection_report.json").write_text(
        json.dumps(rejections, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def upsert_edge_card(connection, row, run_id: str, edge_version: str, edge_bucket: str, edge_rank: int, markdown_path: Path, edge_payload):
    connection.execute(
        """
        INSERT INTO edge_cards (
          candidate_family_id,
          candidate_family_ranking_id,
          run_id,
          edge_version,
          edge_name,
          edge_bucket,
          edge_status,
          edge_rank,
          edge_markdown_path,
          edge_json,
          updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(candidate_family_id, run_id, edge_version, edge_bucket) DO UPDATE SET
          candidate_family_ranking_id = excluded.candidate_family_ranking_id,
          edge_name = excluded.edge_name,
          edge_status = excluded.edge_status,
          edge_rank = excluded.edge_rank,
          edge_markdown_path = excluded.edge_markdown_path,
          edge_json = excluded.edge_json,
          updated_at = excluded.updated_at
        """,
        (
            row["candidate_family_id"],
            row["candidate_family_ranking_id"],
            run_id,
            edge_version,
            row["family_name"],
            edge_bucket,
            "drafted",
            edge_rank,
            str(markdown_path.resolve()),
            json.dumps(edge_payload, sort_keys=True),
            now_utc(),
        ),
    )


def main():
    args = parse_args()
    output_dir = ROOT / "data" / "structural-analogy" / "runs" / f"{args.ranking_run_id}-edge-cards"
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(Path(args.db_path).resolve()), timeout=60)
    connection.execute("PRAGMA busy_timeout = 60000")
    try:
        ensure_store_contract(connection, Path(args.schema_sql_path).resolve())
        run_id = ensure_run(connection, args.run_id, args.ranking_run_id, args.edge_version)
        clear_existing_run_rows(connection, run_id)
        ranked_rows = load_ranked_rows(connection, args.ranking_run_id)
        limits = {
            "top_edge": args.max_edge_cards,
            "almost_there": args.max_almost_there,
            "suppressed": args.max_suppressed,
        }
        selected_rows = select_target_rows(ranked_rows, limits)
        family_ids = [
            row["candidate_family_id"]
            for rows in selected_rows.values()
            for row in rows
        ]
        rejected_rows = select_rejected_rows(ranked_rows, args.max_suppressed)
        family_ids.extend(row["candidate_family_id"] for row in rejected_rows)
        members_by_family = load_member_support(connection, args.ranking_run_id, family_ids)

        grouped_rows = {"top_edge": [], "almost_there": [], "suppressed": []}
        for bucket, rows in selected_rows.items():
            for row in rows:
                payload = build_edge_payload(row, members_by_family.get(row["candidate_family_id"], []))
                grouped_rows[bucket].append(payload)
        rejection_rows = [
            build_rejection_payload(row, members_by_family.get(row["candidate_family_id"], []))
            for row in rejected_rows
        ]

        markdown_path = render_markdown(run_id, grouped_rows, output_dir)
        rejection_report_path = render_rejection_report(run_id, rejection_rows, output_dir)
        for bucket, cards in grouped_rows.items():
            for index, card in enumerate(cards, start=1):
                row = next(r for r in ranked_rows if r["family_name"] == card["family_name"])
                upsert_edge_card(connection, row, run_id, args.edge_version, bucket, index, markdown_path, card)

        summary = {
            "run_id": run_id,
            "ranking_run_id": args.ranking_run_id,
            "output_dir": str(output_dir.resolve()),
            "markdown_path": str(markdown_path.resolve()),
            "rejection_report_path": str(rejection_report_path.resolve()),
            "top_edge_count": len(grouped_rows["top_edge"]),
            "almost_there_count": len(grouped_rows["almost_there"]),
            "suppressed_count": len(grouped_rows["suppressed"]),
            "rejected_count": len(rejection_rows),
        }
        (output_dir / "edge_cards.json").write_text(json.dumps(grouped_rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        connection.execute(
            "UPDATE extraction_runs SET run_status = ?, completed_at = ? WHERE run_id = ?",
            ("completed", now_utc(), run_id),
        )
        connection.commit()
    finally:
        connection.close()

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
