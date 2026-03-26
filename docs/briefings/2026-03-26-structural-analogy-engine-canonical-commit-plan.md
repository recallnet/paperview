---
doc_type: briefing
owner: devrel
review_policy: periodic-7
reviewed: 2026-03-26
status: active
summary: Canonical commit-by-commit living plan for the structural analogy engine, updated to be mechanism-first, benchmarked, and strategy-output oriented.
tags:
  - docs
  - briefing
  - plan
  - research
  - strategy-discovery
written: 2026-03-26
---

# Structural Analogy Engine Canonical Commit Plan

## Summary

This is now the canonical forward-execution document for the structural analogy engine. It supersedes the older phase-first plan as the primary control surface for future work, while the earlier plan remains useful as historical implementation log and artifact inventory.

The central correction is simple: this project is not a paper-clustering or embedding-map exercise. It is a mechanism-discovery and transfer-review system whose unit of value is a `mechanism instance`, whose success condition is lexically non-obvious but structurally plausible candidate discovery, and whose final output is a ranked set of strategy briefs with concrete next tests.

This plan is broken into commit-sized units of work. Each commit section includes:

- status
- scope
- deliverables
- exit criteria
- proactive completion record
- upstream impact notes

When a commit is completed, the operator should:

1. mark that commit `completed`
2. fill in its completion record
3. review all later commits
4. add short impact notes in any affected later sections, referencing the completed commit ID

That is the living-plan rule for this document.

---

## Canonical Status

- Overall status: `active`
- Canonical owner: `unassigned`
- Working mode: `local-first`
- Canonical execution unit: `commit`
- Current commit focus: `C02-insight-type-and-fragility-contract`
- Last updated: `2026-03-26`

---

## Where We Are Now

The current repo has already built a substantial amount of table-stakes infrastructure:

- full `q-fin` metadata harvest
- in-progress PDF pull with operational tracking, inventory, and retry flow
- checked-in extraction schema and fingerprint schema
- canonical SQLite store with `papers`
- deterministic 200-paper abstract pilot
- local MLX extraction runner
- schema-aware quality gate
- gate-before-ingest workflow
- first successful beyond-benchmark ingest on a clean 25-paper slice

The current bottleneck is also clear:

- abstract extraction quality has been stabilized enough to run real slices
- but the system is still too paper-centric
- adjacent-domain seeding is not yet in place
- retrieval has no far-analog benchmark
- the output contract still trends toward `paper_extractions` instead of mechanism families and strategy briefs

So the repo is not at zero. But it is also not yet pointed at the final product strongly enough.

---

## Table-Stakes And Core Components

These are the non-negotiable components of the real system:

1. Mechanism-first storage rather than paper-first storage.
2. Mixed-family corpus coverage rather than q-fin-only ontology hardening.
3. Extraction outputs that are insight-bearing, not just schema-valid.
4. Section-aware evidence spans, not abstract-only summaries forever.
5. Normalized structural fingerprints that survive jargon shifts across domains.
6. A benchmark that explicitly rewards lexical-far, structural-near retrieval.
7. Multi-view retrieval, not a single embedding surface.
8. Measured underexploited proxies rather than intuition-only novelty.
9. Anti-transfer and fragility fields as first-class outputs.
10. Analyst feedback as a formal learning loop.
11. Hard go/no-go gates before full-text scale-up, retrieval signoff, and project success claims.
12. Final candidate packets that end in minimal test plans.

If a future change does not improve one of those components, it is probably not on the critical path.

---

## What Was Missing From The Old Plan

The earlier plan got the intent mostly right but still had structural weaknesses:

- it treated `paper_extractions` as the main machine-readable unit
- it did not make `insight type` mandatory
- it over-centered `q-fin` before adjacent-family ontology hardening
- it had no operational discovery benchmark
- it compressed retrieval into one broad phase instead of a multi-view stack
- it did not formalize `underexploited` as a measured proxy
- it did not make anti-transfer mandatory
- it did not separate hard gates from ranked utility
- it did not require minimal test plans in every final candidate
- it treated analyst feedback more as workflow than as a formal phase

