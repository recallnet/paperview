# AGENTS

## Protected Checkout

- `/Users/devrel/Projects/recallnet/paperview` is the human-facing protected
  checkout.
- It should stay on `main`. Treat direct feature work on protected `main` as a
  workflow bug.
- Allowed from the protected checkout: `git status`, `git diff`, `git log`,
  `git show`, `git fetch`, and `mq` / `mdream` / `codecontext` commands.
- Do not commit, merge, rebase, or push feature work directly from the
  protected checkout when a topic worktree is appropriate.

## Branch Workflow

- Create a topic worktree for implementation work.
- Make edits, tests, and commits in the topic worktree, not on protected
  `main`.
- Use `mq` to land work back through protected `main`. Do not `git merge` or
  `git push` directly to `main`.

## Landing Work With mq

- `mq` is installed on this machine by default and should be used as the
  integration path for protected-main workflows.
- Local paperview `mq` skill:
  `.agents/skills/mq-paperview-protected-main/SKILL.md`

Default flow from a topic worktree:

1. Preflight:

```bash
mq submit --check-only --json
```

2. Submit and wait for landing:

```bash
mq submit --wait --for landed --json --timeout 30m
```

Durable-handle alternative:

```bash
mq submit --json
mq wait --submission <id> --for landed --json --timeout 30m
```

Use `mq` submission and wait commands as the source of truth. Do not use ad hoc
sleep loops or branch-name polling to decide whether landing is complete.

## Local Skills

- `codecontext-paperview`
  Path: `.agents/skills/codecontext-paperview/SKILL.md`
  Use this whenever you edit critical Python materializers, corpus/retrieval
  logic, or any file where a non-obvious decision could be lost.

- `mdream-hypothesis-deepening`
  Path: `.agents/skills/mdream-hypothesis-deepening/SKILL.md`
  Use this for multi-round `mdream` research sessions that must keep scoring and
  refining hypotheses until a surprising, testable idea survives.

- `mq-paperview-protected-main`
  Path: `.agents/skills/mq-paperview-protected-main/SKILL.md`
  Use this when landing topic-branch work back through protected `main`.

## codecontext Workflow

Before editing critical files, run:

```bash
npm run codecontext:scope -- <file>
```

For Python files, also run:

```bash
npm run codecontext:py -- <file.py>
```

After editing, run:

```bash
npm run codecontext:diff -- <file>
```

For broader repo orientation:

```bash
npm run codecontext:report
```

Use inline `@context` annotations only for non-obvious, high-value reasoning:

- critical invariants
- corpus or parsing lessons
- external contract quirks
- regression guards explaining why a simpler edit would be wrong

## Engineering Bias

- Prefer the right design over the fastest hack.
- Use established packages and existing workflow surfaces when they already
  solve the problem cleanly.
- Keep `mdream` as the primary user-facing product and treat the corpus pipeline
  as the maintainer system behind it.
