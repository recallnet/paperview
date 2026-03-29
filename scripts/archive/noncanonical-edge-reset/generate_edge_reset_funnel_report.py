#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_RUNS_ROOT = ROOT / "data" / "structural-analogy" / "runs"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a concrete funnel and rejection report for an edge reset slice."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


def load_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def raw_extraction_counts(rows):
    empty = 0
    non_empty = 0
    for row in rows:
        if row.get("parse_status") != "ok":
            continue
        if "mechanism_instances" in row:
            instances = row.get("mechanism_instances") or []
            if instances:
                non_empty += 1
            else:
                empty += 1
            continue
        extraction = row.get("extraction")
        if extraction:
            non_empty += 1
        else:
            empty += 1
    return {"raw_extraction_empty": empty, "raw_extraction_non_empty": non_empty}


def aggregate_provenance(connection, extraction_run_id: str):
    counts = {"explicit_from_model": 0, "explicit_from_source_snippet": 0, "inferred": 0, "defaulted": 0, "missing": 0}
    rows = connection.execute(
        """
        SELECT mechanism_json
        FROM mechanism_instances
        WHERE run_id = ? AND lifecycle_status = 'active'
        """,
        (extraction_run_id,),
    ).fetchall()
    for (mechanism_json,) in rows:
        if not mechanism_json:
            continue
        payload = json.loads(mechanism_json)
        provenance = payload.get("field_provenance", {})
        for value in provenance.values():
            if value in counts:
                counts[value] += 1
            elif value in {"inferred_from_normalizer", "inferred_from_card_generator"}:
                counts["inferred"] += 1
            elif value in {"defaulted"}:
                counts["defaulted"] += 1
            else:
                counts["missing"] += 1
    return counts


