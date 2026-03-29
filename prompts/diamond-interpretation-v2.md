Return exactly one JSON object and nothing else.
Do not wrap the JSON in markdown fences.
Do not add commentary outside the JSON.

Task:
Interpret exactly one shortlist-gated diamond candidate. You are not doing full-corpus extraction.
You must only classify the provided diamond batch item and packet context.

Allowed classifications:
- `TRANSLATION_CANDIDATE`
- `COMPOSITIONAL_CANDIDATE`
- `STRANDED_QFIN_RESULT`
- `TRANSITION_SEAM`
- `NO_TRANSLATION`

Rules:
- Use only the supplied lane, operator, packet, and rationale context.
- Do not invent a market connection if the packet does not support one.
- If the item is interesting but still not clearly executable, choose `NO_TRANSLATION`.
- If the item is mainly a recombination of two useful regions, prefer `COMPOSITIONAL_CANDIDATE`.
- If the item is an old q-fin result that now looks testable, prefer `STRANDED_QFIN_RESULT`.
- Use `TRANSITION_SEAM` only when the main result is a state-boundary or regime-handoff edge rather than a generic translation.
- Otherwise, if the item carries a real pre-2024 solution pattern that could transfer into target markets, prefer `TRANSLATION_CANDIDATE`.

Return JSON matching this exact shape:

{
  "classification": "...",
  "result_summary": "...",
  "first_test": "...",
  "instrument_assumed": "...",
  "modern_equivalent": "...",
  "why_stranded_or_unrealized": "...",
  "gap_to_close": "...",
  "confidence": "..."
}
