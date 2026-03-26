#!/usr/bin/env python3

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_MINING_VERSION = "c11-queryless-v1"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create provisional bootstrap adjudication labels from queryless candidate hits."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--queryless-run-id",
        required=True,
        help="Queryless mining run id produced by mine_queryless_candidates.py.",
    )
    parser.add_argument(
        "--output-path",
        default=None,
        help="Optional explicit JSONL path for the bootstrap labels.",
    )
    parser.add_argument(
        "--mining-version",
        default=DEFAULT_MINING_VERSION,
        help="Queryless mining contract version to read.",
    )
    return parser.parse_args()


def now_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def clamp(value):
    return max(0.0, min(1.0, value))


def load_hits(connection, queryless_run_id: str, mining_version: str):
    connection.row_factory = sqlite3.Row
    return connection.execute(
        """
        SELECT
          qch.queryless_candidate_hit_id,
          qch.mining_mode,
          qch.source_mechanism_instance_id,
          qch.candidate_mechanism_instance_id,
          qch.rank_within_source,
          qch.is_cross_family,
          qch.structural_similarity_score,
          qch.lexical_distance_score,
          qch.transfer_plausibility_score,
          qch.blocker_penalty_score,
          qch.reranker_score,
          qch.source_literature_family,
          qch.candidate_literature_family,
          qch.source_evaluation_split,
          qch.candidate_evaluation_split,
          doc.source_json
        FROM queryless_candidate_hits qch
        JOIN mechanism_retrieval_documents doc
          ON doc.mechanism_instance_id = qch.candidate_mechanism_instance_id
         AND doc.run_id = qch.retrieval_run_id
         AND doc.retrieval_version = qch.retrieval_version
        WHERE qch.run_id = ?
          AND qch.mining_version = ?
        ORDER BY qch.queryless_candidate_hit_id
        """,
        (queryless_run_id, mining_version),
    ).fetchall()


def parse_json_object(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {}


def bootstrap_score(hit, candidate_doc):
    traits = candidate_doc.get("mechanism_traits", {})
    tradecore_fit = {"high": 1.0, "medium": 0.6, "low": 0.2}.get(
        traits.get("tradecore_fit", "low"),
        0.2,
    )
    novelty_bonus = 0.08 if hit["rank_within_source"] <= 3 else 0.0
    evidence_bonus = 0.06 if candidate_doc.get("section_labels") else 0.0
    return clamp(
        0.34 * hit["reranker_score"]
        + 0.22 * hit["structural_similarity_score"]
        + 0.16 * hit["lexical_distance_score"]
        + 0.16 * hit["transfer_plausibility_score"]
        + 0.12 * tradecore_fit
        + novelty_bonus
        + evidence_bonus
        - 0.18 * hit["blocker_penalty_score"]
    )


def build_label_record(hit):
    candidate_doc = parse_json_object(hit["source_json"])
    bootstrap = bootstrap_score(hit, candidate_doc)
    traits = candidate_doc.get("mechanism_traits", {})
    tradecore_fit = traits.get("tradecore_fit", "low")
    structurally_relevant = hit["structural_similarity_score"] >= 0.6
    non_obvious = hit["lexical_distance_score"] >= 0.68
    accept = bootstrap >= 0.46
    worth_strategy_brief = (
        bootstrap >= 0.52
        and tradecore_fit in {"medium", "high"}
        and hit["blocker_penalty_score"] <= 0.42
    )
    genuinely_new = non_obvious and bootstrap >= 0.5

    interesting_reasons = []
    weak_reasons = []
    if tradecore_fit in {"medium", "high"}:
        interesting_reasons.append("tradecore fit survives legacy bootstrap screen")
    if candidate_doc.get("section_labels"):
        interesting_reasons.append("abstract-backed evidence span is available")
    if hit["rank_within_source"] <= 3:
        interesting_reasons.append("top-ranked queryless analog for the source mechanism")
    if non_obvious:
        interesting_reasons.append("lexically non-obvious within the live q-fin slice")
    if hit["blocker_penalty_score"] > 0.42:
        weak_reasons.append("blocker burden remains high")
    if tradecore_fit == "low":
        weak_reasons.append("tradecore fit remains low")
    if hit["transfer_plausibility_score"] < 0.5:
        weak_reasons.append("transfer path still looks weak under bootstrap scoring")

    # @context requirement -- Bootstrap labels are only a provisional queue
    # initializer for the first live downstream materialization. They must stay
    # clearly distinguishable from human Gate C review and should bias toward a
    # small reviewable queue rather than fabricating broad confidence.
    return {
        "queryless_candidate_hit_id": hit["queryless_candidate_hit_id"],
        "accept": accept,
        "structurally_relevant": structurally_relevant,
        "non_obvious": non_obvious,
        "genuinely_new": genuinely_new,
        "worth_strategy_brief": worth_strategy_brief,
        "interesting_reasons": interesting_reasons[:3],
        "weak_reasons": weak_reasons[:3],
        "notes": f"bootstrap_score={bootstrap:.4f}; tradecore_fit={tradecore_fit}",
    }


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_path = (
        Path(args.output_path).resolve()
        if args.output_path
        else DEFAULT_OUTPUT_DIR
        / args.queryless_run_id
        / "bootstrap_queryless_labels.jsonl"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    try:
        hits = load_hits(connection, args.queryless_run_id, args.mining_version)
    finally:
        connection.close()

    if not hits:
        raise SystemExit(
            "no queryless_candidate_hits found for the requested run; complete C11 before bootstrapping labels"
        )

    records = [build_label_record(hit) for hit in hits]
    output_path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )
    positive_count = sum(1 for record in records if record["accept"])
    briefworthy_count = sum(1 for record in records if record["worth_strategy_brief"])
    print(
        json.dumps(
            {
                "queryless_run_id": args.queryless_run_id,
                "label_count": len(records),
                "accepted_count": positive_count,
                "worth_strategy_brief_count": briefworthy_count,
                "output_path": str(output_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
