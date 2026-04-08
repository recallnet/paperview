---
name: codecontext-paperview
description: Run the paperview codecontext workflow before and after editing critical files. Use whenever you touch Python materializers, corpus/retrieval logic, CLI workflow files, or any non-obvious decision path in this repo. Also use it whenever AGENTS.md tells you to run codecontext for a file.
---

# codecontext for paperview

Use this skill to preserve non-obvious reasoning in the paperview repo.

## When to use it

Use this skill before editing:

- Python materializers under `scripts/`
- corpus / retrieval / scoring logic
- `mdream` workflow files when the change could erase a hard-won decision
- docs or code that already mention `@context`

## Standard loop

1. Brief yourself on the file:

```bash
npm run codecontext:scope -- <file>
```

2. If the file is Python, run the repo checker before editing:

```bash
npm run codecontext:py -- <file.py>
```

3. Make the smallest correct edit.

4. After editing, verify the changed context surface:

```bash
npm run codecontext:diff -- <file>
```

5. If the change spans multiple important files, refresh the repo view:

```bash
npm run codecontext:report
```

## What to capture

Use short inline `@context` notes only for:

- critical invariants
- non-obvious parsing or corpus lessons
- external contract mismatches
- regression guards explaining why a simpler-looking edit would be wrong

Do not use `@context` for narration or obvious comments.

## Repo-specific reminder

This repo is Python-heavy. The Python checker is the primary enforcement surface
for `.py` files, and the CLI is the broader orientation surface for everything
else.
