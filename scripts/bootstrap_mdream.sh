#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_db="${MDREAM_SOURCE_DB:-$repo_root/data/structural-analogy/paperview.sqlite3}"

if ! command -v go >/dev/null 2>&1; then
  echo "bootstrap_mdream: go is required to install mdream" >&2
  exit 1
fi

(
  cd "$repo_root/mdream"
  go install ./cmd/mdream
)

if [[ ! -f "$source_db" ]]; then
  echo "bootstrap_mdream: installed mdream, but source DB is missing at $source_db" >&2
  echo "bootstrap_mdream: fetch the shared corpus bundle and rerun mdream init --json" >&2
  exit 0
fi

echo "bootstrap_mdream: mdream installed"
echo "bootstrap_mdream: source DB found at $source_db"
echo "bootstrap_mdream: next step -> mdream init --json"
