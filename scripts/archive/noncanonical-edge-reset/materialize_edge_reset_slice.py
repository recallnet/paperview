#!/usr/bin/env python3

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path


ARCHIVE_ROOT = Path(__file__).resolve().parent.parent
# @context requirement -- Archived runners live under scripts/archive/... so the
# old parent.parent root calculation now lands on the archive directory instead
# of the repo root. Use parents[3] to keep historical workflows pointed at the
# real data/, prompts/, and sql/ surfaces.
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_PROMPT_PATH = ROOT / "prompts" / "edge-extraction-v26.md"
DEFAULT_SCHEMA_PATH = ROOT / "schemas" / "edge_extraction.schema.json"
DEFAULT_RUNS_ROOT = ROOT / "data" / "structural-analogy" / "runs"
RANKING_STACK_DIR = ARCHIVE_ROOT / "noncanonical-ranking-stack"
EXTRACTION_DIR = ARCHIVE_ROOT / "noncanonical-extraction-workflow"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the full section-backed edge reset slice end-to-end."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--paper-ids-path", required=True)
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--prompt-path", default=str(DEFAULT_PROMPT_PATH))
    parser.add_argument("--schema-path", default=str(DEFAULT_SCHEMA_PATH))
    parser.add_argument("--prompt-version", default=None)
    parser.add_argument("--response-contract-version", default=None)
    parser.add_argument("--max-requests", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--temperature", type=float, default=0.0)
    return parser.parse_args()


def infer_prompt_version(prompt_path: Path):
    return prompt_path.stem


def infer_response_contract_version(prompt_version: str):
    return f"{prompt_version}-batch-v1"


def run_cmd(cmd, cwd=ROOT):
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    if stdout.startswith("{"):
        return json.loads(stdout)
    return {"stdout": stdout}


def load_paper_ids(path: Path):
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def infer_focus(text: str):
    lowered = text.lower()
    tags = []
    mapping = [
        ("prediction_or_event_market", ["prediction market", "event market", "pari-mutuel"]),
        ("auction_and_allocation", ["auction", "allocation", "bid"]),
        ("parity_and_arbitrage", ["arbitrage", "parity", "cointegrat", "cross-market"]),
        (
            "orderbook_queue_liquidity",
            ["limit order", "order book", "queue", "liquidity", "spread", "market microstructure", "price impact"],
        ),
        ("amm_blockchain_settlement", ["blockchain", "amm", "liquidity pool", "settlement", "bridge"]),
    ]
    for tag, keys in mapping:
        if any(key in lowered for key in keys):
            tags.append(tag)
    return tags or ["edge_reset_strong_slice"]


def label_score(label: str):
    priority_patterns = [
        r"introduction",
        r"background",
        r"motivation",
        r"market",
        r"data",
        r"model",
        r"setup",
        r"assumption",
        r"mechanism",
        r"liquidity",
        r"order",
        r"queue",
        r"auction",
        r"pari",
        r"prediction",
        r"settlement",
        r"result",
        r"discussion",
        r"conclusion",
        r"proof",
        r"appendix",
        r"limitation",
        r"robust",
    ]
    score = 0
    for index, pattern in enumerate(priority_patterns):
        if re.search(pattern, label or "", re.I):
            score += 100 - index
    if (label or "").lower() == "front_matter":
        score -= 50
    return score


def build_section_backed_batch(db_path: Path, paper_ids, output_path: Path):
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        placeholders = ", ".join("?" for _ in paper_ids)
        papers = connection.execute(
            f"""
            SELECT
              paper_id,
              title,
              abstract,
              primary_category,
              published_at,
              updated_at,
              ingest_status,
              literature_family,
              evaluation_split
            FROM papers
            WHERE paper_id IN ({placeholders})
            """,
            paper_ids,
        ).fetchall()
        sections = connection.execute(
            f"""
            SELECT
              paper_id,
              section_label,
              section_order,
              content_text
            FROM paper_sections
            WHERE paper_id IN ({placeholders})
            """,
            paper_ids,
        ).fetchall()
    finally:
        connection.close()

    paper_by_id = {row["paper_id"]: row for row in papers}
    sections_by_paper = {}
    for row in sections:
        sections_by_paper.setdefault(row["paper_id"], []).append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for paper_id in paper_ids:
            row = paper_by_id[paper_id]
            chosen_sections = sorted(
                sections_by_paper.get(paper_id, []),
                key=lambda item: (-label_score(item["section_label"]), item["section_order"]),
            )[:6]
            section_snippets = []
            evidence_lines = []
            for section in chosen_sections:
                text = " ".join((section["content_text"] or "").split())
                if not text:
                    continue
                snippet = text[:1200]
                section_snippets.append(
                    {
                        "section_label": section["section_label"],
                        "section_order": section["section_order"],
                        "snippet": snippet,
                    }
                )
                evidence_lines.append(f"[{section['section_label']}] {snippet[:400]}")
            combined_text = f"{row['title'] or ''} {row['abstract'] or ''}"
            payload = {
                "paper_id": row["paper_id"],
                "title": row["title"],
                "abstract": row["abstract"],
                "primary_category": row["primary_category"],
                "published_at": row["published_at"],
                "updated_at": row["updated_at"],
                "ingest_status": row["ingest_status"],
                "literature_family": row["literature_family"],
                "evaluation_split": row["evaluation_split"],
                "section_snippets": section_snippets,
                "section_evidence": "\n\n".join(evidence_lines[:4]),
                "edge_focus": infer_focus(combined_text),
                "selection_reason": "materialized_edge_reset_slice",
            }
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def accepted_paper_ids(path: Path):
    return [
        json.loads(line)["paper_id"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    paper_ids_path = Path(args.paper_ids_path).resolve()
    prompt_path = Path(args.prompt_path).resolve()
    schema_path = Path(args.schema_path).resolve()
    prompt_version = args.prompt_version or infer_prompt_version(prompt_path)
    response_contract_version = (
        args.response_contract_version or infer_response_contract_version(prompt_version)
    )
    paper_ids = load_paper_ids(paper_ids_path)
    if args.max_requests is not None:
        paper_ids = paper_ids[: args.max_requests]

    pilot_dir = ROOT / "data" / "structural-analogy" / "pilots" / args.run_prefix
    batch_path = pilot_dir / "papers.jsonl"
    run_ids = {
        "extraction": args.run_prefix,
        "c08": f"{args.run_prefix}-c08",
        "c09": f"{args.run_prefix}-c09",
        "c10": f"{args.run_prefix}-c10",
        "c11": f"{args.run_prefix}-c11",
        "c12_bootstrap": f"{args.run_prefix}-c12-bootstrap",
        "c12": f"{args.run_prefix}-c12",
        "c13": f"{args.run_prefix}-c13",
        "c14": f"{args.run_prefix}-c14",
    }
    summary = {
        "paper_ids_path": str(paper_ids_path),
        "paper_count": len(paper_ids),
        "run_ids": run_ids,
    }

    section_cmd = [
        "uv",
        "run",
        "--with",
        "pypdf",
        "python3",
        str(EXTRACTION_DIR / "prepare_section_evidence.py"),
        "--db-path",
        str(db_path),
    ]
    for paper_id in paper_ids:
        section_cmd.extend(["--paper-id", paper_id])
    summary["section_prep"] = run_cmd(section_cmd)

    build_section_backed_batch(db_path, paper_ids, batch_path)
    summary["batch_path"] = str(batch_path.resolve())

    summary["prepare_run"] = run_cmd(
        [
            "python3",
            str(EXTRACTION_DIR / "create_extraction_run.py"),
            "--db-path",
            str(db_path),
            "--batch-path",
            str(batch_path),
            "--prompt-path",
            str(prompt_path),
            "--run-id",
            run_ids["extraction"],
            "--run-kind",
            "edge_extraction",
            "--prompt-version",
            prompt_version,
            "--request-kind",
            "edge_extraction",
            "--response-contract-version",
            response_contract_version,
        ]
    )

    summary["model_run"] = run_cmd(
        [
            "uv",
            "run",
            "--with",
            "mlx-lm",
            "python3",
            str(EXTRACTION_DIR / "run_local_mlx_extraction.py"),
            "--requests-path",
            str(DEFAULT_RUNS_ROOT / run_ids["extraction"] / "requests.jsonl"),
            "--responses-path",
            str(DEFAULT_RUNS_ROOT / run_ids["extraction"] / "responses.jsonl"),
            "--max-requests",
            str(len(paper_ids)),
            "--max-tokens",
            str(args.max_tokens),
            "--temperature",
            str(args.temperature),
        ]
    )

    summary["gate_and_ingest"] = run_cmd(
        [
            "python3",
            str(EXTRACTION_DIR / "review_and_ingest_extractions.py"),
            "--db-path",
            str(db_path),
            "--run-id",
            run_ids["extraction"],
            "--responses-path",
            str(DEFAULT_RUNS_ROOT / run_ids["extraction"] / "responses.jsonl"),
            "--schema-path",
            str(schema_path),
            "--ingest-passing-subset-on-blocking",
        ]
    )

    accepted_ids = accepted_paper_ids(
        DEFAULT_RUNS_ROOT / run_ids["extraction"] / "responses.accepted.jsonl"
    )
    accepted_args = [arg for paper_id in accepted_ids for arg in ("--paper-id", paper_id)]

    summary["c08"] = run_cmd(
        [
            "python3",
            str(RANKING_STACK_DIR / "normalize_mechanism_fingerprints.py"),
            "--db-path",
            str(db_path),
            "--run-id",
            run_ids["c08"],
            *accepted_args,
        ]
    )
    summary["c09"] = run_cmd(
        [
            "python3",
            str(RANKING_STACK_DIR / "score_mechanism_exposure.py"),
            "--db-path",
            str(db_path),
            "--run-id",
            run_ids["c09"],
            *accepted_args,
        ]
    )
    summary["c10"] = run_cmd(
        [
            "python3",
            str(RANKING_STACK_DIR / "build_retrieval_stack.py"),
            "--db-path",
            str(db_path),
            "--run-id",
            run_ids["c10"],
            *accepted_args,
        ]
    )
    summary["c11"] = run_cmd(
        [
            "python3",
            str(RANKING_STACK_DIR / "mine_queryless_candidates.py"),
            "--db-path",
            str(db_path),
            "--run-id",
            run_ids["c11"],
            "--retrieval-run-id",
            run_ids["c10"],
        ]
    )
    summary["c12_bootstrap"] = run_cmd(
        [
            "python3",
            str(RANKING_STACK_DIR / "bootstrap_queryless_labels.py"),
            "--db-path",
            str(db_path),
            "--queryless-run-id",
            run_ids["c11"],
            "--output-path",
            str(DEFAULT_RUNS_ROOT / run_ids["c11"] / "bootstrap_queryless_labels.jsonl"),
        ]
    )
    summary["c12"] = run_cmd(
        [
            "python3",
            str(RANKING_STACK_DIR / "run_analyst_adjudication.py"),
            "--db-path",
            str(db_path),
            "--queryless-run-id",
            run_ids["c11"],
            "--labels-path",
            str(DEFAULT_RUNS_ROOT / run_ids["c11"] / "bootstrap_queryless_labels.jsonl"),
            "--run-id",
            run_ids["c12"],
            "--created-by",
            "bootstrap-heuristic",
            "--skip-exposure-refresh",
        ]
    )
    summary["c13"] = run_cmd(
        [
            "python3",
            str(RANKING_STACK_DIR / "build_candidate_family_ranking.py"),
            "--db-path",
            str(db_path),
            "--run-id",
            run_ids["c13"],
            "--adjudication-run-id",
            run_ids["c12"],
            *accepted_args,
        ]
    )
    summary["c14"] = run_cmd(
        [
            "python3",
            # @context requirement -- this archived edge-reset runner has to
            # call the archived card generator explicitly so the preserved
            # pipeline does not silently depend on a removed root-level copy.
            str(Path(__file__).resolve().parent / "generate_edge_cards.py"),
            "--db-path",
            str(db_path),
            "--ranking-run-id",
            run_ids["c13"],
            "--run-id",
            run_ids["c14"],
            "--max-edge-cards",
            "15",
            "--max-almost-there",
            "15",
            "--max-suppressed",
            "15",
        ]
    )

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
