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
- Current commit focus: `C12-analyst-adjudication-and-weight-update`
- Last updated: `2026-03-26`

---

## Where We Are Now

The current repo has already built a substantial amount of table-stakes infrastructure:

- full `q-fin` metadata harvest
- in-progress PDF pull with operational tracking, inventory, and retry flow
- checked-in extraction schema and fingerprint schema
- canonical SQLite store with `papers`
- deterministic mixed-family pilot generation
- local MLX extraction runner
- schema-aware quality gate
- gate-before-ingest workflow
- adjacent-literature seed registries and holdout policy
- discovery benchmark definition with retrieval thresholds
- section-aware evidence preparation and mechanism-level fingerprint normalization
- `sqlite-vec` plus Python bindings already installed locally for SQLite-native vector work

The current bottleneck is also clear:

- abstract extraction quality is stable enough to support downstream retrieval work
- exposure scoring and follow-up priors now exist at the mechanism level
- a benchmarkable multi-view retrieval stack now exists across structured, sparse, dense, and graph views
- queryless mining and local reranking now persist ranked candidate hits across six zero-query discovery modes
- but analyst feedback and final candidate assembly are still not built
- the next capability surface is analyst adjudication and weight update on top of the persisted mining queue
- the system now has most of the local infrastructure it needs, but the analyst loop and hard-gated ranking layers still need to be implemented and benchmarked

So the repo is not at zero. But it is also not yet pointed at the final product strongly enough.

## Local Toolchain Readiness

The local stack is now materially stronger than the original draft assumed:

- `sqlite-vec` v0.1.6 is installed locally, including the Python binding
- first vector retrieval work can therefore stay SQLite-native in `C10`
- MLX remains the active Apple Silicon execution path for local model work
- MLX is also the intended high-throughput local embedding path on this Mac Studio once the install completes
- `sentence-transformers` is the preferred Python fallback and baseline path for local embeddings when MLX coverage or model support is insufficient

That means the remaining plan is mostly blocked by implementation work, not missing local infrastructure.

## Canonical Vector Strategy

Use one primary vector space for production retrieval, not a grab bag of
incompatible embeddings.

Rules:

- vectors are only directly comparable when they come from the same model,
  dimension, and normalization contract
- the production ANN surface should therefore use one canonical embedder and
  one fixed output dimension at a time
- alternate models may exist, but they should live in separate indices or act
  as rerankers rather than being mixed into the primary corpus space

Current recommended roster:

- primary production index: `Qwen/Qwen3-Embedding-0.6B`
  - start with `512` dimensions for the main SQLite-native corpus index
  - use for mechanism summaries, transfer rationales, and serialized
    `fingerprint_text`
- exploratory discovery index: `BAAI/bge-m3`
  - keep separate from the production vector space
  - use for lexical-far / structural-near discovery experiments, bridge-paper
    search, and hybrid retrieval research
- high-fidelity second pass: `Alibaba-NLP/gte-Qwen2-7B-instruct`
  - do not mix into the main ANN index
  - use for reranking, adjudication, or top-k quality passes only