def load_survivors(connection, ranking_run_id: str, extraction_run_id: str, edge_run_id: str, limit: int):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          cfr.family_rank,
          cf.family_name,
          cfr.gate_status,
          cfr.rationale_json,
          mi.mechanism_json,
          pe.extraction_json,
          ec.edge_json
        FROM candidate_family_rankings cfr
        JOIN candidate_families cf
          ON cf.candidate_family_id = cfr.candidate_family_id
        LEFT JOIN candidate_family_members cfm
          ON cfm.candidate_family_id = cf.candidate_family_id AND cfm.run_id = cfr.run_id
        LEFT JOIN adjudicated_queryless_hits aqh
          ON aqh.adjudicated_queryless_hit_id = cfm.adjudicated_queryless_hit_id
        LEFT JOIN mechanism_instances mi
          ON mi.mechanism_instance_id = aqh.candidate_mechanism_instance_id
        LEFT JOIN paper_extractions pe
          ON pe.extraction_id = mi.source_extraction_id AND pe.run_id = ?
        LEFT JOIN edge_cards ec
          ON ec.candidate_family_ranking_id = cfr.candidate_family_ranking_id AND ec.run_id = ?
        WHERE cfr.run_id = ?
          AND cfr.gate_status IN ('passed', 'blocked', 'almost_there')
        GROUP BY cfr.candidate_family_ranking_id
        ORDER BY cfr.family_rank
        LIMIT ?
        """,
        (extraction_run_id, edge_run_id, ranking_run_id, limit),
    ).fetchall()
    survivors = []
    for row in rows:
        survivors.append(
            {
                "family_rank": row["family_rank"],
                "family_name": row["family_name"],
                "gate_status": row["gate_status"],
                "source_snippet": json.loads(row["extraction_json"]) if row["extraction_json"] else {},
                "field_provenance": (json.loads(row["mechanism_json"]).get("field_provenance", {}) if row["mechanism_json"] else {}),
                "final_rendered_card": json.loads(row["edge_json"]) if row["edge_json"] else {},
            }
        )
    return survivors


def main():
    args = parse_args()
    run_prefix = args.run_prefix
    runs_root = DEFAULT_RUNS_ROOT
    responses_path = runs_root / run_prefix / "responses.jsonl"
    gate_summary_path = runs_root / run_prefix / "gate_summary.json"
    ingest_summary_path = runs_root / run_prefix / "ingest_summary.json"
    ranking_summary_path = runs_root / f"{run_prefix}-c13" / "candidate_family_ranking_summary.json"
    edge_summary_path = runs_root / f"{run_prefix}-c13-edge-cards" / "edge_cards.json"
    rejection_path = runs_root / f"{run_prefix}-c13-edge-cards" / "rejection_report.json"

    response_rows = load_jsonl(responses_path)
    raw_counts = raw_extraction_counts(response_rows)
    gate_summary = json.loads(gate_summary_path.read_text(encoding="utf-8")) if gate_summary_path.exists() else {}
    ingest_summary = json.loads(ingest_summary_path.read_text(encoding="utf-8")) if ingest_summary_path.exists() else {}
    ranking_summary = json.loads(ranking_summary_path.read_text(encoding="utf-8")) if ranking_summary_path.exists() else {}
    edge_summary = json.loads(edge_summary_path.read_text(encoding="utf-8")) if edge_summary_path.exists() else {}
    rejection_rows = json.loads(rejection_path.read_text(encoding="utf-8")) if rejection_path.exists() else []

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    try:
        provenance = aggregate_provenance(connection, run_prefix)
        survivors = load_survivors(
            connection,
            f"{run_prefix}-c13",
            run_prefix,
            f"{run_prefix}-c14",
            args.limit,
        )
    finally:
        connection.close()

    completeness_fail = ingest_summary.get("invalid", 0)
    completeness_pass = gate_summary.get("reviewed_count", 0) - completeness_fail
    report = {
        "run_prefix": run_prefix,
        "funnel": {
            "papers_selected": len(response_rows),
            **raw_counts,
            "extraction_completeness_pass": completeness_pass,
            "extraction_completeness_fail": completeness_fail,
            "reached_normalization": ingest_summary.get("inserted", 0) + ingest_summary.get("updated", 0),
            "failed_semantic_validity": ranking_summary.get("semantic_gate_reject_count", 0),
            "failed_explicit_transfer_path": sum(
                reason.get("count", 0)
                for family in rejection_rows
                for reason in family.get("rejection_reasons", [])
                if reason.get("gate") == "failed_explicit_transfer_path"
            ),
            "failed_evidence_threshold": sum(
                reason.get("count", 0)
                for family in rejection_rows
                for reason in family.get("rejection_reasons", [])
                if reason.get("gate") == "failed_evidence_threshold"
            ),
            "failed_catastrophic_blocker": sum(
                reason.get("count", 0)
                for family in rejection_rows
                for reason in family.get("rejection_reasons", [])
                if reason.get("gate") == "failed_catastrophic_blocker"
            ),
            "top_edge": len(edge_summary.get("top_edge", [])),
            "almost_there": len(edge_summary.get("almost_there", [])),
            "suppressed_interesting": len(edge_summary.get("suppressed", [])),
            "rejected": len(rejection_rows),
        },
        "provenance_counts": provenance,
        "survivors": survivors,
        "semantic_top_failure_reasons": ranking_summary.get("semantic_gate_top_failure_reasons", []),
    }

    output_dir = runs_root / run_prefix
    md_path = output_dir / "funnel_report.md"
    json_path = output_dir / "funnel_report.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [f"# Funnel Report `{run_prefix}`", "", "## Funnel"]
    for key, value in report["funnel"].items():
        lines.append(f"- {key.replace('_', ' ')}: `{value}`")
    lines.extend(["", "## Provenance"])
    for key, value in provenance.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Survivors"])
    if not survivors:
        lines.append("- none")
    for survivor in survivors:
        lines.extend(
            [
                f"- `{survivor['family_name']}` (`{survivor['gate_status']}`)",
                f"  source snippet: `{json.dumps(survivor['source_snippet'], sort_keys=True)[:1200]}`",
                f"  field provenance: `{json.dumps(survivor['field_provenance'], sort_keys=True)}`",
                f"  final card: `{json.dumps(survivor['final_rendered_card'], sort_keys=True)[:1200]}`",
            ]
        )
    lines.extend(["", "## Top Semantic Failures"])
    for item in report["semantic_top_failure_reasons"][:10]:
        lines.append(f"- `{item['reason']}`: `{item['count']}`")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path)}, indent=2))


if __name__ == "__main__":
    main()
