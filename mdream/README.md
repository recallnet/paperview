# mdream

`mdream` is a local research-agent CLI over the paperview literature store.

It is designed for iterative hypothesis exploration:

- retrieve papers and sections from the shared corpus DB
- drill into specific evidence
- store session notes and hypotheses
- score hypotheses after reading
- keep moving toward a persistent objective rather than re-deriving judgment from scratch every round

Design goals:

- JSON-first command interface for LLM callers
- short output by default, capped and drillable via stored `result_id`
- local session, note, and hypothesis memory outside the repo in the app-support store
- read-only access to the canonical paperview source database
- no duplicate storage of the paper corpus

Current command groups:

- `init`
- `session create|get|list`
- `note add|list`
- `hypothesis add|list`
- `hypothesis add|list|score|top`
- `discover round`
- `search papers|sections`
- `paper get|sections|neighbors`
- `surface list|get`
- `score paper`
- `result get`
- `tools`

Typical flow:

```bash
mdream init --json
mdream discover round --prompt "find a surprising strategy for unprofessionalized low-volume prediction markets" --json
mdream result get --result-id <discover_result_id> --full --json
mdream hypothesis add --session-id <session_id> --title "..." --text "..." --json
mdream hypothesis score --hypothesis-id <hypothesis_id> --lead-id <lead_id> --result-id <result_id> --prior-novelty 3 --posterior-novelty 8 --prior-plausibility 4 --posterior-plausibility 7 --thin-market-fit 8 --executability 6 --evidence-quality 7 --basin-repetition-penalty 1 --generic-drag-penalty 2 --json
mdream hypothesis top --session-id <session_id> --json
mdream --session <session_id> discover round --prompt "focus on settlement lag and toxic flow" --json
mdream paper sections --paper-id 1210.4900 --full --json
mdream surface get --surface diamond-board --item-id early_market_failure_modes_ledger:market_design:composition:market_design_seams__parity_propagation --full --json
```

Notes:

- every command supports `--json`
- short output is capped and returns a `result_id` for paging or `--full` reloads
- `discover round` creates a session automatically unless `--session` is provided
- `discover round` now emits `agent_priority_score` plus `score_breakdown` so agents can optimize a tool-native ranking target instead of only raw lexical match
- `hypothesis score` persists the agent's post-reading judgments and computes a reusable `surprise_score` plus `objective_score`
- `hypothesis top` shows the session's current best scored hypotheses, and `discover round` now includes a `session_objective` block so later rounds can optimize against stored judgments instead of only the latest retrieval score
- `discover round` is corpus-first by default: runtime paper retrieval outranks canonical surfaced priors unless you explicitly pass `--prefer-surfaces`
- follow-up `discover round` calls are novelty-first by default: previously seen leads only backfill when fresh leads run out; use `--allow-repeats` to let old leads compete normally
- `paper sections --full` returns stored section text, not only snippets
- installed `mdream` now defaults to a machine-global store at `~/Library/Application Support/mdream/mdream.sqlite3`, so it can be called from any working directory
- `MDREAM_STORE_DB` and `MDREAM_SOURCE_DB` override the default store and source corpus paths when needed
- on first run, `mdream` persists the active source DB path in the store and reuses it from any directory after that
- the canonical source corpus is expected at `data/structural-analogy/paperview.sqlite3` unless `MDREAM_SOURCE_DB` overrides it
