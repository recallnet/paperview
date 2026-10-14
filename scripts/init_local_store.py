#!/usr/bin/env python3
"""Initialize the canonical corpus schema without inventing corpus records."""
import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db-path', type=Path, default=ROOT / 'data/structural-analogy/paperview.sqlite3')
    args = parser.parse_args()
    args.db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db_path) as connection:
        connection.executescript((ROOT / 'sql/paperview_schema.sql').read_text())
    print(json.dumps({'db_path': str(args.db_path.resolve()), 'initialized': True}))


if __name__ == '__main__':
    main()
