---
doc_type: briefing
owner: devrel
review_policy: periodic-7
reviewed: 2026-04-08
status: historical
summary: Historical reset memo from the edge-card phase that has been superseded by the embedding-first discovery plan.
tags:
  - docs
  - briefing
  - research
  - strategy-discovery
written: 2026-03-27
---

# Structural Analogy Engine Edge-Card Reset

Superseded by [Structural Analogy Engine Plan](./2026-03-25-structural-analogy-engine-plan.md).

## Product Reset

The product surface is now `edge_card`, not `strategy_brief` polish over an abstract-only `q_fin` queue.

The goal is to surface concrete, testable edge hypotheses from the corpus:

- what relation or behavior breaks
- in what market state it breaks
- who is wrong
- why the wrongness persists
- what closes the window
- what executor primitive is required
- what the cheapest validation step is
- what would falsify it quickly

## Immediate Build Priorities

1. Prioritize section-aware full-text extraction.
2. Expand the extraction contract with edge fields:
   - invariant
   - trigger window
   - wrong actor
   - persistence reason
   - death condition
   - executor gap
   - cheap validation
   - fast falsifier
3. Preserve weird candidates as explicit `suppressed` outputs instead of silently killing them upstream.
4. Normalize and retrieve for structural-near / lexical-far discovery, not obvious same-family recurrences.
5. Emit `edge_cards`, `almost-there`, and `suppressed` lanes every checkpoint.

## Implemented Reset Surfaces

- New full-text preparation step: `scripts/prepare_sections_for_extraction_run.py`
- New edge extraction prompt: `prompts/edge-extraction-v26.md`
- New edge extraction schema: `schemas/edge_extraction.schema.json`
- Expanded canonical store fields on `mechanism_instances` for edge-oriented metadata
- New final artifact generator: `scripts/generate_edge_cards.py`
- Updated downstream orchestrator: `scripts/materialize_live_downstream_run.py` now treats edge cards as the default final output

## Next Checkpoint Deliverables

- 10 edge cards
- 10 almost-there cards
- 10 suppressed candidates with explicit suppression reasons
- schema diff showing the edge-oriented extraction contract
- evidence that section-aware full-text parsing ran on the active extraction slice
- evidence that at least some cards are lexically far from standard `q_fin`

## What Not To Do

- Do not spend another cycle making the current abstract-only queue look smarter.
- Do not judge progress by extraction cleanliness, cluster quality, or corpus scale alone.
- Do not silently inherit `research_dead_end_worth_excluding` into candidate generation when the candidate is merely weird.