This preserves future flexibility without making `C10` and `C11` compare
incompatible vectors as if they lived in one space.

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
| `C02` | `completed` | Add insight-type, fragility, and anti-transfer schema | `C01` |
| `C03` | `completed` | Seed adjacent literatures and holdout slices | `C01` |
| `C04` | `completed` | Build discovery benchmark and retrieval acceptance thresholds | `C02`, `C03` |
| `C05` | `completed` | Refactor local store and extraction pipeline around mechanism instances | `C01`, `C02` |
| `C06` | `completed` | Stabilize abstract extraction on mixed-family mechanism outputs | `C03`, `C05` |
| `C07` | `completed` | Add section-aware text prep and evidence spans | `C05` |
| `C08` | `completed` | Implement normalization and structural fingerprinting | `C05`, `C06`, `C07` |
| `C09` | `completed` | Add exposure scoring and transfer manifold bootstrap | `C03`, `C08` |
| `C10` | `completed` | Build multi-view retrieval stack | `C04`, `C08`, `C09` |
| `C11` | `completed` | Add queryless mining jobs and local reranking | `C10` |
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

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in the completing git commit for C02`
- Operator: `Codex`
- Reviewer:
- Verification:
  - extended `schemas/extraction.schema.json` and the bundled example/vocab artifacts with mandatory insight, fragility, and anti-transfer fields
  - updated `scripts/review_extraction_quality.py` to block promising candidates without specific blocker context
  - extended the checked-in SQL surface for `mechanism_instances`, `transfer_hypotheses`, and `candidate_families` to carry the C02 contract
- Completion notes:
  - `insight_type` is now mandatory in the active extraction contract
  - `required_assumptions`, `assumption_violations`, `fragility_flags`, `capacity_constraints`, `failure_regimes`, and `negative_transfer_rationale` are now required fields
  - the repo now encodes the rule that promising candidates cannot advance without explicit blocker or anti-transfer context

### Upstream Impact Notes

- Completed in `C02`: insight-type, fragility, and anti-transfer fields now exist in the active extraction schema and in the canonical SQL table surface, not as paper-level attributes.
- `C04` should build benchmark labels around the checked-in `insight_type` enum rather than inventing a second category system.
- `C05` should map validated extraction fields directly into the new JSON columns on `mechanism_instances` and `transfer_hypotheses`.
- `C06` should tune prompts against the mandatory blocker fields and the new reviewer gate, not just the older paper-first schema keys.

## C03: Adjacent Literature Seeding

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in the completing git commit for C03`
- Operator: `Codex`
- Reviewer:
- Verification:
  - added checked-in adjacent-family seed registry, jargon lexicons, and holdout policy under `configs/`
  - extended the `papers` store surface plus metadata loader to stamp `literature_family` and `evaluation_split`
  - updated pilot-batch tooling to support mixed-family selection while excluding reserved holdout rows
- Completion notes:
  - the repo now has explicit seed coverage for betting, pari-mutuel, auctions, electricity, freight, DeFi, constrained-arbitrage, and fragmented special-market families
  - `fragmented_special_markets` is now reserved as a holdout family in the checked-in split policy
  - adjacent seeding can be materialized into active-vs-holdout artifacts without polluting git with generated corpus data

### Upstream Impact Notes

- Completed in `C03`: adjacent-family seeding, per-family lexicons, and reserved holdout policy now exist as checked-in repo assets.
- `C04` should use the `fragmented_special_markets` holdout policy from `C03` as one source of lexical-far benchmark candidates.
- `C06` should tune on the active families from `C03` and keep the reserved holdout family out of prompt-iteration loops.
- `C09` should treat the checked-in `literature_family` field as the canonical family label for exposure and manifold features.

## C04: Discovery Benchmark Construction

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in the completing git commit for C04`
- Operator: `Codex`
- Reviewer:
- Verification:
  - added a checked-in discovery benchmark definition with adjudicated bucket labels and explicit retrieval thresholds
  - extended `benchmark_pairs` with stable benchmark keys plus paper-level source/candidate ids for pre-C05 storage
  - added a materializer that loads the benchmark into SQLite and verified it on a temp store
- Completion notes:
  - the benchmark now covers all four lexical/structural buckets with adjudicated obvious neighbors, true far analogs, and hard negatives
  - the holdout family from `C03` is now used directly in the lexical-far benchmark source set
  - retrieval acceptance thresholds are now explicit and repo-local instead of implied by prose only

### Upstream Impact Notes

- Completed in `C04`: the repo now has a checked-in benchmark definition, retrieval thresholds, and materialization path in `benchmark_pairs`.
- `C05` should map benchmark pairs from paper-level anchors to mechanism instances without losing the benchmark keys or adjudication payload.
- `C10` should benchmark each retrieval surface against the `lexically_far_structurally_near` subset from `C04` before combining views.
- `C12` should treat the `C04` adjudications as seed analyst labels and update them only through an explicit review path.

## C05: Mechanism-Instance Store And Extraction Refactor

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in the completing git commit for C05`
- Operator: `Codex`
- Reviewer:
- Verification:
  - extended the checked-in SQL contract with `mechanism_instances.evidence_confidence` plus `paper_extractions.response_contract_version`
  - refactored `scripts/ingest_extraction_responses.py` so validated rows persist as per-paper staging snapshots and promote into canonical `mechanism_instances` plus `mechanism_evidence_spans`
  - added a `promote_paper_extractions.py` backfill path for older valid staging rows and verified both ingest and backfill flows on a temp SQLite store
