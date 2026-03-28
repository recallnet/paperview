#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path

from create_pilot_batch import select_batch, write_outputs


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_CONFIG_PATH = ROOT / "configs" / "mixed_family_pilot_v1.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "pilots"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Materialize the checked-in mixed-family pilot batch."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--config-path",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the mixed-family pilot config JSON.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory for generated pilot artifacts.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = json.loads(Path(args.config_path).resolve().read_text(encoding="utf-8"))
    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    try:
        selected = select_batch(
            connection=connection,
            source_corpus=config["source_corpus"],
            literature_families=config["literature_families"],
            exclude_evaluation_split=config["exclude_evaluation_split"],
            batch_size=config["batch_size"],
            downloaded_pdf_quota=config["downloaded_pdf_quota"],
            min_per_literature_family=config["min_per_literature_family"],
        )
    finally:
        connection.close()

    output_dir = Path(args.output_root).resolve() / config["batch_name"]
    summary_path = write_outputs(
        output_dir=output_dir,
        selected_rows=selected,
        source_corpus=config["source_corpus"],
        literature_families=config["literature_families"],
        excluded_evaluation_split=config["exclude_evaluation_split"],
        batch_size=config["batch_size"],
        downloaded_pdf_quota=config["downloaded_pdf_quota"],
        min_per_literature_family=config["min_per_literature_family"],
    )
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
