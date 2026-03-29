#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DOWNSTREAM_DIR = Path(__file__).resolve().parent


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
        help="Maximum number of final cards to generate in the final step.",
    )
    parser.add_argument(
        "--section-source-run-id",
        default=None,
        help="Optional extraction run id whose accepted papers should be section-parsed before downstream analysis.",
    )
    parser.add_argument(
        "--include-legacy-briefs",
        action="store_true",
        help="Also generate the older strategy brief / Gate C artifacts for compatibility.",
    )
    return parser.parse_args()


def run_python(script_name: str, args: list[str], extra_packages: list[str] | None = None):
    if extra_packages:
        cmd = ["uv", "run"]
        for package_name in extra_packages:
            cmd.extend(["--with", package_name])
        cmd.extend([sys.executable, str(ROOT / "scripts" / script_name), *args])
    else:
        cmd = [sys.executable, str(ROOT / "scripts" / script_name), *args]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    stdout = completed.stdout.strip()
    return json.loads(stdout) if stdout.startswith("{") else {"stdout": stdout}


def main():
    args = parse_args()
    db_path = str(Path(args.db_path).resolve())

    run_ids = {
        "section_run_id": f"{args.run_prefix}-c07",
        "normalization_run_id": f"{args.run_prefix}-c08",
        "exposure_run_id": f"{args.run_prefix}-c09",
        "retrieval_run_id": f"{args.run_prefix}-c10",
        "queryless_run_id": f"{args.run_prefix}-c11",
        "bootstrap_labels_path": str(
            ROOT / "data" / "structural-analogy" / "runs" / f"{args.run_prefix}-c11" / "bootstrap_queryless_labels.jsonl"
        ),
        "adjudication_run_id": f"{args.run_prefix}-c12-bootstrap",
        "ranking_run_id": f"{args.run_prefix}-c13",
        "edge_card_run_id": f"{args.run_prefix}-c14-edge",
        "brief_run_id": f"{args.run_prefix}-c14",
        "review_prep_run_id": f"{args.run_prefix}-c16",
    }

    summary = {
        "db_path": db_path,
        "run_prefix": args.run_prefix,
        "max_briefs": args.max_briefs,
    }
    # @context decision -- The reset path prioritizes section-backed evidence
    # before downstream ranking. We keep the existing chain intact, but a run can
    # now front-load full-text section parsing for the accepted extraction slice.
    if args.section_source_run_id:
        summary["section_prep"] = run_python(
            "prepare_sections_for_extraction_run.py",
            [
                "--db-path",
                db_path,
                "--extraction-run-id",
                args.section_source_run_id,
            ],
            extra_packages=["pypdf"],
        )
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
    # @context decision -- Edge cards are now the default product surface.
    # Legacy strategy briefs remain optional compatibility output rather than
    # the primary downstream artifact.
    summary["edge_cards"] = run_python(
        "generate_edge_cards.py",
        [
            "--db-path",
            db_path,
            "--ranking-run-id",
            run_ids["ranking_run_id"],
            "--run-id",
            run_ids["edge_card_run_id"],
            "--max-edge-cards",
            str(args.max_briefs),
        ],
    )
    if args.include_legacy_briefs:
        summary["briefs"] = run_python(
            str(DOWNSTREAM_DIR / "generate_strategy_briefs.py"),
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
            # @context requirement -- the archived downstream review flow has to
            # call its archived Gate C prep script explicitly so the preserved
            # orchestrator does not silently depend on removed root-level files.
            str(DOWNSTREAM_DIR / "prepare_gate_c_review.py"),
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