This canonical plan corrects those gaps.

---

## Canonical Research Model

### Canonical unit

The canonical unit is now `mechanism_instance`, not `paper`.

Rules:

- one paper may produce `0..N` mechanism instances
- one mechanism family may recur across many papers
- retrieval, scoring, and analyst review happen primarily on mechanism instances and candidate families

### Canonical insight types

Every surfaced item must classify as one of:

1. Executable strategy primitive
2. Missing executor primitive
3. Regime filter
4. Failure mode or anti-pattern
5. Market design exploit
6. Crowding or decay warning
7. Monitoring signal
8. Research dead end worth excluding

If an output cannot be assigned one of those types, it does not enter the ranked queue.

### Canonical success rule

No phase is complete unless it measurably increases the system’s ability to surface lexically non-obvious, structurally plausible, strategy-relevant mechanisms that survive analyst review and yield a concrete next test.

---

## Canonical Phase Order

The canonical execution order is now:

1. Phase 0: Corpus readiness
2. Phase 0.5: Adjacent literature seeding
3. Phase 1: Schema and local store
4. Phase 2: Text preparation
5. Phase 3: Abstract-first extraction stability
6. Phase 3.5: Discovery benchmark construction
7. Phase 4: Normalization and fingerprinting
8. Phase 4.5: Exposure scoring and transfer manifold bootstrap
9. Phase 5: Multi-view retrieval and queryless mining
10. Phase 5.5: Analyst adjudication and weight update
11. Phase 6: Candidate family ranking
12. Phase 7: Strategy briefs and minimal test plans

This commit plan implements that order in concrete units.

---

## Commit Board

| Commit | Status | Purpose | Depends On |
| --- | --- | --- | --- |
| `C01` | `completed` | Adopt mechanism-first canonical model and repo contract | none |
| `C02` | `pending` | Add insight-type, fragility, and anti-transfer schema | `C01` |
| `C03` | `pending` | Seed adjacent literatures and holdout slices | `C01` |
| `C04` | `pending` | Build discovery benchmark and retrieval acceptance thresholds | `C02`, `C03` |
| `C05` | `pending` | Refactor local store and extraction pipeline around mechanism instances | `C01`, `C02` |
| `C06` | `pending` | Stabilize abstract extraction on mixed-family mechanism outputs | `C03`, `C05` |
| `C07` | `pending` | Add section-aware text prep and evidence spans | `C05` |
| `C08` | `pending` | Implement normalization and structural fingerprinting | `C05`, `C06`, `C07` |
| `C09` | `pending` | Add exposure scoring and transfer manifold bootstrap | `C03`, `C08` |
| `C10` | `pending` | Build multi-view retrieval stack | `C04`, `C08`, `C09` |
| `C11` | `pending` | Add queryless mining jobs and local reranking | `C10` |
| `C12` | `pending` | Add analyst adjudication loop and weight update path | `C04`, `C09`, `C11` |
| `C13` | `pending` | Add hard-gated candidate ranking and family assembly | `C08`, `C09`, `C11`, `C12` |
| `C14` | `pending` | Generate final strategy briefs and minimal test plans | `C13` |

---

## Go / No-Go Gates

### Gate A: Before full-text scale-up

- semantic pass rate on cross-domain abstract extraction `>= 85%`
- unsupported enum drift `<= 10%`
- ambiguous normalization `<= 15%`
- at least `70%` of accepted records include evidence type plus blocker fields

### Gate B: Before retrieval is considered useful

- hybrid retrieval beats keyword, pure dense, and citation-neighbor baselines on the far-analog benchmark
- top-20 contains at least `5` non-seed-domain candidates accepted by analyst
- duplicate family rate `<= 25%`

### Gate C: Before calling the system successful

