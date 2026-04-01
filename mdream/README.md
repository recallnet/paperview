# mdream

`mdream` is a local research-agent CLI over the paperview literature store.

Design goals:

- JSON-first command interface for LLM callers
- short output by default, capped and drillable via stored `result_id`
- local session, note, and hypothesis memory in `mdream.sqlite3`
- read-only access to the canonical paperview source database
- no duplicate storage of the paper corpus

Current command groups:

- `init`
- `session create|get|list`
- `note add|list`
- `hypothesis add|list`
- `discover round`
- `search papers|sections`
- `paper get|sections|neighbors`
- `surface list|get`
- `score paper`
- `result get`
- `tools`

Typical flow:

```bash
go run ./cmd/mdream init --json
go run ./cmd/mdream discover round --prompt "find a surprising strategy for unprofessionalized low-volume prediction markets" --json
go run ./cmd/mdream result get --result-id <discover_result_id> --full --json
go run ./cmd/mdream --session <session_id> discover round --prompt "focus on settlement lag and toxic flow" --json
go run ./cmd/mdream paper sections --paper-id 1210.4900 --full --json
go run ./cmd/mdream surface get --surface diamond-board --item-id early_market_failure_modes_ledger:market_design:composition:market_design_seams__parity_propagation --full --json
```

Notes:

- every command supports `--json`
- short output is capped and returns a `result_id` for paging or `--full` reloads
- `discover round` creates a session automatically unless `--session` is provided
- `paper sections --full` returns stored section text, not only snippets
- installed `mdream` now defaults to a machine-global store at `~/Library/Application Support/mdream/mdream.sqlite3` on this Mac, so it can be called from any working directory
- `MDREAM_STORE_DB` and `MDREAM_SOURCE_DB` override the default store and source corpus paths when needed
- on first run, `mdream` persists the active source DB path in the store and reuses it from any directory after that
