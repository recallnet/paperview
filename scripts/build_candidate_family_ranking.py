#!/usr/bin/env python3

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"
DEFAULT_RANKING_VERSION = "c13-family-ranking-v1"
DEFAULT_RUN_KIND = "candidate_family_ranking"
TRAIT_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.35, "other": 0.35}
EVIDENCE_SCORE = {"high": 1.0, "strong": 1.0, "medium": 0.7, "moderate": 0.7, "low": 0.35, "weak": 0.35, "unscored": 0.25}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build hard-gated candidate family rankings from adjudicated hits."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-sql-path",
        default=str(DEFAULT_SCHEMA_SQL_PATH),
        help="Path to the SQL schema to apply before ranking.",
    )
    parser.add_argument(
        "--adjudication-run-id",
        required=True,
        help="Analyst adjudication run id produced by run_analyst_adjudication.py.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit candidate ranking run id.",
    )
    parser.add_argument(
        "--ranking-version",
        default=DEFAULT_RANKING_VERSION,
        help="Candidate family ranking contract version to persist.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clamp(value):
    return max(0.0, min(1.0, value))


def normalize_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def slugify(value):
    materialized = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return materialized or "unknown"


def parse_json_object(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {}


def avg(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))


def ensure_run(connection, run_id: str | None, adjudication_run_id: str, ranking_version: str):
    resolved_run_id = run_id or (
        f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    config = {
        "adjudication_run_id": adjudication_run_id,
        "ranking_version": ranking_version,
    }
    existing = connection.execute(
        "SELECT run_id FROM extraction_runs WHERE run_id = ?",
        (resolved_run_id,),
    ).fetchone()
    if existing is None:
        connection.execute(
            """
            INSERT INTO extraction_runs (
              run_id,
              run_kind,
              model_name,
              prompt_version,
              config_json,
              started_at,
              run_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_run_id,
                DEFAULT_RUN_KIND,
                adjudication_run_id,
                ranking_version,
                json.dumps(config, sort_keys=True),
                now_utc(),
                "running",
            ),
        )
    else:
        connection.execute(
            """
            UPDATE extraction_runs
            SET run_kind = ?,
                model_name = ?,
                prompt_version = ?,
                config_json = ?,
                run_status = ?,
                completed_at = NULL
            WHERE run_id = ?
            """,
            (
                DEFAULT_RUN_KIND,
                adjudication_run_id,
                ranking_version,
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def load_adjudicated_hits(connection, adjudication_run_id: str):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          aqh.adjudicated_queryless_hit_id,
          aqh.queryless_candidate_hit_id,
          aqh.run_id AS adjudication_run_id,
          aqh.analyst_weight_update_id,
          aqh.queryless_run_id,
          aqh.mining_mode,
          aqh.source_mechanism_instance_id,
          aqh.candidate_mechanism_instance_id,
          aqh.adjusted_score,
          aqh.adjusted_rank_within_source,
          aqh.score_delta,
          aqh.support_json,
          qch.source_paper_id,
          qch.candidate_paper_id,
          qch.source_literature_family,
          qch.candidate_literature_family,
          qch.source_evaluation_split,
          qch.candidate_evaluation_split,
          qch.is_cross_family,
          qch.structural_similarity_score,
          qch.lexical_distance_score,
          qch.transfer_plausibility_score,
          qch.blocker_penalty_score,
          qch.rationale_json AS queryless_rationale_json,
          qch.retrieval_run_id,
          qch.retrieval_version,
          src_doc.source_json AS source_document_json,
          src_doc.mechanism_summary_text AS source_mechanism_summary,
          cand_doc.source_json AS candidate_document_json,
          cand_doc.mechanism_summary_text AS candidate_mechanism_summary,
          mi.insight_type AS candidate_insight_type,
          mi.mechanism_label AS candidate_mechanism_label,
          COALESCE(es.worth_followup_score, 0.0) AS candidate_worth_followup_score,
          COALESCE(es.underexploited_score, 0.0) AS candidate_underexploited_score,
          COALESCE(es.exposure_score, 0.0) AS candidate_exposure_score
        FROM adjudicated_queryless_hits aqh
        JOIN queryless_candidate_hits qch
          ON qch.queryless_candidate_hit_id = aqh.queryless_candidate_hit_id
        JOIN mechanism_retrieval_documents src_doc
          ON src_doc.mechanism_instance_id = qch.source_mechanism_instance_id
         AND src_doc.run_id = qch.retrieval_run_id
         AND src_doc.retrieval_version = qch.retrieval_version
        JOIN mechanism_retrieval_documents cand_doc
          ON cand_doc.mechanism_instance_id = qch.candidate_mechanism_instance_id
         AND cand_doc.run_id = qch.retrieval_run_id
         AND cand_doc.retrieval_version = qch.retrieval_version
        JOIN mechanism_instances mi
          ON mi.mechanism_instance_id = qch.candidate_mechanism_instance_id
        LEFT JOIN mechanism_exposure_scores es
          ON es.mechanism_instance_id = qch.candidate_mechanism_instance_id
         AND es.exposure_score_id = (
           SELECT es2.exposure_score_id
           FROM mechanism_exposure_scores es2
           WHERE es2.mechanism_instance_id = qch.candidate_mechanism_instance_id
           ORDER BY es2.updated_at DESC, es2.exposure_score_id DESC
           LIMIT 1
         )
        WHERE aqh.run_id = ?
        ORDER BY aqh.adjusted_score DESC, aqh.adjudicated_queryless_hit_id
        """,
        (adjudication_run_id,),
    ).fetchall()

    labels_by_hit = defaultdict(lambda: {"bool": {}, "interesting": [], "weak": []})
    for hit_id, label_kind, label_value, notes in connection.execute(
        """
        SELECT queryless_candidate_hit_id, label_kind, label_value, notes
        FROM analyst_labels
        WHERE queryless_candidate_hit_id IS NOT NULL
        """
    ):
        if label_kind in {
            "accept",
            "structurally_relevant",
            "non_obvious",
            "genuinely_new",
            "worth_strategy_brief",
        }:
            labels_by_hit[hit_id]["bool"][label_kind] = label_value
        elif label_kind == "interesting_reason":
            labels_by_hit[hit_id]["interesting"].append(notes or label_value)
        elif label_kind == "weakness_reason":
            labels_by_hit[hit_id]["weak"].append(notes or label_value)

    return [
        {
            **dict(row),
            "source_document_json": parse_json_object(row["source_document_json"]),
            "candidate_document_json": parse_json_object(row["candidate_document_json"]),
            "queryless_rationale_json": parse_json_object(row["queryless_rationale_json"]),
            "support_json": parse_json_object(row["support_json"]),
            "analyst_labels": labels_by_hit[row["queryless_candidate_hit_id"]],
        }
        for row in rows
    ]


def trait_score(document_json, trait_name):
    traits = document_json.get("mechanism_traits", {})
    return TRAIT_SCORE.get(traits.get(trait_name, "unknown"), 0.35)


def build_transfer_path(hit):
    structural_support = hit["queryless_rationale_json"].get("structural_support", {})
    facet_overlaps = structural_support.get("facet_overlaps", {})
    candidate_traits = hit["candidate_document_json"].get("mechanism_traits", {})
    overlap_fields = [
        field_name
        for field_name, score in facet_overlaps.items()
        if score and score >= 0.3
    ]
    path_parts = []
    if overlap_fields:
        path_parts.append("shared structure via " + ", ".join(sorted(overlap_fields)))
    if trait_score(hit["candidate_document_json"], "prediction_market_portability") >= 0.6:
        path_parts.append("prediction portability is medium/high")
    if trait_score(hit["candidate_document_json"], "novel_market_portability") >= 0.6:
        path_parts.append("novel-market portability is medium/high")
    if hit["analyst_labels"]["interesting"]:
        path_parts.append("analyst rationale: " + "; ".join(hit["analyst_labels"]["interesting"][:2]))
    return path_parts


def gate_hit(hit):
    candidate_doc = hit["candidate_document_json"]
    evidence_threshold_pass = (
        EVIDENCE_SCORE.get(candidate_doc.get("evidence_confidence", "unscored"), 0.25) >= 0.7
        and bool(candidate_doc.get("section_labels"))
    )
    transfer_path = build_transfer_path(hit)
    explicit_transfer_path_pass = (
        hit["transfer_plausibility_score"] >= 0.55 and len(transfer_path) > 0
    )
    explicit_failure_mode_pass = bool(
        candidate_doc.get("failure_regimes")
        or candidate_doc.get("fragility_flags")
        or candidate_doc.get("capacity_constraints")
        or candidate_doc.get("fingerprint_facets", {}).get("portability_blockers")
        or hit["analyst_labels"]["weak"]
    )
    non_null_tradecore_mapping_pass = (
        trait_score(candidate_doc, "tradecore_fit") >= 0.6
    )
    catastrophic_blockers = len(
        candidate_doc.get("fingerprint_facets", {}).get("portability_blockers", [])
    ) >= 3 or hit["blocker_penalty_score"] > 0.42
    no_catastrophic_blocker_pass = not catastrophic_blockers
    gate_results = {
        "evidence_threshold_pass": evidence_threshold_pass,
        "explicit_transfer_path_pass": explicit_transfer_path_pass,
        "explicit_failure_mode_pass": explicit_failure_mode_pass,
        "non_null_tradecore_mapping_pass": non_null_tradecore_mapping_pass,
        "no_catastrophic_blocker_pass": no_catastrophic_blocker_pass,
    }
    gate_pass = all(gate_results.values())
    return gate_pass, gate_results, transfer_path


def base_utility(hit):
    candidate_doc = hit["candidate_document_json"]
    bool_labels = hit["analyst_labels"]["bool"]
    analyst_novelty = avg(
        1.0 if bool_labels.get(label_kind) in {"yes", "accept", "accepted"} else 0.0
        for label_kind in ("non_obvious", "genuinely_new", "worth_strategy_brief")
    )
    evidence_score = EVIDENCE_SCORE.get(candidate_doc.get("evidence_confidence", "unscored"), 0.25)
    tradecore_mapping = trait_score(candidate_doc, "tradecore_fit")
    return clamp(
        0.30 * hit["adjusted_score"]
        + 0.16 * hit["candidate_worth_followup_score"]
        + 0.14 * hit["candidate_underexploited_score"]
        + 0.10 * hit["structural_similarity_score"]
        + 0.10 * hit["lexical_distance_score"]
        + 0.10 * analyst_novelty
        + 0.06 * evidence_score
        + 0.08 * tradecore_mapping
        - 0.12 * hit["blocker_penalty_score"]
    )


def family_key(hit):
    facets = hit["candidate_document_json"].get("fingerprint_facets", {})
    trigger = (facets.get("trigger") or ["unknown_trigger"])[0]
    topology = (facets.get("market_topology") or ["unknown_topology"])[0]
    execution = (facets.get("execution_shape") or ["unknown_execution"])[0]
    insight_type = hit["candidate_insight_type"] or "unknown_insight"
    return "__".join(
        slugify(part)
        for part in (trigger, topology, execution, insight_type)
    )


def build_family_records(hits):
    families = {}
    for hit in hits:
        gate_pass, gate_results, transfer_path = gate_hit(hit)
        utility = base_utility(hit)
        family_name = family_key(hit)
        entry = families.setdefault(
            family_name,
            {
                "family_name": family_name,
                "members": [],
                "passed_members": [],
                "source_family_counts": Counter(),
                "candidate_family_counts": Counter(),
                "primary_trigger": (
                    hit["candidate_document_json"].get("fingerprint_facets", {}).get("trigger") or ["unknown_trigger"]
                )[0],
                "target_domain": hit["candidate_literature_family"],
                "candidate_insight_type": hit["candidate_insight_type"],
                "family_summary": hit["candidate_mechanism_summary"],
            },
        )
        member = {
            **hit,
            "gate_pass": gate_pass,
            "gate_results": gate_results,
            "transfer_path": transfer_path,
            "base_utility_score": utility,
        }
        entry["members"].append(member)
        if gate_pass:
            entry["passed_members"].append(member)
        entry["source_family_counts"][hit["source_literature_family"]] += 1
        entry["candidate_family_counts"][hit["candidate_literature_family"]] += 1

    family_records = []
    for family_name, entry in families.items():
        members = entry["members"]
        passed_members = entry["passed_members"]
        representative = max(
            passed_members or members,
            key=lambda member: (member["base_utility_score"], member["adjusted_score"]),
        )
        blocker_status = "satisfied" if passed_members else "blocked"
        family_status = "queued" if passed_members else "rejected"
        family_records.append(
            {
                **entry,
                "candidate_family_row": {
                    "family_name": family_name,
                    "family_status": family_status,
                    "family_summary": normalize_text(entry["family_summary"]),
                    "blocker_requirement_status": blocker_status,
                    "family_json": {
                        "target_domain": entry["target_domain"],
                        "candidate_insight_type": entry["candidate_insight_type"],
                        "source_family_counts": dict(sorted(entry["source_family_counts"].items())),
                        "candidate_family_counts": dict(sorted(entry["candidate_family_counts"].items())),
                        "member_hit_ids": [
                            member["adjudicated_queryless_hit_id"] for member in members
                        ],
                        "passed_member_hit_ids": [
                            member["adjudicated_queryless_hit_id"] for member in passed_members
                        ],
                        "representative_candidate_mechanism_instance_id": representative["candidate_mechanism_instance_id"],
                    },
                },
                "representative": representative,
                "mean_base_utility_score": avg(
                    member["base_utility_score"] for member in passed_members or members
                ),
                "gate_status": "passed" if passed_members else "rejected",
            }
        )
    return family_records


def rank_families(family_records):
    ordered = sorted(
        family_records,
        key=lambda record: (
            -(record["mean_base_utility_score"] if record["gate_status"] == "passed" else -1.0),
            -record["representative"]["adjusted_score"],
            record["family_name"],
        ),
    )
    seen_domains = Counter()
    seen_triggers = Counter()
    ranked = []
    for record in ordered:
        diversity_penalty = (
            0.10 * seen_domains[record["target_domain"]]
            + 0.06 * seen_triggers[record["primary_trigger"]]
        )
        final_priority = clamp(record["mean_base_utility_score"] - diversity_penalty)
        ranked.append(
            {
                **record,
                "diversity_penalty_score": diversity_penalty,
                "final_priority_score": final_priority,
            }
        )
        if record["gate_status"] == "passed":
            seen_domains[record["target_domain"]] += 1
            seen_triggers[record["primary_trigger"]] += 1

    return sorted(
        ranked,
        key=lambda record: (
            0 if record["gate_status"] == "passed" else 1,
            -record["final_priority_score"],
            record["family_name"],
        ),
    )


def upsert_candidate_family(connection, run_id: str, record):
    family_json = dict(record["candidate_family_row"]["family_json"])
    family_json["last_ranking_run_id"] = run_id
    cursor = connection.execute(
        """
        INSERT INTO candidate_families (
          family_name,
          family_status,
          family_summary,
          blocker_requirement_status,
          family_json,
          updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(family_name) DO UPDATE SET
          family_status = excluded.family_status,
          family_summary = excluded.family_summary,
          blocker_requirement_status = excluded.blocker_requirement_status,
          family_json = excluded.family_json,
          updated_at = excluded.updated_at
        RETURNING candidate_family_id
        """,
        (
            record["candidate_family_row"]["family_name"],
            record["candidate_family_row"]["family_status"],
            record["candidate_family_row"]["family_summary"],
            record["candidate_family_row"]["blocker_requirement_status"],
            json.dumps(family_json, sort_keys=True),
            now_utc(),
        ),
    )
    return cursor.fetchone()[0]


def upsert_transfer_hypothesis(connection, candidate_family_id: int, member):
    negative_rationale = list(member["analyst_labels"]["weak"])
    negative_rationale.extend(
        member["candidate_document_json"].get("failure_regimes", [])
    )
    negative_rationale.extend(
        member["candidate_document_json"].get("fragility_flags", [])
    )
    rationale_json = {
        "gate_results": member["gate_results"],
        "transfer_path": member["transfer_path"],
        "base_utility_score": member["base_utility_score"],
        "adjusted_score": member["adjusted_score"],
        "source_literature_family": member["source_literature_family"],
        "candidate_literature_family": member["candidate_literature_family"],
        "queryless_candidate_hit_id": member["queryless_candidate_hit_id"],
        "adjudicated_queryless_hit_id": member["adjudicated_queryless_hit_id"],
    }
    existing = connection.execute(
        """
        SELECT transfer_hypothesis_id
        FROM transfer_hypotheses
        WHERE mechanism_instance_id = ?
          AND candidate_family_id = ?
          AND COALESCE(target_domain, '') = COALESCE(?, '')
        """,
        (
            member["source_mechanism_instance_id"],
            candidate_family_id,
            member["candidate_literature_family"],
        ),
    ).fetchone()
    status = "passed_gates" if member["gate_pass"] else "rejected"
    if existing is None:
        connection.execute(
            """
            INSERT INTO transfer_hypotheses (
              mechanism_instance_id,
              candidate_family_id,
              target_domain,
              hypothesis_status,
              negative_transfer_rationale_json,
              rationale_json,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member["source_mechanism_instance_id"],
                candidate_family_id,
                member["candidate_literature_family"],
                status,
                json.dumps(sorted(set(negative_rationale))),
                json.dumps(rationale_json, sort_keys=True),
                now_utc(),
            ),
        )
    else:
        connection.execute(
            """
            UPDATE transfer_hypotheses
            SET hypothesis_status = ?,
                negative_transfer_rationale_json = ?,
                rationale_json = ?,
                updated_at = ?
            WHERE transfer_hypothesis_id = ?
            """,
            (
                status,
                json.dumps(sorted(set(negative_rationale))),
                json.dumps(rationale_json, sort_keys=True),
                now_utc(),
                existing[0],
            ),
        )


def persist_family_members(connection, candidate_family_id: int, run_id: str, record):
    for member in record["members"]:
        support_payload = {
            "gate_status": "passed" if member["gate_pass"] else "rejected",
            "gate_results": member["gate_results"],
            "transfer_path": member["transfer_path"],
            "base_utility_score": member["base_utility_score"],
        }
        connection.execute(
            """
            INSERT INTO candidate_family_members (
              candidate_family_id,
              run_id,
              adjudicated_queryless_hit_id,
              source_mechanism_instance_id,
              candidate_mechanism_instance_id,
              member_role,
              support_json,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_family_id, run_id, adjudicated_queryless_hit_id) DO UPDATE SET
              member_role = excluded.member_role,
              support_json = excluded.support_json,
              updated_at = excluded.updated_at
            """,
            (
                candidate_family_id,
                run_id,
                member["adjudicated_queryless_hit_id"],
                member["source_mechanism_instance_id"],
                member["candidate_mechanism_instance_id"],
                "representative_hypothesis"
                if member["adjudicated_queryless_hit_id"]
                == record["representative"]["adjudicated_queryless_hit_id"]
                else "supporting_hypothesis",
                json.dumps(support_payload, sort_keys=True),
                now_utc(),
            ),
        )


def persist_family_ranking(connection, candidate_family_id: int, run_id: str, ranking_version: str, family_rank: int, record):
    rationale_payload = {
        "gate_status": record["gate_status"],
        "member_count": len(record["members"]),
        "passed_member_count": len(record["passed_members"]),
        "target_domain": record["target_domain"],
        "primary_trigger": record["primary_trigger"],
        "representative_hit_id": record["representative"]["adjudicated_queryless_hit_id"],
        "representative_adjusted_score": record["representative"]["adjusted_score"],
    }
    connection.execute(
        """
        INSERT INTO candidate_family_rankings (
          candidate_family_id,
          run_id,
          ranking_version,
          family_rank,
          gate_status,
          base_utility_score,
          diversity_penalty_score,
          final_priority_score,
          rationale_json,
          updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(candidate_family_id, run_id, ranking_version) DO UPDATE SET
          family_rank = excluded.family_rank,
          gate_status = excluded.gate_status,
          base_utility_score = excluded.base_utility_score,
          diversity_penalty_score = excluded.diversity_penalty_score,
          final_priority_score = excluded.final_priority_score,
          rationale_json = excluded.rationale_json,
          updated_at = excluded.updated_at
        """,
        (
            candidate_family_id,
            run_id,
            ranking_version,
            family_rank,
            record["gate_status"],
            record["mean_base_utility_score"],
            record["diversity_penalty_score"],
            record["final_priority_score"],
            json.dumps(rationale_payload, sort_keys=True),
            now_utc(),
        ),
    )


def persist_strategy_candidate(connection, run_id: str, candidate_family_id: int, family_rank: int, record):
    candidate_payload = {
        "run_id": run_id,
        "candidate_family_id": candidate_family_id,
        "family_rank": family_rank,
        "gate_status": record["gate_status"],
        "target_domain": record["target_domain"],
        "representative_candidate_mechanism_instance_id": record["representative"]["candidate_mechanism_instance_id"],
    }
    connection.execute(
        """
        INSERT INTO strategy_candidates (
          source_paper_id,
          candidate_name,
          candidate_status,
          priority_score,
          review_notes,
          candidate_json,
          updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["representative"]["source_paper_id"],
            record["family_name"],
            "queued" if record["gate_status"] == "passed" else "rejected",
            record["final_priority_score"],
            "; ".join(record["representative"]["transfer_path"][:2]),
            json.dumps(candidate_payload, sort_keys=True),
            now_utc(),
        ),
    )


def summarize(run_id: str, adjudication_run_id: str, ranked_records):
    passed = [record for record in ranked_records if record["gate_status"] == "passed"]
    domains = Counter(record["target_domain"] for record in passed)
    duplicate_family_rate = 0.0
    if passed:
        duplicate_family_rate = (
            len(passed) - len(set(record["family_name"] for record in passed))
        ) / len(passed)
    return {
        "run_id": run_id,
        "adjudication_run_id": adjudication_run_id,
        "family_count": len(ranked_records),
        "passed_family_count": len(passed),
        "target_domain_counts": dict(sorted(domains.items())),
        "duplicate_family_rate": duplicate_family_rate,
        "top_passed_families": [
            {
                "family_name": record["family_name"],
                "final_priority_score": record["final_priority_score"],
                "target_domain": record["target_domain"],
            }
            for record in passed[:10]
        ],
    }


def write_summary(run_id: str, summary):
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "candidate_family_ranking_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary_path


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    schema_sql_path = Path(args.schema_sql_path).resolve()

    connection = sqlite3.connect(str(db_path))
    try:
        ensure_store_contract(connection, schema_sql_path)
        run_id = ensure_run(connection, args.run_id, args.adjudication_run_id, args.ranking_version)
        connection.commit()

        hits = load_adjudicated_hits(connection, args.adjudication_run_id)
        if not hits:
            raise SystemExit(
                "no adjudicated_queryless_hits found for the requested run; complete C12 before running C13"
            )
        family_records = build_family_records(hits)
        ranked_records = rank_families(family_records)

        connection.execute("BEGIN")
        try:
            for family_rank, record in enumerate(ranked_records, start=1):
                candidate_family_id = upsert_candidate_family(connection, run_id, record)
                for member in record["members"]:
                    upsert_transfer_hypothesis(connection, candidate_family_id, member)
                persist_family_members(connection, candidate_family_id, run_id, record)
                persist_family_ranking(
                    connection,
                    candidate_family_id,
                    run_id,
                    args.ranking_version,
                    family_rank,
                    record,
                )
                persist_strategy_candidate(
                    connection, run_id, candidate_family_id, family_rank, record
                )
            connection.execute(
                """
                UPDATE extraction_runs
                SET run_status = ?, completed_at = ?
                WHERE run_id = ?
                """,
                ("completed", now_utc(), run_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()

    summary = summarize(run_id, args.adjudication_run_id, ranked_records)
    summary_path = write_summary(run_id, summary)
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
