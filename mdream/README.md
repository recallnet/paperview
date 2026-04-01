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
- `search papers|sections`
- `paper get|sections|neighbors`
- `surface list|get`
- `score paper`
- `result get`
- `tools`

Typical flow:

```bash
go run ./cmd/mdream init --json
go run ./cmd/mdream session create --label "prediction market seams" --prompt "find surprising strategies" --json
go run ./cmd/mdream search papers --query "prediction market delayed repair" --json
go run ./cmd/mdream paper get --paper-id 2106.00581 --json
go run ./cmd/mdream paper sections --paper-id 2106.00581 --json
go run ./cmd/mdream score paper --paper-id 2106.00581 --json
```