- Completion notes:
  - extraction runs now record a `mechanism-instance-batch-v1` response contract that allows `0..N` mechanism instances per paper
  - accepted outputs now land in canonical mechanism tables with abstract-backed evidence spans and persisted confidence labels
  - benchmark pairs now bridge from paper-level anchors to mechanism ids only when the paper-to-mechanism mapping is uniquely resolved
  - `paper_extractions` remains available as a transitional per-paper snapshot rather than the downstream analysis unit

### Upstream Impact Notes

- Completed in `C05`: the active ingest path now writes canonical `mechanism_instances` and `mechanism_evidence_spans`, while `paper_extractions` remains only a staging snapshot.
- Completed in `C05`: extraction runs can declare `0..N` mechanism instances per paper via the checked-in `mechanism-instance-batch-v1` response contract.
- Completed in `C05`: benchmark pairs bridge from paper ids to mechanism ids only when the mapping is unambiguous, preserving the `C04` benchmark keys and adjudication payload without inventing labels.

## C06: Mixed-Family Abstract Extraction Stability

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in the completing git commit for C06`
- Operator: `Codex`
- Reviewer:
- Verification:
  - added a checked-in mixed-family pilot definition plus `scripts/materialize_mixed_family_pilot.py` so active-family batches can be rebuilt with a minimum per-family floor
  - updated run preparation and local MLX output handling so mixed-family runs carry `literature_family` context and preserve the `mechanism-instance-batch-v1` paper-level wrapper
  - updated the reviewer and gate summary to score wrapper-style outputs, block empty batches on mechanism-like abstracts, and report Gate A rollout metrics
  - verified a temp mixed-family smoke slice with one row per requested family, `semantic_pass_rate = 1.0`, `unsupported_enum_ratio = 0.0`, `accepted_with_evidence_and_blockers_ratio = 1.0`, and canonical ingest into `mechanism_instances`
- Completion notes:
  - mixed-family pilots now have a checked-in config with per-family coverage floors rather than relying on ad hoc CLI flags
  - `prompts/abstract-extraction-v26.md` now returns `0..N` mechanism instances per paper through the canonical wrapper contract
  - off-domain freight/logistics-style abstracts can collapse to an empty mechanism batch, while mechanism-like abstracts are blocked if they collapse to nothing
  - the repo now has explicit Gate A metrics on mixed-family wrapper outputs instead of only raw blocking/warning counts

### Upstream Impact Notes

- Completed in `C06`: mixed-family pilot materialization, wrapper-style prompt/runtime output, and Gate A metrics now exist as checked-in repo workflows.
- Completed in `C06`: the reviewer now treats empty `mechanism_instances` batches as acceptable only for genuinely non-mechanistic abstracts, not as a silent fallback for mechanism-like papers.

## C07: Section-Aware Text Preparation

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in the completing git commit for C07`
- Operator: `Codex`
- Reviewer:
- Verification:
  - added `scripts/prepare_section_evidence.py` to parse downloaded PDFs into `paper_sections` using `pypdf` via `uv`
  - wired section preparation to log unreadable or missing files into `parse_failures` with `failure_stage = section_parse`
  - upgraded canonical `mechanism_evidence_spans` from abstract fallback to section-backed snippets when parsed section text overlapped the mechanism label/summary
  - verified the flow on a temp SQLite store with one real downloaded PDF and one missing-PDF case
