---
name: mq-paperview-protected-main
description: Land paperview topic-branch work through mq into protected main. Use whenever a change in this repo is ready to integrate and publish through the protected-main workflow instead of direct git merge or push.
---

# mq for paperview Protected Main

Use this skill when work in a paperview topic worktree is ready to land through
the protected-main workflow.

This skill assumes:

- `mq` is on `PATH`
- the protected checkout is `/Users/devrel/Projects/recallnet/paperview`
- you are submitting from a topic worktree, not doing feature work directly on
  protected `main`

## Standard landing flow

1. Preflight:

```bash
mq submit --check-only --json
```

2. Submit and wait for remote landing:

```bash
mq submit --wait --for landed --json --timeout 30m
```

## Durable-handle alternative

For long or backgrounded runs:

```bash
mq submit --json
mq wait --submission <id> --for landed --json --timeout 30m
```

## Do not do this

- do not `git push` directly to `main`
- do not use sleeps or polling loops to infer completion
- do not use `mq logs` or `mq events` as the primary completion signal
- do not commit feature work on the protected checkout

## Health checks

From the protected checkout, use:

```bash
mq doctor --repo /Users/devrel/Projects/recallnet/paperview --json
mq status --repo /Users/devrel/Projects/recallnet/paperview --json
```

If the protected checkout is dirty or blocked, fix that before attempting more
landings.
