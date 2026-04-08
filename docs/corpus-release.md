---
doc_type: guide
owner: docs-stewards
review_policy: periodic-7
reviewed: 2026-04-08
status: active
summary: Release process for sharing the paperview source DB and embedding-backed corpus with a team.
tags:
  - corpus
  - release
  - lfs
written: 2026-04-08
---

# Corpus Release Guide

The repo source code and the corpus data have different lifecycles.

## Recommended split

- git repo: code, configs, schemas, docs, lightweight manifests
- Git LFS or release asset: `data/structural-analogy/paperview.sqlite3`

The tracked artifact in git should be the manifest, not the 17G database itself.

## Release checklist

1. Confirm the source DB is consistent with the checked-in schema and embedding recipe.
2. Update [`../corpus/manifest.json`](../corpus/manifest.json).
3. Publish the DB bundle through the agreed team channel.
4. Verify a clean checkout can:
   - install `mdream`
   - place the DB at the expected path
   - run `mdream init --json`
   - run one discovery round successfully

## Compatibility contract

The corpus manifest should tell teammates:

- corpus version
- schema file
- embedding recipe version
- expected DB path
- record counts
- compatible `mdream` assumptions

