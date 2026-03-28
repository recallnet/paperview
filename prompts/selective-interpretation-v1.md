Return exactly one JSON object and nothing else.
Do not wrap the JSON in markdown fences.
Do not add commentary outside the JSON.

Task:
Interpret exactly one shortlisted discovery item. You are not doing full-corpus extraction.
You must only classify the provided shortlist item and packet context.

Allowed classifications:
- `TRANSLATION_CANDIDATE`
- `COMPOSITIONAL_CANDIDATE`
- `STRANDED_QFIN_RESULT`
- `NO_TRANSLATION`

Rules:
- Use only the supplied shortlist metadata and review packet context.
- Do not invent a market connection if the packet does not support one.
- If the item is interesting but not clearly translatable, choose `NO_TRANSLATION`.
- If the item mainly combines multiple useful regions, prefer `COMPOSITIONAL_CANDIDATE`.
- If the item is a stranded q-fin result that now looks executable, prefer `STRANDED_QFIN_RESULT`.
- If the item appears to carry a real pre-2024 solution pattern that could transfer into target markets, prefer `TRANSLATION_CANDIDATE`.

Return JSON matching this exact shape:

{
  "classification": "...",
  "result_summary": "...",
  "first_step": "...",
  "instrument_assumed": "...",
  "modern_equivalent": "...",
  "why_stranded_or_unrealized": "...",
  "gap_to_close": "...",
  "confidence": "..."
}