- Completion notes:
  - section-aware text prep now exists as a repo-native workflow instead of plan prose only
  - parsed sections preserve `section_id` anchors and `content_hash` values in the canonical store
  - evidence spans only upgrade when section-level overlap is positive, so the C05 abstract fallback remains intact when full-text support is weak
  - parse failures are now explicit and queryable instead of being lost as ad hoc operator errors

### Upstream Impact Notes

- Completed in `C07`: parsed PDF sections, section-backed evidence upgrades, and explicit `section_parse` failure logging now exist as checked-in repo workflows.
- Completed in `C07`: section evidence only replaces the abstract fallback when parsed text provides a positive support match, preserving the C05 mechanism-store contract.

## C08: Normalization And Structural Fingerprinting

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in the completing git commit for C08`
- Operator: `Codex`
- Reviewer:
- Verification:
  - updated `schemas/fingerprint.schema.json`, `schemas/examples/fingerprint.example.json`, and `schemas/normalization_vocab.json` to the mechanism-level C08 facet contract
  - extended `sql/paperview_schema.sql` with canonical `mechanism_fingerprints` and `normalization_reviews` tables while demoting `paper_fingerprints` to transitional status
  - added `scripts/normalize_mechanism_fingerprints.py` to map active `mechanism_instances` plus section-backed evidence into deterministic `fingerprint_text` and queued ambiguity review rows
  - verified schema validity, SQLite DDL, and a temp-store smoke test that normalized one active mechanism and queued one ambiguity review
- Completion notes:
  - normalization is now mechanism-first instead of paper-first, matching the C01 and C05 store contracts
  - the canonical fingerprint surface now includes trigger, state variables, actor structure, market topology, pricing path, execution shape, liquidity regime, capacity limit, boundary conditions, and portability blockers
  - ambiguous or lossy mappings are no longer silent; they land in `normalization_reviews` for operator follow-up
  - the serialized `fingerprint_text` surface is now ready for C10 structured, sparse, and dense retrieval work

### Upstream Impact Notes

- Completed in `C08`: active mechanism instances now normalize into canonical mechanism-level fingerprints plus deterministic `fingerprint_text`.
- Completed in `C08`: lossy mappings now queue into `normalization_reviews` instead of disappearing as implicit heuristic choices.

## C09: Exposure Scoring And Transfer Manifold Bootstrap

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in git history for this commit`
- Operator: `Codex`
- Reviewer: `not reviewed`
- Verification: `python3 -m py_compile scripts/score_mechanism_exposure.py`; `npm run codecontext:py -- scripts/score_mechanism_exposure.py`; temp-store run of `python3 scripts/score_mechanism_exposure.py --db-path /tmp/paperview-c09-test.sqlite3 --run-id c09-test-run`
- Completion notes:
  - added `scripts/score_mechanism_exposure.py` plus `npm run score:exposure`
  - added canonical `mechanism_exposure_scores` persistence for `exposure_score`, `underexploited_score`, `worth_followup_score`, and analyst-learning feature rows
  - bootstrapped the scorer from canonical `mechanism_instances`, `mechanism_fingerprints`, family metadata, benchmark-linked mechanism ids, and any future `analyst_labels`
  - verified end-to-end persistence on a temp SQLite store with mixed-family mechanism rows and benchmark-derived labels

### Upstream Impact Notes

