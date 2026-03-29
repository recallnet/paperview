#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path

from edge_semantic_validity import semantic_validity


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"


def parse_args():
    parser = argparse.ArgumentParser(description="Export semantic trace for top ranked families.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--ranking-run-id", required=True)
    parser.add_argument("--extraction-run-id", required=True)
    parser.add_argument("--edge-run-id", default=None)
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


def parse_json(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded


def main():
    args = parse_args()
    db = sqlite3.connect(str(Path(args.db_path).resolve()))
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT
          cfr.family_rank,
          cf.family_name,
          cfr.gate_status,
          cfr.rationale_json,
          qch.queryless_candidate_hit_id,
          qch.source_paper_id,
          qch.candidate_paper_id,
          mi.mechanism_instance_id,
          mi.mechanism_json,
          pe.extraction_json,
          ec.edge_json
        FROM candidate_family_rankings cfr
        JOIN candidate_families cf
          ON cf.candidate_family_id = cfr.candidate_family_id
        JOIN candidate_family_members cfm
          ON cfm.candidate_family_id = cf.candidate_family_id
         AND cfm.run_id = cfr.run_id
        JOIN adjudicated_queryless_hits aqh
          ON aqh.adjudicated_queryless_hit_id = cfm.adjudicated_queryless_hit_id
        JOIN queryless_candidate_hits qch
          ON qch.queryless_candidate_hit_id = aqh.queryless_candidate_hit_id
        JOIN mechanism_instances mi
          ON mi.mechanism_instance_id = aqh.candidate_mechanism_instance_id
        LEFT JOIN paper_extractions pe
          ON pe.paper_id = mi.paper_id
         AND pe.run_id = ?
        LEFT JOIN edge_cards ec
          ON ec.candidate_family_ranking_id = cfr.candidate_family_ranking_id
         AND ec.run_id = COALESCE(?, ec.run_id)
        WHERE cfr.run_id = ?
        GROUP BY cfr.candidate_family_ranking_id
        ORDER BY cfr.family_rank
        LIMIT ?
        """,
        (args.extraction_run_id, args.edge_run_id, args.ranking_run_id, args.limit),
    ).fetchall()
    report = []
    for row in rows:
        mechanism_json = parse_json(row["mechanism_json"])
        extraction_json = parse_json(row["extraction_json"])
        edge_json = parse_json(row["edge_json"])
        semantic_result = semantic_validity(mechanism_json or extraction_json)
        report.append(
            {
                "family_rank": row["family_rank"],
                "family_name": row["family_name"],
                "gate_status": row["gate_status"],
                "raw_source_snippet": {
                    "paper_id": row["candidate_paper_id"],
                    "mechanism_summary": extraction_json.get("mechanism_summary"),
                    "invariant_statement": extraction_json.get("invariant_statement"),
                    "market_object": extraction_json.get("market_object"),
                    "wrong_actor": extraction_json.get("wrong_actor"),
                    "cheap_validation_step": extraction_json.get("cheap_validation_step"),
                },
                "raw_model_extraction_output": extraction_json,
                "normalized_row_after_ingestion": mechanism_json,
                "semantic_validity_result": semantic_result,
                "final_ranked_or_card_fields": {
                    "rationale": parse_json(row["rationale_json"]),
                    "edge_json": edge_json,
                },
            }
        )
    output_dir = ROOT / "data" / "structural-analogy" / "runs" / args.ranking_run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "semantic_trace.json"
    md_path = output_dir / "semantic_trace.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [f"# Semantic Trace `{args.ranking_run_id}`", ""]
    for item in report:
        lines.extend(
            [
                f"## Rank {item['family_rank']} `{item['family_name']}`",
                f"- gate_status: `{item['gate_status']}`",
                f"- raw source snippet: `{json.dumps(item['raw_source_snippet'], sort_keys=True)}`",
                f"- raw model output: `{json.dumps(item['raw_model_extraction_output'], sort_keys=True)[:1500]}`",
                f"- normalized row: `{json.dumps(item['normalized_row_after_ingestion'], sort_keys=True)[:1500]}`",
                f"- semantic validity: `{json.dumps(item['semantic_validity_result'], sort_keys=True)}`",
                f"- final fields: `{json.dumps(item['final_ranked_or_card_fields'], sort_keys=True)[:1500]}`",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "count": len(report)}, indent=2))


if __name__ == "__main__":
    main()
