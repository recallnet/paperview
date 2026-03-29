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
DEFAULT_BRIEF_VERSION = "c14-strategy-brief-v1"
DEFAULT_RUN_KIND = "strategy_brief_generation"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate final strategy briefs from ranked candidate families."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-sql-path",
        default=str(DEFAULT_SCHEMA_SQL_PATH),
        help="Path to the SQL schema to apply before brief generation.",
    )
    parser.add_argument(
        "--ranking-run-id",
        required=True,
        help="Candidate family ranking run id produced by build_candidate_family_ranking.py.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit strategy brief generation run id.",
    )
    parser.add_argument(
        "--brief-version",
        default=DEFAULT_BRIEF_VERSION,
        help="Brief contract version to persist.",
    )
    parser.add_argument(
        "--max-briefs",
        type=int,
        default=10,
        help="Maximum number of top ranked queued families to package into briefs.",
    )
    parser.add_argument(
        "--include-provisional-rejected",
        action="store_true",
        help="When no families passed C13, package top rejected families as provisional analyst-triage briefs.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))


def ensure_run(connection, run_id: str | None, ranking_run_id: str, brief_version: str, max_briefs: int):
    resolved_run_id = run_id or (
        f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    config = {
        "ranking_run_id": ranking_run_id,
        "brief_version": brief_version,
        "max_briefs": max_briefs,
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
                ranking_run_id,
                brief_version,
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
                ranking_run_id,
                brief_version,
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def parse_json_object(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {}


def parse_json_array(value):
    if not value:
        return []
    decoded = json.loads(value)
    return decoded if isinstance(decoded, list) else []


def normalize_text(value):
    return " ".join((value or "").split()).strip()


def slugify(value):
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in (value or "")).strip("-")


def load_ranked_families(
    connection, ranking_run_id: str, max_briefs: int, include_provisional_rejected: bool
):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          cfr.candidate_family_ranking_id,
          cfr.candidate_family_id,
          cfr.family_rank,
          cfr.gate_status,
          cfr.base_utility_score,
          cfr.diversity_penalty_score,
          cfr.final_priority_score,
          cfr.rationale_json,
          cf.family_name,
          cf.family_status,
          cf.family_summary,
          cf.blocker_requirement_status,
          cf.family_json
        FROM candidate_family_rankings cfr
        JOIN candidate_families cf
          ON cf.candidate_family_id = cfr.candidate_family_id
        WHERE cfr.run_id = ?
          AND cfr.gate_status = 'passed'
        ORDER BY cfr.family_rank
        LIMIT ?
        """,
        (ranking_run_id, max_briefs),
    ).fetchall()
    if not rows and include_provisional_rejected:
        rows = connection.execute(
            """
            SELECT
              cfr.candidate_family_ranking_id,
              cfr.candidate_family_id,
              cfr.family_rank,
              cfr.gate_status,
              cfr.base_utility_score,
              cfr.diversity_penalty_score,
              cfr.final_priority_score,
              cfr.rationale_json,
              cf.family_name,
              cf.family_status,
              cf.family_summary,
              cf.blocker_requirement_status,
              cf.family_json
            FROM candidate_family_rankings cfr
            JOIN candidate_families cf
              ON cf.candidate_family_id = cfr.candidate_family_id
            WHERE cfr.run_id = ?
            ORDER BY cfr.family_rank
            LIMIT ?
            """,
            (ranking_run_id, max_briefs),
        ).fetchall()
    return [
        {
            **dict(row),
            "rationale_json": parse_json_object(row["rationale_json"]),
            "family_json": parse_json_object(row["family_json"]),
        }
        for row in rows
    ]


def load_family_members(connection, ranking_run_id: str):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          cfm.candidate_family_id,
          cfm.member_role,
          cfm.support_json,
          aqh.adjudicated_queryless_hit_id,
          aqh.source_mechanism_instance_id,
          aqh.candidate_mechanism_instance_id,
          aqh.adjusted_score,
          aqh.adjusted_rank_within_source,
          qch.source_paper_id,
          qch.candidate_paper_id,
          qch.source_literature_family,
          qch.candidate_literature_family,
          qch.structural_similarity_score,
          qch.lexical_distance_score,
          qch.transfer_plausibility_score,
          qch.blocker_penalty_score,
          src.mechanism_label AS source_mechanism_label,
          src.mechanism_summary AS source_mechanism_summary,
          cand.mechanism_label AS candidate_mechanism_label,
          cand.mechanism_summary AS candidate_mechanism_summary,
          doc.source_json AS candidate_document_json
        FROM candidate_family_members cfm
        JOIN adjudicated_queryless_hits aqh
          ON aqh.adjudicated_queryless_hit_id = cfm.adjudicated_queryless_hit_id
        JOIN queryless_candidate_hits qch
          ON qch.queryless_candidate_hit_id = aqh.queryless_candidate_hit_id
        JOIN mechanism_instances src
          ON src.mechanism_instance_id = aqh.source_mechanism_instance_id
        JOIN mechanism_instances cand
          ON cand.mechanism_instance_id = aqh.candidate_mechanism_instance_id
        JOIN mechanism_retrieval_documents doc
          ON doc.mechanism_instance_id = aqh.candidate_mechanism_instance_id
         AND doc.run_id = qch.retrieval_run_id
         AND doc.retrieval_version = qch.retrieval_version
        WHERE cfm.run_id = ?
        ORDER BY cfm.candidate_family_id, aqh.adjusted_score DESC
        """,
        (ranking_run_id,),
    ).fetchall()
    by_family = defaultdict(list)
    for row in rows:
        record = dict(row)
        record["support_json"] = parse_json_object(row["support_json"])
        record["candidate_document_json"] = parse_json_object(row["candidate_document_json"])
        by_family[row["candidate_family_id"]].append(record)
    return by_family


def load_transfer_hypotheses(connection):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          candidate_family_id,
          mechanism_instance_id,
          target_domain,
          hypothesis_status,
          negative_transfer_rationale_json,
          rationale_json
        FROM transfer_hypotheses
        WHERE candidate_family_id IS NOT NULL
        ORDER BY candidate_family_id, transfer_hypothesis_id
        """
    ).fetchall()
    by_family = defaultdict(list)
    for row in rows:
        record = dict(row)
        record["negative_transfer_rationale_json"] = parse_json_array(
            row["negative_transfer_rationale_json"]
        )
        record["rationale_json"] = parse_json_object(row["rationale_json"])
        by_family[row["candidate_family_id"]].append(record)
    return by_family


def infer_required_assumptions(member):
    candidate_doc = member["candidate_document_json"]
    assumptions = list(candidate_doc.get("required_assumptions", []))
    for field_name in ("boundary_conditions", "capacity_limit"):
        assumptions.extend(
            candidate_doc.get("fingerprint_facets", {}).get(field_name, [])
        )
    return sorted(dict.fromkeys(assumptions))


def infer_fragility(member, hypotheses):
    candidate_doc = member["candidate_document_json"]
    fragility = list(candidate_doc.get("fragility_flags", []))
    fragility.extend(candidate_doc.get("failure_regimes", []))
    for hypothesis in hypotheses:
        fragility.extend(hypothesis["negative_transfer_rationale_json"])
    return sorted(dict.fromkeys(fragility))


def infer_observable_signals(member):
    facets = member["candidate_document_json"].get("fingerprint_facets", {})
    signals = []
    for key in ("trigger", "state_variables", "pricing_path", "execution_shape"):
        signals.extend(facets.get(key, []))
    return sorted(dict.fromkeys(signals))


def infer_minimal_dataset(member):
    facets = member["candidate_document_json"].get("fingerprint_facets", {})
    datasets = [
        "paper-backed mechanism summaries and section evidence",
        "time series covering " + ", ".join(facets.get("state_variables", [])[:2])
        if facets.get("state_variables")
        else "time series covering the candidate mechanism state variables",
        "event logs for " + ", ".join(facets.get("execution_shape", [])[:2])
        if facets.get("execution_shape")
        else "event logs for the target execution path",
    ]
    return [normalize_text(item) for item in datasets if item]


def infer_cheapest_validation(member):
    target_domain = member["candidate_literature_family"]
    source_family = member["source_literature_family"]
    return (
        f"Replay the {target_domain} transfer hypothesis against a small "
        f"{source_family}-anchored holdout slice and check whether the cited "
        "observable signals move in the predicted direction."
    )


def infer_failure_criteria(member, fragility):
    criteria = []
    if fragility:
        criteria.append("Any validation slice immediately triggers: " + ", ".join(fragility[:3]))
    criteria.append("The proposed signal disappears after transaction-cost and blocker adjustments.")
    criteria.append("The mechanism only recovers same-family obvious neighbors rather than cross-domain analogs.")
    return criteria


def infer_change_mind(member):
    return [
        "A stronger same-family explanation fully accounts for the observed edge.",
        "Required assumptions fail on the minimal validation slice.",
        "Analyst review finds the mechanism non-novel after examining the cited evidence and transfer path.",
    ]


def build_brief_payload(family, members, hypotheses):
    representative = next(
        (member for member in members if member["member_role"] == "representative_hypothesis"),
        members[0],
    )
    required_assumptions = infer_required_assumptions(representative)
    fragility = infer_fragility(representative, hypotheses)
    observable_signals = infer_observable_signals(representative)
    minimal_dataset = infer_minimal_dataset(representative)
    transfer_rationale = [
        normalize_text(item)
        for item in representative["support_json"].get("transfer_path", [])
        if item
    ]
    if not transfer_rationale:
        transfer_rationale.append(
            "Representative family member cleared the C13 hard gates with explicit transfer support."
        )

    brief = {
        "brief_name": family["family_name"],
        "mechanism_family": family["family_name"],
        "family_rank": family["family_rank"],
        "gate_status": family["gate_status"],
        "target_domain": family["family_json"].get("target_domain"),
        "transfer_rationale": transfer_rationale,
        "tradecore_mapping": representative["candidate_document_json"].get("mechanism_traits", {}).get(
            "tradecore_fit", "unknown"
        ),
        "required_assumptions": required_assumptions,
        "fragility_failure_regimes": fragility,
        "observable_target_signals": observable_signals,
        "minimal_dataset": minimal_dataset,
        "cheapest_validation_procedure": infer_cheapest_validation(representative),
        "failure_criteria": infer_failure_criteria(representative, fragility),
        "what_would_change_our_mind": infer_change_mind(representative),
        "representative_source_paper_id": representative["source_paper_id"],
        "representative_candidate_paper_id": representative["candidate_paper_id"],
        "representative_source_mechanism": representative["source_mechanism_label"],
        "representative_candidate_mechanism": representative["candidate_mechanism_label"],
        "representative_candidate_summary": normalize_text(representative["candidate_mechanism_summary"]),
        "analyst_informed_rank": representative["adjusted_rank_within_source"],
        "final_priority_score": family["final_priority_score"],
        "supporting_member_count": len(members),
        "transfer_hypothesis_count": len(hypotheses),
    }
    return brief


def render_markdown(brief):
    lines = [
        f"# {brief['brief_name']}",
        "",
        "## Summary",
        f"- Family rank: `{brief['family_rank']}`",
        f"- Gate status: `{brief['gate_status']}`",
        f"- Final priority score: `{brief['final_priority_score']:.4f}`",
        f"- Target domain: `{brief['target_domain']}`",
        f"- Tradecore mapping: `{brief['tradecore_mapping']}`",
        "",
    ]
    if brief["gate_status"] != "passed":
        lines.extend(
            [
                "## Provisional Status",
                "- This brief comes from a rejected C13 family and is intended for provisional analyst triage only.",
                "- Treat it as a bootstrap review packet, not as a passed-gates candidate claim.",
                "",
            ]
        )
    lines.extend(
        [
            "## Mechanism",
            f"- Representative source mechanism: `{brief['representative_source_mechanism']}`",
            f"- Representative candidate mechanism: `{brief['representative_candidate_mechanism']}`",
            f"- Candidate summary: {brief['representative_candidate_summary']}",
            "",
            "## Transfer Rationale",
        ]
    )
    for item in brief["transfer_rationale"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Required Assumptions"])
    for item in brief["required_assumptions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Fragility And Failure Regimes"])
    for item in brief["fragility_failure_regimes"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Observable Target Signals"])
    for item in brief["observable_target_signals"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Minimal Dataset"])
    for item in brief["minimal_dataset"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Cheapest Validation Procedure",
            f"- {brief['cheapest_validation_procedure']}",
            "",
            "## Failure Criteria",
        ]
    )
    for item in brief["failure_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## What Would Change Our Mind"])
    for item in brief["what_would_change_our_mind"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_brief_files(run_id: str, brief):
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id / "briefs"
    run_dir.mkdir(parents=True, exist_ok=True)
    brief_slug = slugify(brief["brief_name"])
    markdown_path = run_dir / f"{brief['family_rank']:02d}-{brief_slug}.md"
    json_path = run_dir / f"{brief['family_rank']:02d}-{brief_slug}.json"
    markdown_path.write_text(render_markdown(brief), encoding="utf-8")
    json_path.write_text(json.dumps(brief, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return markdown_path, json_path


def persist_brief(connection, run_id: str, brief_version: str, family, brief, markdown_path: Path):
    brief_status = "drafted" if brief["gate_status"] == "passed" else "provisional_drafted"
    connection.execute(
        """
        INSERT INTO strategy_briefs (
          candidate_family_id,
          candidate_family_ranking_id,
          run_id,
          brief_version,
          brief_name,
          brief_status,
          brief_rank,
          brief_markdown_path,
          brief_json,
          updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(candidate_family_id, run_id, brief_version) DO UPDATE SET
          candidate_family_ranking_id = excluded.candidate_family_ranking_id,
          brief_name = excluded.brief_name,
          brief_status = excluded.brief_status,
          brief_rank = excluded.brief_rank,
          brief_markdown_path = excluded.brief_markdown_path,
          brief_json = excluded.brief_json,
          updated_at = excluded.updated_at
        """,
        (
            family["candidate_family_id"],
            family["candidate_family_ranking_id"],
            run_id,
            brief_version,
            brief["brief_name"],
            brief_status,
            brief["family_rank"],
            str(markdown_path),
            json.dumps(brief, sort_keys=True),
            now_utc(),
        ),
    )


def update_strategy_candidate(connection, family, brief):
    connection.execute(
        """
        UPDATE strategy_candidates
        SET candidate_status = ?,
            review_notes = ?,
            updated_at = ?
        WHERE candidate_name = ?
          AND json_extract(candidate_json, '$.candidate_family_id') = ?
        """,
        (
            "briefed" if brief["gate_status"] == "passed" else "briefed_provisional",
            brief["cheapest_validation_procedure"],
            now_utc(),
            family["family_name"],
            family["candidate_family_id"],
        ),
    )


def summarize(run_id: str, ranking_run_id: str, briefs):
    target_domains = defaultdict(int)
    holdout_count = 0
    for brief in briefs:
        target_domains[brief["target_domain"]] += 1
        if any("holdout" in item.lower() for item in brief["transfer_rationale"]):
            holdout_count += 1
    return {
        "run_id": run_id,
        "ranking_run_id": ranking_run_id,
        "brief_count": len(briefs),
        "provisional_brief_count": sum(
            1 for brief in briefs if brief["gate_status"] != "passed"
        ),
        "target_domain_counts": dict(sorted(target_domains.items())),
        "briefs_with_holdout_language": holdout_count,
        "top_briefs": [
            {
                "brief_name": brief["brief_name"],
                "family_rank": brief["family_rank"],
                "target_domain": brief["target_domain"],
            }
            for brief in briefs[:5]
        ],
    }


def write_summary(run_id: str, summary):
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "strategy_brief_summary.json"
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
        run_id = ensure_run(
            connection,
            args.run_id,
            args.ranking_run_id,
            args.brief_version,
            args.max_briefs,
        )
        connection.commit()

        ranked_families = load_ranked_families(
            connection,
            args.ranking_run_id,
            args.max_briefs,
            args.include_provisional_rejected,
        )
        if not ranked_families:
            raise SystemExit(
                "no passed candidate_family_rankings found for the requested run; complete C13 before running C14"
            )
        members_by_family = load_family_members(connection, args.ranking_run_id)
        hypotheses_by_family = load_transfer_hypotheses(connection)

        briefs = []
        connection.execute("BEGIN")
        try:
            for family in ranked_families:
                members = members_by_family[family["candidate_family_id"]]
                hypotheses = hypotheses_by_family[family["candidate_family_id"]]
                brief = build_brief_payload(family, members, hypotheses)
                markdown_path, _ = write_brief_files(run_id, brief)
                persist_brief(connection, run_id, args.brief_version, family, brief, markdown_path)
                update_strategy_candidate(connection, family, brief)
                briefs.append(brief)

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

    summary = summarize(run_id, args.ranking_run_id, briefs)
    summary_path = write_summary(run_id, summary)
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
