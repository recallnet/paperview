---
doc_type: guide
owner: docs-stewards
review_policy: periodic-7
reviewed: 2026-04-08
status: active
summary: User and agent guide for installing and operating mdream against the shared paperview corpus.
tags:
  - mdream
  - operations
  - research
written: 2026-04-08
---

# mdream Operator Guide

`mdream` is the user-facing entrypoint for this repo. Treat the rest of the repo
as the maintainer system that prepares the paper corpus it queries.

## Prerequisites

- the shared source DB exists at `data/structural-analogy/paperview.sqlite3`, or
  you set `MDREAM_SOURCE_DB`
- `mdream` is installed via [`scripts/bootstrap_mdream.sh`](../scripts/bootstrap_mdream.sh)
  or your local machine wrapper

## Standard loop

1. Initialize the local session store:

```bash
mdream init --json
```

2. Run a first discovery round:

```bash
mdream discover round --prompt "..." --json
```

3. Drill into promising evidence:

```bash
mdream result get --result-id <result_id> --full --json
mdream paper get --paper-id <paper_id> --full --json
mdream paper sections --paper-id <paper_id> --full --json
```

4. Persist a hypothesis:

```bash
mdream hypothesis add \
  --session-id <session_id> \
  --title "..." \
  --text "..." \
  --target-market "prediction markets" \
  --json
```

5. Score the hypothesis after reading:

```bash
mdream hypothesis score \
  --hypothesis-id <hypothesis_id> \
  --lead-id <lead_id> \
  --result-id <result_id> \
  --prior-novelty 3 \
  --posterior-novelty 8 \
  --prior-plausibility 4 \
  --posterior-plausibility 7 \
  --thin-market-fit 8 \
  --executability 6 \
  --evidence-quality 7 \
  --basin-repetition-penalty 1 \
  --generic-drag-penalty 2 \
  --json
```

6. Check the current objective leader:

```bash
mdream hypothesis top --session-id <session_id> --json
```

7. Continue discovery within the same session:

```bash
mdream --session <session_id> discover round --prompt "..." --json
```

## Runtime locations

- local store: `~/Library/Application Support/mdream/mdream.sqlite3`
- source DB: `data/structural-analogy/paperview.sqlite3` by default

`mdream` should never require you to browse raw SQLite files during normal use.

