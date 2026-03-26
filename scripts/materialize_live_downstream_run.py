#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Materialize the first live downstream mechanism-to-brief run from the reconciled local store."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--run-prefix",
        default="live-bootstrap",
        help="Prefix used to derive run ids for the downstream chain.",
    )
    parser.add_argument(
        "--max-briefs",
        type=int,
        default=10,
        help="Maximum number of briefs to generate in the final step.",
    )
    return parser.parse_args()


def run_python(script_name: str, args: list[str]):
    cmd = [sys.executable, str(ROOT / "scripts" / script_name), *args]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    stdout = completed.stdout.strip()
    return json.loads(stdout) if stdout.startswith("{") else {"stdout": stdout}


def main():
    args = parse_args()
    db_path = str(Path(args.db_path).resolve())

    run_ids = {
        "normalization_run_id": f"{args.run_prefix}-c08",
        "exposure_run_id": f"{args.run_prefix}-c09",
        "retrieval_run_id": f"{args.run_prefix}-c10",
        "queryless_run_id": f"{args.run_prefix}-c11",
        "bootstrap_labels_path": str(
            ROOT / "data" / "structural-analogy" / "runs" / f"{args.run_prefix}-c11" / "bootstrap_queryless_labels.jsonl"
        ),
        "adjudication_run_id": f"{args.run_prefix}-c12-bootstrap",
        "ranking_run_id": f"{args.run_prefix}-c13",
        "brief_run_id": f"{args.run_prefix}-c14",
        "review_prep_run_id": f"{args.run_prefix}-c16",
    }

    summary = {
        "db_path": db_path,
        "run_prefix": args.run_prefix,
        "max_briefs": args.max_briefs,
    }
    summary["normalization"] = run_python(
        "normalize_mechanism_fingerprints.py",
        ["--db-path", db_path, "--run-id", run_ids["normalization_run_id"]],
    )
    summary["exposure"] = run_python(
        "score_mechanism_exposure.py",
        ["--db-path", db_path, "--run-id", run_ids["exposure_run_id"]],
    )
    summary["retrieval"] = run_python(
        "build_retrieval_stack.py",
        ["--db-path", db_path, "--run-id", run_ids["retrieval_run_id"]],
    )
    summary["queryless"] = run_python(
        "mine_queryless_candidates.py",
        [
            "--db-path",
            db_path,
            "--retrieval-run-id",
            run_ids["retrieval_run_id"],
            "--run-id",
            run_ids["queryless_run_id"],
        ],
    )
    summary["bootstrap_labels"] = run_python(
        "bootstrap_queryless_labels.py",
        [
            "--db-path",
            db_path,
            "--queryless-run-id",
            run_ids["queryless_run_id"],
            "--output-path",
            run_ids["bootstrap_labels_path"],
        ],
    )
    summary["adjudication"] = run_python(
        "run_analyst_adjudication.py",
        [
            "--db-path",
            db_path,
            "--queryless-run-id",
            run_ids["queryless_run_id"],
            "--labels-path",
            run_ids["bootstrap_labels_path"],
            "--run-id",
            run_ids["adjudication_run_id"],
            "--created-by",
            "bootstrap-heuristic",
        ],
    )
    summary["ranking"] = run_python(
        "build_candidate_family_ranking.py",
        [
            "--db-path",
            db_path,
            "--adjudication-run-id",
            run_ids["adjudication_run_id"],
            "--run-id",
            run_ids["ranking_run_id"],
        ],
    )
    summary["briefs"] = run_python(
        "generate_strategy_briefs.py",
        [
            "--db-path",
            db_path,
            "--ranking-run-id",
            run_ids["ranking_run_id"],
            "--run-id",
            run_ids["brief_run_id"],
            "--max-briefs",
            str(args.max_briefs),
            "--include-provisional-rejected",
        ],
    )
    summary["gate_c_prep"] = run_python(
        "prepare_gate_c_review.py",
        [
            "--db-path",
            db_path,
            "--brief-run-id",
            run_ids["brief_run_id"],
            "--run-id",
            run_ids["review_prep_run_id"],
            "--max-briefs",
            str(args.max_briefs),
        ],
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
