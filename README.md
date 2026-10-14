# paperview

Paperview is a reference implementation of local literature retrieval and persistent hypothesis scoring for research agents. The Go [`mdream`](mdream/README.md) CLI searches a SQLite corpus and stores sessions, notes, hypotheses, and agent-assigned scores. Python scripts build section-based text views and derived research reports.

The scores record an agent’s judgments. They do not measure scientific validity, predictive accuracy, or trading performance. No completed comparative retrieval benchmark or validated trading outcome is included.

## Setup

Requires Go 1.25 or later and a C compiler (the SQLite driver uses CGO). Python 3.10 or later is required for pipeline scripts and tests; some pipeline commands also require `uv` and the packages listed in `package.json`.

```sh
git clone https://github.com/recallnet/paperview.git
cd paperview
./scripts/bootstrap_mdream.sh
```

Ensure `$(go env GOPATH)/bin` is on `PATH`. The installer builds the CLI even when the source database is absent.

**The corpus database is not included, and this repository provides no public corpus download.** The manifest describes an internal historical corpus, not an available release. Supply a compatible SQLite database created from material you are authorized to use, with the schema in [`sql/paperview_schema.sql`](sql/paperview_schema.sql). The pipeline is a maintainer workflow, not a complete downloader and parser for rebuilding that historical corpus.

```sh
export MDREAM_SOURCE_DB=/absolute/path/to/paperview.sqlite3
mdream init --json
mdream discover round --prompt "investigate a research hypothesis" --json
```

By default, the local session store is `~/Library/Application Support/mdream/mdream.sqlite3`; `MDREAM_STORE_DB` overrides it. The source corpus is opened read-only. Session notes and hypotheses remain on disk: use a private directory for sensitive research and do not commit local databases.

## Research workflow

1. Discover candidate papers and sections.
2. Read the evidence using `paper get` and `paper sections`.
3. Record a hypothesis and its supporting evidence.
4. Record prior and posterior judgments using `hypothesis score`.
5. Retrieve stored results and compare hypotheses across rounds.

See the [CLI reference](mdream/README.md), [operator guide](docs/operator-guide.md), [corpus build guide](docs/corpus-build.md), and [corpus release guide](docs/corpus-release.md). Discovery uses section views including surprise, mechanism, regime, and full-section text. Its ranking and objective functions are research heuristics.

## Validation

```sh
PYTHONPATH=scripts uv run --python 3.13 --with pyyaml --with numpy --with sqlite-vec --with scikit-learn python -m unittest discover -s tests -p 'test_*.py' -v
(cd mdream && go test ./... && go vet ./... && go build ./cmd/mdream)
bash -n scripts/bootstrap_mdream.sh
npm run docs:lint
```

The docs lint command requires the internal Recall documentation tooling declared in `package.json`; availability outside the original environment is not guaranteed. Tests use fixtures and do not establish that the missing historical corpus can be reproduced.

## Data, reports, and licensing

The MIT license applies to Recall-authored source code and documentation. It does not grant rights to papers, quoted text, metadata supplied by others, model artifacts, or external datasets. Preserve each source’s license and attribution, and verify rights before redistributing a database or derived report. Public availability of a paper does not imply permission to redistribute it.

[`reports/`](reports/) contains historical internal research artifacts and candidate classifications. They are unvalidated hypotheses, including negative results, rather than investment advice or proven strategies. The tracked reports contain paper identifiers and titles, derived scores, and research commentary; the underlying full-text database is not included. No rights to redistribute a paper or the historical corpus are implied.
