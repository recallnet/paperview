#!/usr/bin/env python3

import argparse
import json
import sqlite3
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_RUN_ID = "qfin-prelim-00882-c13"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Materialize the full research finding pack for a ranked family run."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--family-name", action="append", default=None)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--include-dead-ends", action="store_true")
    return parser.parse_args()


def slugify(value):
    materialized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.lower())
    while "--" in materialized:
        materialized = materialized.replace("--", "-")
    return materialized.strip("-") or "research-pack"


def default_output_dir(run_id):
    return ROOT / "data" / "structural-analogy" / "runs" / f"{slugify(run_id)}-finding-pack"


def select_families(connection, run_id, requested_families, top_k, include_dead_ends):
    if requested_families:
        return requested_families

    query = """
        SELECT cfr.family_rank, cf.family_name, cf.family_status
        FROM candidate_family_rankings cfr
        JOIN candidate_families cf ON cf.candidate_family_id = cfr.candidate_family_id
        WHERE cfr.run_id = ?
        ORDER BY cfr.family_rank ASC, cfr.final_priority_score DESC
    """
    rows = connection.execute(query, (run_id,)).fetchall()
    families = []
    for row in rows:
        family_name = row["family_name"]
        if not include_dead_ends and "research-dead-end-worth-excluding" in family_name:
            continue
        families.append(family_name)
        if len(families) >= top_k:
            break
    return families


def run_export(args, family_names, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3",
        str(ROOT / "scripts" / "export_cluster_cartography.py"),
        "--db-path",
        str(Path(args.db_path).resolve()),
        "--run-id",
        args.run_id,
        "--output-path",
        str(output_dir / "cluster-cartography.md"),
        "--json-output-path",
        str(output_dir / "cluster-cartography.json"),
        "--thesis-output-path",
        str(output_dir / "thesis_seed_pack.md"),
        "--thesis-json-output-path",
        str(output_dir / "thesis_seed_pack.json"),
        "--motif-evidence-output-path",
        str(output_dir / "motif_evidence_pack.md"),
        "--motif-evidence-json-output-path",
        str(output_dir / "motif_evidence_pack.json"),
        "--measurement-spec-output-path",
        str(output_dir / "measurement_spec_pack.md"),
        "--measurement-spec-json-output-path",
        str(output_dir / "measurement_spec_pack.json"),
    ]
    for family_name in family_names:
        cmd.extend(["--family-name", family_name])
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def write_manifest(args, family_names, output_dir):
    manifest = {
        "run_id": args.run_id,
        "db_path": str(Path(args.db_path).resolve()),
        "selected_families": family_names,
        "artifacts": {
            "cluster_cartography_markdown": str(output_dir / "cluster-cartography.md"),
            "cluster_cartography_json": str(output_dir / "cluster-cartography.json"),
            "thesis_seed_pack_markdown": str(output_dir / "thesis_seed_pack.md"),
            "thesis_seed_pack_json": str(output_dir / "thesis_seed_pack.json"),
            "motif_evidence_pack_markdown": str(output_dir / "motif_evidence_pack.md"),
            "motif_evidence_pack_json": str(output_dir / "motif_evidence_pack.json"),
            "measurement_spec_pack_markdown": str(output_dir / "measurement_spec_pack.md"),
            "measurement_spec_pack_json": str(output_dir / "measurement_spec_pack.json"),
        },
    }
    path = output_dir / "finding_pack_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def main():
    args = parse_args()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else default_output_dir(args.run_id)

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        family_names = select_families(
            connection,
            args.run_id,
            args.family_name,
            args.top_k,
            args.include_dead_ends,
        )
    finally:
        connection.close()

    if not family_names:
        raise SystemExit(
            f"no candidate families selected for run_id={args.run_id}; supply --family-name or check candidate_family_rankings"
        )

    run_export(args, family_names, output_dir)
    manifest_path = write_manifest(args, family_names, output_dir)
    print(output_dir)
    print(manifest_path)


if __name__ == "__main__":
    main()
