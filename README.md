# paperview

`paperview` is the corpus and maintainer pipeline behind
[`mdream`](./mdream/README.md), a CLI for exploring surprising and executable
market-structure hypotheses from a shared paper database.

## Repo focus

This repo now has two distinct layers:

1. `mdream/`
   User-facing research CLI. This is the primary product surface.
2. corpus pipeline
   Maintainer workflow for harvesting papers, parsing sections, materializing
   embeddings, and shipping an updated searchable SQLite corpus.

If you are using the repo, start with `mdream`. If you are extending the paper
corpus or refreshing embeddings, use the maintainer docs under [docs](./docs/INDEX.md).

## Quickstart

1. Fetch the shared corpus bundle so the source DB exists at:
   `data/structural-analogy/paperview.sqlite3`
2. Install `mdream`:

```bash
./scripts/bootstrap_mdream.sh
```

3. Initialize the local session store:

```bash
mdream init --json
```

4. Run a first discovery round:

```bash
mdream discover round \
  --prompt "find a surprising strategy for unprofessionalized low-volume prediction markets" \
  --json
```

## What ships with the repo

- [`mdream/`](./mdream/README.md): CLI source and user workflow
- [`corpus/manifest.json`](./corpus/manifest.json): tracked compatibility and
  corpus metadata
- [`reports/published/`](./reports/published/): checked-in publication surfaces
- [`docs/operator-guide.md`](./docs/operator-guide.md): how users and agents
  should drive `mdream`
- [`docs/corpus-build.md`](./docs/corpus-build.md): how maintainers add papers
  and refresh the searchable corpus
- [`docs/corpus-release.md`](./docs/corpus-release.md): how to package and share
  the DB with a team

## Repo layout

- `mdream/`: Go CLI
- `configs/`: embedding spaces, challenge capsules, shortlist rules
- `scripts/`: harvest, parse, embedding, and materialization pipeline
- `sql/`: SQLite schema
- `schemas/`: JSON schema contracts
- `tests/`: Python and Go verification
- `docs/`: operator and maintainer docs
- `reports/`: memo outputs and checked-in publication surfaces

## Maintainer workflow

The build pipeline still matters because `mdream` depends on a good section-first
corpus, not just titles and abstracts.

The current canonical discovery representation is section-first:

- `surprise_sections`
- `mechanism_sections`
- `regime_sections`
- `all_sections`

Those views are defined in [configs/embedding_spaces.yaml](./configs/embedding_spaces.yaml)
and drive the embedding-backed retrieval surfaces consumed by `mdream`.

When new paper sources are added:

1. ingest metadata and PDFs
2. parse `paper_sections`
3. materialize `text_views`
4. rebuild view embeddings and discovery maps
5. verify the corpus manifest before releasing the DB

See [docs/corpus-build.md](./docs/corpus-build.md) for the exact commands.

## Published examples

The canonical checked-in publication surfaces now live under
[reports/published/](./reports/published/):

- [diamond_board.md](./reports/published/diamond_board.md)
- [findings_and_throwaways.md](./reports/published/findings_and_throwaways.md)
- [research_output.md](./reports/published/research_output.md)
- [run_summary.md](./reports/published/run_summary.md)
- [run_summary.json](./reports/published/run_summary.json)

## Notes

- The source corpus DB is intentionally not tracked in git outside your chosen
  distribution channel (for example Git LFS or release assets).
- `mdream` keeps its local session/history store outside the repo under
  `~/Library/Application Support/mdream/mdream.sqlite3`.
- The repo-local `mdream/*.sqlite3` pattern is ignored on purpose; runtime state
  should not live in the product tree.
