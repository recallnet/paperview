---
doc_type: guide
owner: docs-stewards
review_policy: periodic-7
reviewed: 2026-04-08
status: active
summary: Maintainer workflow for adding papers and rebuilding the section-first paperview corpus for mdream.
tags:
  - corpus
  - embeddings
  - pipeline
written: 2026-04-08
---

# Corpus Build Guide

Use this when you are extending or refreshing the searchable literature corpus
behind `mdream`.

## Canonical representation

Discovery is now section-first. The embedding recipe in
[`configs/embedding_spaces.yaml`](../configs/embedding_spaces.yaml) weights:

- `surprise_sections`
- `mechanism_sections`
- `regime_sections`
- `all_sections`

Do not revert discovery ranking to title/abstract-first. That collapses search
back toward already-realized discourse.

## Build flow

1. Harvest or ingest new paper metadata and PDFs.
2. Initialize or migrate the local store:

```bash
npm run store:init
```

3. Load metadata into the canonical SQLite DB.
4. Parse PDFs into `paper_sections`.
5. Materialize text views.
6. Materialize view embeddings.
7. Rebuild the discovery map / nearest-neighbor structures.
8. Refresh the tracked corpus manifest before releasing the DB.

## Current source of truth

- schema: [`sql/paperview_schema.sql`](../sql/paperview_schema.sql)
- embedding recipe: [`configs/embedding_spaces.yaml`](../configs/embedding_spaces.yaml)
- corpus manifest: [`../corpus/manifest.json`](../corpus/manifest.json)

## Verification

At minimum, run the tests that touch the representation layer and docs:

```bash
python3 -m unittest -v \
  tests.test_materialize_text_views \
  tests.test_build_representation_discovery_map \
  tests.test_materialize_view_embeddings
npm run docs:lint
```