- Add notes here when earlier commits change domain families, labeling, or feature availability.
- Inherits `C03`: exposure features should include `literature_family` and holdout-aware corpus membership rather than only source-corpus labels.
- Inherits `C06`: exposure work should use the checked-in mixed-family pilot and Gate A metrics as its first non-q-fin calibration slice.
- Inherits `C08`: exposure scoring can now use normalized trigger/topology/liquidity facets and ambiguity-review burden as explicit features rather than re-deriving them from raw extraction JSON.
- Completed in `C09`: older local SQLite files may lag the checked-in schema, so downstream jobs should apply `sql/paperview_schema.sql` or otherwise verify store shape before assuming C05/C08/C09 tables exist.

## C10: Multi-View Retrieval Stack

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in git history for this commit`
- Operator: `Codex`
- Reviewer: `not reviewed`
- Verification: `python3 -m py_compile scripts/build_retrieval_stack.py scripts/benchmark_retrieval_stack.py`; `npm run codecontext:py -- scripts/build_retrieval_stack.py`; `npm run codecontext:py -- scripts/benchmark_retrieval_stack.py`; temp-store runs of `python3 scripts/build_retrieval_stack.py --db-path /tmp/paperview-c10-test.sqlite3 --run-id c10-build-test` and `python3 scripts/benchmark_retrieval_stack.py --db-path /tmp/paperview-c10-test.sqlite3 --retrieval-run-id c10-build-test --run-id c10-benchmark-test`
- Completion notes:
  - added `scripts/build_retrieval_stack.py` plus `npm run retrieve:build`
  - added `scripts/benchmark_retrieval_stack.py` plus `npm run retrieve:benchmark`
  - persisted canonical retrieval documents, dense embeddings, graph edges, and per-view benchmark results in SQLite
  - implemented separate structured, sparse, dense, graph, citation-baseline, and hybrid retrieval views over canonical mechanism-level artifacts
  - benchmark summaries now materialize Gate B-style comparison metrics from `benchmark_pairs`

### Upstream Impact Notes

- Inherits `C05`: sparse and dense retrieval should target canonical mechanism summaries and evidence spans, while respecting that benchmark bridges remain null when a paper maps to multiple active mechanisms.
- Inherits `C06`: retrieval indexing should assume wrapper-style mixed-family runs may legitimately contain zero-mechanism papers and should index only accepted mechanism instances, not the empty wrapper rows.
- Inherits `C06`: with accepted mixed-family mechanism rows remaining in SQLite and `sqlite-vec` now available locally, the first vector retrieval surface should stay SQLite-native unless a later capability gap proves otherwise.
- Inherits `C07`: sparse retrieval can now target parsed discussion/model/result sections and section-backed evidence snippets instead of abstract-only text.
- Inherits `C08`: structured retrieval should read `mechanism_fingerprints` directly, and dense retrieval should treat serialized `fingerprint_text` as a first-class embedding surface.
- Inherits completed `C09`: retrieval should join `mechanism_exposure_scores` directly and treat `underexploited_score` / `worth_followup_score` as first-class reranking priors rather than recomputing exposure heuristics in the query layer.
- Inherits current local toolchain state: `sqlite-vec` and its Python binding are already installed, while MLX and `sentence-transformers` should be treated as the primary and fallback local embedding paths respectively.
- Inherits the canonical vector strategy: the production ANN index should start with `Qwen/Qwen3-Embedding-0.6B` at `512` dimensions, while `BAAI/bge-m3` stays a separate exploratory index and `Alibaba-NLP/gte-Qwen2-7B-instruct` stays a reranking-only surface.
- Completed in `C10`: the first shipped dense baseline is deterministic hashing so the retrieval contract is benchmarkable even before the canonical local embedder is wired in; later work should swap the backend, not redesign the retrieval tables or benchmark loop.

## C11: Queryless Mining And Local Reranking

- Status: `completed`
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

- Status: `completed`
- Completed on: `2026-03-26`
- Commit SHA: `recorded in the completing git commit for C11`
- Operator: `Codex`
- Reviewer:
- Verification:
  - added `scripts/mine_queryless_candidates.py` plus `npm run mine:queryless` to score and persist ranked hits across all six queryless mining modes
  - extended `sql/paperview_schema.sql` with canonical `queryless_candidate_hits` persistence so later analyst/ranking work can read auditable reranker outputs instead of transient top-k lists
  - enriched `scripts/build_retrieval_stack.py` `source_json` payloads with mechanism traits, blocker fields, and full fingerprint facets so C11 can rerank off persisted retrieval documents without re-reading raw extraction JSON
  - verified the end-to-end C11 flow on `/tmp/paperview-c11-test.sqlite3` by running `build_retrieval_stack.py` and `mine_queryless_candidates.py`, which produced persisted ranked hits for all six mining modes
- Completion notes:
  - queryless mining now persists ranked candidate pairs for `structural_near_lexical_far`, `tradecore_near_jargon_far`, `bridge_mechanisms_across_families`, `zero_seed_vocabulary_holdouts`, `contradiction_mining`, and `rare_fingerprint_combinations_with_high_fit`
  - each persisted hit now carries explicit `structural_similarity_score`, `lexical_distance_score`, `transfer_plausibility_score`, `blocker_penalty_score`, and mode-specific reranker output
  - rationale payloads now retain section labels, mechanism traits, blocker context, evidence excerpts, and score breakdowns so later analyst adjudication can inspect why a pair surfaced

### Upstream Impact Notes

- Inherits `C07`: queryless mining should be able to inspect section-backed evidence snippets and section labels, not only mechanism summaries.
- Inherits completed `C09`: mining jobs should use `underexploited_score` to prioritize rare/high-fit mechanisms before adding heavier reranking passes.
- Inherits the canonical vector strategy: queryless mining should compare candidates within one production vector space at a time, while any `bge-m3` exploratory mining or `gte-Qwen2-7B-instruct` reranking should be logged as separate phases rather than blended scores.
- Inherits completed `C10`: queryless mining should read persisted `mechanism_retrieval_documents`, `mechanism_dense_embeddings`, and `mechanism_graph_edges` instead of rebuilding candidate corpora inline.
- Completed in `C11`: downstream work should treat `queryless_candidate_hits` as the canonical ranked mining queue, including its per-mode reranker sub-scores and rationale payloads, rather than reconstructing candidate pairs from retrieval-only tables.

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
- Inherits `C08`: family assembly and hard gating should cluster on canonical mechanism-level fingerprints and can down-rank families that rely heavily on queued normalization ambiguities.
- Inherits completed `C09`: analyst feedback should attach to persisted mechanism-level feature rows in `mechanism_exposure_scores` so weight updates do not have to reconstruct the bootstrap feature set from raw JSON.
- Inherits completed `C10`: analyst adjudication should store view-aware evidence against persisted retrieval ranks and candidate lists from `retrieval_benchmark_results`, not only against manually assembled examples.
- Inherits completed `C11`: analyst adjudication should attach directly to persisted `queryless_candidate_hits` rows and their reranker sub-scores so accept/reject labels can update mode weights without reverse-engineering why a pair surfaced.

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

- Inherits `C02`: the hard-gate layer should use the canonical blocker fields directly rather than reconstructing fragility or anti-transfer heuristics downstream.
- Inherits completed `C09`: ranking should consume persisted `exposure_score`, `underexploited_score`, and `worth_followup_score` as canonical priors before adding family-level aggregation.
- Inherits completed `C10`: candidate family assembly should start from persisted hybrid retrieval neighborhoods and benchmarked retrieval views, not from a single dense nearest-neighbor list.
- Inherits completed `C11`: hard-gated ranking should start from persisted `queryless_candidate_hits` and preserve the mode-wise `structural_similarity_score`, `lexical_distance_score`, `transfer_plausibility_score`, and `blocker_penalty_score` as inspectable inputs into family assembly.

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
