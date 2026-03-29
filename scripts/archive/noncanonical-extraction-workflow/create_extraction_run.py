#!/usr/bin/env python3

import argparse
import json
import sqlite3
import textwrap
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_BATCH_PATH = (
    ROOT / "data" / "structural-analogy" / "pilots" / "abstract-pilot-v1" / "papers.jsonl"
)
DEFAULT_PROMPT_PATH = ROOT / "prompts" / "abstract-extraction-v1.md"
DEFAULT_RUNS_ROOT = ROOT / "data" / "structural-analogy" / "runs"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a prompt-ready abstract extraction run from a pilot batch."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--batch-path",
        default=str(DEFAULT_BATCH_PATH),
        help="Path to the pilot batch JSONL.",
    )
    parser.add_argument(
        "--prompt-path",
        default=str(DEFAULT_PROMPT_PATH),
        help="Path to the prompt template markdown file.",
    )
    parser.add_argument(
        "--runs-root",
        default=str(DEFAULT_RUNS_ROOT),
        help="Root directory for generated run artifacts.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit run id. Defaults to a UTC timestamp-based id.",
    )
    parser.add_argument(
        "--run-kind",
        default="abstract_extraction",
        help="Run kind recorded in SQLite.",
    )
    parser.add_argument(
        "--model-name",
        default="unassigned-local-model",
        help="Model identifier placeholder for the run metadata.",
    )
    parser.add_argument(
        "--prompt-version",
        default="abstract-extraction-v1",
        help="Prompt version identifier recorded in SQLite.",
    )
    parser.add_argument(
        "--response-contract-version",
        default="mechanism-instance-batch-v1",
        help="Response contract version recorded in prepared requests.",
    )
    parser.add_argument(
        "--request-kind",
        default="abstract_extraction",
        help="Logical request kind emitted in prepared requests.",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Optional cap on the number of batch rows to include.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc)


def default_run_id(prefix: str):
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}"


def load_batch(batch_path: Path, max_requests=None):
    rows = []
    with batch_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
            if max_requests is not None and len(rows) >= max_requests:
                break
    return rows


def build_request_payload(row):
    payload = {
        "paper_id": row["paper_id"],
        "literature_family": row.get("literature_family", "unknown"),
        "evaluation_split": row.get("evaluation_split", "unknown"),
        "title": row["title"],
        "primary_category": row["primary_category"],
        "published_at": row["published_at"],
        "updated_at": row["updated_at"],
        "ingest_status": row["ingest_status"],
        "abstract": row["abstract"],
    }
    # @context decision -- The edge-card reset can only become more than another abstract pass if
    # prepared batches preserve any section-backed evidence assembled upstream. Silently dropping
    # those fields here would make the new prompt/schema look live while the model still only sees
    # abstracts.
    for key in ("section_evidence", "section_snippets", "edge_focus", "selection_reason"):
        if key in row:
            payload[key] = row[key]
    return payload


def build_prompt(prompt_template: str, row):
    payload = build_request_payload(row)
    return textwrap.dedent(
        f"""{prompt_template}

        ---
        {json.dumps(payload, indent=2, sort_keys=True)}
        """
    ).strip() + "\n"


def register_run(connection, run_id: str, run_kind: str, model_name: str, prompt_version: str, config):
    connection.execute(
        """
        INSERT INTO extraction_runs (
          run_id,
          run_kind,
          model_name,
          prompt_version,
          config_json,
          run_status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
          run_kind = excluded.run_kind,
          model_name = excluded.model_name,
          prompt_version = excluded.prompt_version,
          config_json = excluded.config_json,
          run_status = excluded.run_status
        """,
        (
            run_id,
            run_kind,
            model_name,
            prompt_version,
            json.dumps(config, sort_keys=True),
            "prepared",
        ),
    )


def write_run_artifacts(run_dir: Path, prompt_template: str, requests):
    run_dir.mkdir(parents=True, exist_ok=True)

    prompt_copy_path = run_dir / "prompt.md"
    requests_path = run_dir / "requests.jsonl"
    summary_path = run_dir / "summary.json"

    prompt_copy_path.write_text(prompt_template, encoding="utf-8")

    with requests_path.open("w", encoding="utf-8") as handle:
        for request in requests:
            handle.write(json.dumps(request, sort_keys=True) + "\n")

    summary = {
        "run_id": requests[0]["run_id"] if requests else None,
        "request_count": len(requests),
        "artifacts": {
            "prompt": str(prompt_copy_path.resolve()),
            "requests": str(requests_path.resolve()),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary_path


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    batch_path = Path(args.batch_path).resolve()
    prompt_path = Path(args.prompt_path).resolve()
    runs_root = Path(args.runs_root).resolve()
    run_id = args.run_id or default_run_id(args.run_kind)

    prompt_template = prompt_path.read_text(encoding="utf-8").strip() + "\n"
    rows = load_batch(batch_path, max_requests=args.max_requests)
    run_dir = runs_root / run_id

    requests = []
    for row in rows:
        requests.append(
            {
                "run_id": run_id,
                "paper_id": row["paper_id"],
                "run_kind": args.run_kind,
                "prompt_version": args.prompt_version,
                "model_name": args.model_name,
                "request_kind": args.request_kind,
                "response_contract_version": args.response_contract_version,
                "request_payload": build_request_payload(row),
                "prompt": build_prompt(prompt_template, row),
            }
        )

    config = {
        "batch_path": str(batch_path),
        "batch_size": len(rows),
        "max_requests": args.max_requests,
        "prompt_path": str(prompt_path),
        "runs_root": str(runs_root),
        "response_contract": {
            "version": args.response_contract_version,
            "line_unit": "paper",
            "mechanism_cardinality": "0..N",
            "accepted_line_formats": [
                "legacy_single_extraction",
                "paper_wrapper_with_extraction",
                "paper_wrapper_with_mechanism_instances"
            ],
        },
    }

    connection = sqlite3.connect(str(db_path))
    try:
        register_run(
            connection=connection,
            run_id=run_id,
            run_kind=args.run_kind,
            model_name=args.model_name,
            prompt_version=args.prompt_version,
            config=config,
        )
        connection.commit()
    finally:
        connection.close()

    summary_path = write_run_artifacts(
        run_dir=run_dir,
        prompt_template=prompt_template,
        requests=requests,
    )

    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