- at least `5` candidate briefs are judged genuinely new and worth validation
- at least `2` imply either a new executor primitive or a new regime filter
- at least `1` is a holdout candidate with near-zero seed vocabulary overlap

---

## Commit Details

## C01: Mechanism-First Reframe

- Status: `completed`
- Scope: make `mechanism_instance` the canonical storage and reasoning unit, and make this document the canonical forward plan
- Depends on: none

### Deliverables

- checked-in schema or design draft for:
  - `mechanism_instances`
  - `mechanism_evidence_spans`
  - `transfer_hypotheses`
  - `candidate_families`
  - `analyst_labels`
  - `benchmark_pairs`
- explicit repo decision that one paper may map to `0..N` mechanism instances
- clear note in docs that `paper_extractions` is transitional, not final

### Exit Criteria

- mechanism-first model is documented and accepted in-repo
- later commits reference mechanism instances, not papers, as their primary unit

### Completion Record

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in the completing git commit for C01`
- Operator: `Codex`
- Reviewer:
- Verification:
  - added draft mechanism-first tables to `sql/paperview_schema.sql`
  - updated repo docs to mark `paper_extractions` as transitional rather than canonical
  - updated later commit notes to inherit the mechanism-first contract from `C01`
- Completion notes:
  - `mechanism_instances`, `mechanism_evidence_spans`, `transfer_hypotheses`, `candidate_families`, `analyst_labels`, and `benchmark_pairs` now exist as checked-in schema definitions
  - the repo now states explicitly that one paper may map to `0..N` mechanism instances
  - `paper_extractions` remains available only as the current abstract-first staging surface until `C05`

### Upstream Impact Notes

- `C02` should extend the new mechanism-first tables in place rather than adding insight and fragility fields to `paper_extractions`.
- `C04` should use the checked-in `benchmark_pairs` table shape from `C01` as its storage starting point.
- `C05` should migrate the active ingest path toward `mechanism_instances` instead of inventing a second canonical destination.

## C02: Insight-Type And Fragility Contract

- Status: `pending`
- Scope: make outputs strategy-bearing and falsifiable
- Depends on: `C01`

### Deliverables

- insight-type enum added to canonical schema
- required fields for:
  - `required_assumptions`
  - `assumption_violations`
  - `fragility_flags`
  - `capacity_constraints`
  - `failure_regimes`
  - `negative_transfer_rationale`
- rule that no final candidate enters the queue without at least one blocker or fragility condition

### Exit Criteria

- extraction/normalization contract can represent both transfer promise and anti-transfer risk
- “interesting paper” outputs without usable insight type are structurally excluded

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Inherits `C01`: insight-type, fragility, and anti-transfer fields should be added to `mechanism_instances`, `transfer_hypotheses`, and related canonical tables, not treated as paper-level attributes.

## C03: Adjacent Literature Seeding

- Status: `pending`
- Scope: stop overfitting the ontology to q-fin
- Depends on: `C01`

### Deliverables

- seeded pilot corpora for at least:
  - betting / sportsbook pricing
  - pari-mutuel / tournament pricing
  - auctions / market design
  - electricity / power markets
  - freight / logistics / transportation pricing
  - DeFi / AMM / on-chain market design
  - constrained arbitrage / forced-flow
  - fragmented special markets
- `literature_family` field in metadata/store
- per-family jargon lexicons
- held-out cross-domain evaluation slice reserved from prompt tuning

### Exit Criteria

- ontology hardening and prompt tuning can be tested on mixed-family data
- cross-domain holdout slice exists and is protected from tuning leakage

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change seeding priorities or family definitions.

## C04: Discovery Benchmark Construction

- Status: `pending`
- Scope: prevent retrieval from collapsing into obvious neighbors
- Depends on: `C02`, `C03`

### Deliverables

- benchmark buckets:
  - lexically near / structurally near
  - lexically near / structurally far
  - lexically far / structurally near
  - lexically far / structurally far
- manually adjudicated anchor / true-far-analog / hard-negative records
- benchmark storage in `benchmark_pairs`
- explicit acceptance thresholds for retrieval

### Exit Criteria

- retrieval work cannot be declared complete without beating baselines on lexical-far / structural-near cases

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Inherits `C01`: benchmark storage should build on the draft `benchmark_pairs` table already checked into the local store schema.

## C05: Mechanism-Instance Store And Extraction Refactor

- Status: `pending`
- Scope: move the pipeline from `paper_extractions` toward mechanism-first persistence
- Depends on: `C01`, `C02`

### Deliverables

- SQL/storage migration for new canonical tables
- extraction run contract that allows `0..N` mechanism instances per paper
- persistence for evidence spans and confidence
- transitional mapping from existing `paper_extractions` to new tables where possible

### Exit Criteria

- accepted extraction outputs can land as mechanism instances with evidence spans
- `paper_extractions` is clearly secondary or transitional

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Inherits `C01`: refactor the active ingest path into the checked-in canonical tables instead of defining new mechanism-first storage names.

## C06: Mixed-Family Abstract Extraction Stability

- Status: `pending`
- Scope: get abstract extraction stable on mechanism instances across adjacent literatures
- Depends on: `C03`, `C05`

### Deliverables

- mixed-family pilot batch
- prompt/runtime path that produces mechanism-instance outputs
- quality gate updated for:
  - insight type
  - fragility fields
  - no-placeholder logic
  - off-domain collapse

### Exit Criteria

- Gate A abstract-level thresholds are met on mixed-family slices

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change extraction contracts or family balance.

## C07: Section-Aware Text Preparation

- Status: `pending`
- Scope: move beyond abstracts into evidence-bearing sections
- Depends on: `C05`

### Deliverables

- section-aware PDF parsing
- `section_ids`
- `mechanism_evidence_spans`
- parse-failure tracking at section level

### Exit Criteria

- mechanism instances can cite actual section spans, not just abstract summaries

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change parsing expectations or section granularity.

## C08: Normalization And Structural Fingerprinting

- Status: `pending`
- Scope: convert raw mechanism instances into comparable structural objects
- Depends on: `C05`, `C06`, `C07`

### Deliverables

- normalized fields for:
  - trigger
  - state variables
  - actor structure
  - market topology
  - pricing path
  - execution shape
  - liquidity regime
  - capacity limit
  - boundary conditions
  - portability blockers
- fingerprint serializer
- ambiguity review path

### Exit Criteria

- accepted mechanism instances have normalized fingerprints suitable for retrieval

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change ontology boundaries or normalization rules.

## C09: Exposure Scoring And Transfer Manifold Bootstrap

- Status: `pending`
- Scope: formalize underexploited proxies and start adaptive transfer learning
- Depends on: `C03`, `C08`

### Deliverables

- `exposure_score`
- `underexploited_score`
- feature set for analyst accept/reject learning
- initial lightweight local model for “worth strategy follow-up”

### Exit Criteria

- ranking can use measured exposure and adaptive transfer priors rather than pure static heuristics

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change domain families, labeling, or feature availability.

## C10: Multi-View Retrieval Stack

- Status: `pending`
- Scope: replace single-surface retrieval with structured + sparse + dense + graph retrieval
- Depends on: `C04`, `C08`, `C09`

### Deliverables

- structured retrieval over fingerprint facets
- sparse lexical retrieval over mechanism spans and discussion/result sections
- dense retrieval over:
  - mechanism summary
  - causal chain summary
  - transfer rationale summary
  - normalized fingerprint text
- graph retrieval over mechanism-instance relations

### Exit Criteria

- retrieval stack exists in separate views and can be benchmarked against C04

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change fingerprint structure, evidence spans, or benchmark definitions.

## C11: Queryless Mining And Local Reranking

- Status: `pending`
- Scope: make the system inform us instead of waiting for manually specified themes
- Depends on: `C10`

### Deliverables

- queryless mining jobs for:
  - structural-near / lexical-far
  - tradecore-near / jargon-far
  - bridge mechanisms across families
  - zero-seed-vocabulary holdouts
  - contradiction mining
  - rare fingerprint combinations with high fit
- local reranker that scores:
  - structural similarity
  - lexical distance realism
  - transfer plausibility
  - blockers

### Exit Criteria

- the system can surface candidates without pre-specified thematic hooks

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change retrieval surfaces or accepted mining modes.

## C12: Analyst Adjudication And Weight Update

- Status: `pending`
- Scope: formalize analyst feedback as part of the system
- Depends on: `C04`, `C09`, `C11`

### Deliverables

- `analyst_labels` workflow
- adjudication fields:
  - accept / reject
  - structurally relevant?
  - non-obvious?
  - genuinely new?
  - worth strategy brief?
  - what made it interesting?
  - what made it weak?
- weight update path for reranking and transfer manifold

### Exit Criteria

- analyst judgments feed back into ranking, ontology refinement, and benchmark maintenance

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change candidate contracts or feature semantics.

## C13: Hard-Gated Candidate Ranking And Family Assembly

- Status: `pending`
- Scope: turn retrieval results into a disciplined review queue
- Depends on: `C08`, `C09`, `C11`, `C12`

### Deliverables

- hard gates for:
  - evidence threshold
  - explicit transfer path
  - explicit failure mode
  - non-null tradecore mapping
  - no catastrophic blocker
- ranked utility formula
- diversity penalty
- `candidate_families`
- `transfer_hypotheses`

### Exit Criteria

- top candidates are filtered, ranked, diversified, and grouped into reusable families

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change ranking features, gates, or analyst labels.

## C14: Strategy Briefs And Minimal Test Plans

- Status: `pending`
- Scope: produce the actual research output that justifies the project
- Depends on: `C13`

### Deliverables

- candidate brief format with:
  - mechanism family
  - transfer rationale
  - tradecore mapping
  - required assumptions
  - fragility / failure regimes
  - observable target signals
  - minimal dataset
  - cheapest validation procedure
  - failure criteria
  - what would change our mind
- final success review against Gate C

### Exit Criteria

- at least five candidate briefs exist and the system can be judged against the real success criteria

### Completion Record

- Status: `pending`
- Completed on:
- Commit SHA:
- Operator:
- Reviewer:
- Verification:
- Completion notes:

### Upstream Impact Notes

- Add notes here when earlier commits change output expectations or validation design.

---

## How To Operate This Document

For each future work turn:

1. Read `Canonical Status`, `Commit Board`, and the next non-completed commit.
2. Advance one commit-sized unit only.
3. Do repo work end-to-end where possible.
4. Update:
   - commit status
   - completion record
   - any affected later commits under `Upstream Impact Notes`
5. Keep the old phase-first plan as historical implementation log unless a migration note says otherwise.

If a change does not clearly move one of the pending commits toward exit criteria, it should probably not be on the critical path.

---

## Additional Context (For AIs And Future Work)

### Canonical repo references

- historical execution log: [`docs/briefings/2026-03-25-structural-analogy-engine-plan.md`](./2026-03-25-structural-analogy-engine-plan.md)
- review brief: [`docs/briefings/2026-03-26-structural-analogy-engine-review-brief.md`](./2026-03-26-structural-analogy-engine-review-brief.md)

### Mandatory structural changes from the revised plan

- paper-first storage is insufficient
- benchmarkless retrieval is insufficient
- q-fin-only ontology hardening is insufficient
- embeddings alone are insufficient
- novelty without exposure proxies is insufficient
- candidate packets without anti-transfer are insufficient

### Canonical output definition

The finished system does not output:

- clusters
- topic maps
- embedding neighborhoods
- paper recommendations

It outputs:

- mechanism instances
- transfer hypotheses
- candidate families
- ranked strategy briefs
- minimal validation plans
