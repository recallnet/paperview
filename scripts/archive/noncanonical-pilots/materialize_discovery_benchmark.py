#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_DEFINITION_PATH = ROOT / "configs" / "discovery_benchmark_definition.json"

VALID_BUCKETS = {
    "lexically_near_structurally_near",
    "lexically_near_structurally_far",
    "lexically_far_structurally_near",
    "lexically_far_structurally_far",
}
VALID_PAIR_KINDS = {"obvious_neighbor", "true_far_analog", "hard_negative"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Materialize the checked-in discovery benchmark into benchmark_pairs."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--definition-path",
        default=str(DEFAULT_DEFINITION_PATH),
        help="Path to the checked-in benchmark definition JSON.",
    )
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_definition(definition):
    seen = set()
    for pair in definition["pairs"]:
        key = pair["benchmark_key"]
        if key in seen:
            raise SystemExit(f"duplicate benchmark_key: {key}")
        seen.add(key)

        if pair["benchmark_bucket"] not in VALID_BUCKETS:
            raise SystemExit(f"invalid benchmark_bucket for {key}: {pair['benchmark_bucket']}")
        if pair["pair_kind"] not in VALID_PAIR_KINDS:
            raise SystemExit(f"invalid pair_kind for {key}: {pair['pair_kind']}")

        source = pair["source_paper"]
        candidate = pair["candidate_paper"]
        for side_name, side in (("source", source), ("candidate", candidate)):
            if not side.get("paper_id"):
                raise SystemExit(f"{key}: {side_name}_paper.paper_id is required")
            if not side.get("literature_family"):
                raise SystemExit(f"{key}: {side_name}_paper.literature_family is required")
            if not side.get("insight_type"):
                raise SystemExit(f"{key}: {side_name}_paper.insight_type is required")


def materialize(connection, definition):
    connection.execute("BEGIN")
    try:
        # @context decision -- C04 stores benchmark anchors at the paper level first because
        # mechanism-instance persistence does not exist until C05. The benchmark must still be
        # queryable and adjudicated now, so benchmark_pairs carries paper ids as the stable bridge.
        connection.execute("DELETE FROM benchmark_pairs")
        for pair in definition["pairs"]:
            benchmark_json = {
                "version": definition["version"],
                "source_paper": pair["source_paper"],
                "candidate_paper": pair["candidate_paper"],
                "adjudication": pair["adjudication"],
            }
            connection.execute(
                """
                INSERT INTO benchmark_pairs (
                  benchmark_key,
                  source_paper_id,
                  candidate_paper_id,
                  benchmark_bucket,
                  pair_kind,
                  label_status,
                  benchmark_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pair["benchmark_key"],
                    pair["source_paper"]["paper_id"],
                    pair["candidate_paper"]["paper_id"],
                    pair["benchmark_bucket"],
                    pair["pair_kind"],
                    pair["label_status"],
                    json.dumps(benchmark_json, sort_keys=True),
                ),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def summarize(definition):
    bucket_counts = {}
    kind_counts = {}
    for pair in definition["pairs"]:
        bucket_counts[pair["benchmark_bucket"]] = bucket_counts.get(pair["benchmark_bucket"], 0) + 1
        kind_counts[pair["pair_kind"]] = kind_counts.get(pair["pair_kind"], 0) + 1
    return {
        "version": definition["version"],
        "pair_count": len(definition["pairs"]),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "pair_kind_counts": dict(sorted(kind_counts.items())),
        "acceptance_thresholds": definition["acceptance_thresholds"],
    }


def main():
    args = parse_args()
    definition = load_json(Path(args.definition_path).resolve())
    validate_definition(definition)

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    try:
        materialize(connection, definition)
    finally:
        connection.close()

    print(json.dumps(summarize(definition), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
