---
doc_type: briefing
owner: devrel
review_policy: periodic-7
reviewed: 2026-03-28
status: active
summary: Canonical active development plan for building the Unrealized Idea Index with Stranding Overlay from the current embedding-first arXiv discovery system.
tags:
  - docs
  - briefing
  - research
  - discovery
  - embeddings
  - development-plan
written: 2026-03-25
---

# Unrealized Idea Index Development Plan

## Summary

This is the canonical active development doc for the repo.

It defines:

- the product
- the architecture
- the ordered execution path
- the per-commit signoff rules
- the current completed and incomplete stages

This doc must be updated before every commit that advances the system. The commit should include the doc update, so the plan is always true at the commit that claims progress.

---

## Human-Readable Plan

## Product Definition

The target system is:

**Unrealized Idea Index with Stranding Overlay**

One ranking system over arXiv using three kinds of evidence:

1. latent similarity
2. translation gap
3. stranding evidence

The system should find smart technical ideas that existed before 2024 but had no realized market connection, or only a premature one.

It must support two final output surfaces from the same pipeline:

1. **Unrealized Ideas Index**
   Cross-domain, bridge-heavy, mechanism-close and domain-far.

2. **Stranded Result Ledger**
   Mostly q-fin, practical, date-aware, and explicit about why a result was stranded.

## Canonical Question

The system should no longer ask:

> What mechanism does this paper contain?

It should ask:

> Does this paper or region contain a smart solution pattern that was not yet connected to our target markets before 2024?

## Hard Rules

- Do not start with full-corpus semantic extraction.
- Do not force every paper into an edge card.
- Do not let local models paraphrase papers into slot-shaped pseudo-insight.
- Do not treat UMAP or cluster pictures as the product surface.
- Do not let failed candidates pollute the shortlist.
- If the fast path conflicts with the right architecture, choose the right architecture.

## Time Firewall

- **Discovery window:** through `2023-12-31`
- **Holdout reality-check:** `2024+`

The holdout is for validation and echo detection, not for primary discovery ranking.

## Corpus Split

Use arXiv only, split into four logical corpora:

1. **Discovery corpus**
   All arXiv papers up to `2023-12-31`.

2. **Realized market corpus**
   Pre-2024 q-fin plus explicitly market, trading, arbitrage, options, prediction-market, and hedging papers.

3. **Stranded-alpha slice**
   `q-fin` papers from `2015–2023`.

4. **Holdout corpus**
   `2024+` q-fin and market-adjacent papers.

## Canonical Pipeline

The discovery path is:

1. `harvest`
2. `views`
3. `embed`
4. `knn`
5. `cluster`
6. `probe`
7. `score`
8. `review`
9. `shortlist`
10. `interpret`
11. `validate`
12. `publish`

This is still map-first:

1. `map`
2. `probe`
3. `shortlist`
4. `interpret`
5. `validate`

## Score Families

Every paper, region, bridge, or shortlist item should eventually carry:

- challenge affinity
- positive-anchor affinity
- negative-anchor affinity
- translation-gap score
- stranding score
- bridge score
- composition score
- holdout echo score
- genericity penalty
- realized-market leakage penalty

The intended shape is:

`unrealized_idea_score = translation_gap + challenge_affinity + positive_anchor_affinity + bridge_score + composition_score + stranding_score + holdout_echo - negative_anchor_affinity - genericity_penalty - realized_market_leakage`

## Representation Views

The canonical text-view set should converge toward:

- problem view
- mechanism view
- regime / constraint view
- stranding view

The current store also has the lower-level operational views used to build toward that:

- `title_abs`
- `abs_only`
- `title_abs_cats`
- `title_only`
- `category_string`
- `section_or_abs`

## Sparse Stranding Overlay

The stranding layer should use weighted sparse signals, not hard binary filters.

Important sparse families:

- instrument-gap markers
- access-barrier markers
- result-specificity markers
- resolution-mechanics markers
- survey penalty
- empirical-only penalty

Do not use naive `.contains()`.
Use regex with negation handling and/or BM25/TF-IDF style sparse scoring.

## Second-Pass Interpretation

Only shortlisted items should reach model interpretation.

Allowed outputs:

- `TRANSLATION_CANDIDATE`
- `COMPOSITIONAL_CANDIDATE`
- `STRANDED_QFIN_RESULT`
- `NO_TRANSLATION`

Strict JSON only. No prose-only classification.

## Final Ledger Shape

For any interpreted item that survives:

- paper
- date
- home domain
- one-sentence result
- why it was stranded or unrealized
- assumed instrument / environment
- modern equivalent
- first test
- gap to close
- priority tier
- direct / calibration / adaptation

---

## Commit Protocol

## Non-Negotiable Rule

Before every commit:

1. update this doc
2. update the stage status table
3. update the active signoff block
4. include the doc update in the same commit as the code and artifacts it describes

No commit should claim progress without this doc being true at that commit.

## Signoff Instructions

Before creating a commit, fill or update the following block in this doc.

Keep only one active signoff block at a time: the next intended commit.

### Active Signoff Block

- Commit scope:
- Why this commit exists:
- Stages touched:
- Code paths touched:
- Commands run:
- Tests run:
- Artifacts produced:
- Acceptance result:
- Open risks after commit:
- Next intended commit:
- Signoff status: `draft | ready | committed`
- Last updated:

### Commit Gate

Do not mark a commit `ready` unless:

- the affected stage has a passing fixture or unit test
- the canonical store contract still holds
- the new stage ran against the real store if the stage is already beyond fixture-only status
- the generated artifact path is recorded
- this doc reflects the new state truthfully

---

## Ordered Commit Plan

Each row is intended to be completable in one or more commits, but the order is canonical.

## Stage Table

| Stage | Goal | Status | Canonical Output |
| --- | --- | --- | --- |
| `S00` | canonical plan reset | `done` | this doc |
| `S01` | canonical foundation tables | `done` | `papers`, `text_views`, `embedding_spaces`, `view_embedding_meta`, `run_events` |
| `S02` | canonical text-view materialization | `done` | `text_views` rows + metrics |
| `S03` | local embedding materialization | `done` | embedding metadata + vec DB |
| `S04` | canonical KNN stage | `done` | `knn_edges` |
| `S05` | canonical graph / cluster stage | `done` | `clusters`, `cluster_members` |
| `S06` | canonical probe stage | `done` | `anchors`, `agitator_patterns`, `probe_hits` |
| `S07` | realized-market firewall corpus | `in_progress` | canonical corpus memberships + realized-market anti-realization set |
| `S08` | stranding sparse scoring layer | `done` | stranding features + scores |
| `S09` | bridge / composition / contrast operators | `done` | bridge, composition, contrast, and negative-space artifacts |
| `S10` | review packet generation | `done` | region packets and dossiers |
| `S11` | shortlist stage | `done` | shortlist rows + rationale |
| `S12` | selective interpretation contract | `done` | JSON interpretations only |
| `S13` | holdout echo validation | `done` | holdout echo metrics |
| `S14` | Unrealized Ideas Index | `done` | human-facing index |
| `S15` | Stranded Result Ledger | `done` | human-facing ledger |
| `S16` | active / archive cleanup | `in_progress` | clean active pipeline surface |

## Completed Stages

### `S01` Canonical Foundation

Completed:

- canonical discovery foundation tables added to `paperview.sqlite3`
- initialization path updated and verified

### `S02` Text Views

Completed:

- canonical `text_views` materializer added
- full store materialized

Current live result:

- `24,203` papers
- `145,218` text views

### `S03` Embeddings

Completed:

- staged embedding materializer added
- canonical metadata kept in main store
- vec tables written to run-local DB

Current live result:

- `4` embedding spaces
- `96,812` embedding metadata rows

### `S04` KNN

Completed:

- canonical `knn_edges` stage added
- full pass materialized

Current live result:

- `2,904,360` KNN edges
- `k = 30`

### `S05` Clusters

Completed:

- canonical `clusters` and `cluster_members`
- fused paper-level mutual-KNN clustering

Current live result:

- `72` coarse clusters
- `78` mid clusters
- `92` local clusters

### `S06` Probes

Completed:

- canonical anchor config
- canonical agitator pattern state
- canonical `probe_hits`

Current live result:

- `7` anchors
- `10` patterns
- `250` probe hits in the current full run

## Remaining Execution Path

### `S07` Realized-Market Firewall

Build:

- canonical corpus-membership layer for:
  - `discovery`
  - `realized_market`
  - `stranded_alpha`
  - `holdout`
- explicit realized market corpus definition
- anti-realization slice from pre-2024 market discourse

Accept when:

- realized corpus can be queried directly
- the time firewall and later holdout logic use the same canonical membership surface
- discovery ranking can score distance from it

Current status:

- canonical `corpus_memberships` foundation is implemented and live
- current live membership counts:
  - `discovery`: `17,323`
  - `realized_market`: `4,579`
  - `stranded_alpha`: `12,255`
  - `holdout`: `6,880`
- the stage is not complete yet because the realized-market slice now reflects explicit market discourse, but later commits still need stronger anti-realization negatives and sparse stranding features before ranking can use it well

### `S08` Stranding Sparse Scoring

Build:

- sparse stranding features
- regex / BM25 / TF-IDF layer with negation handling
- instrument-gap, access-barrier, result-specificity, and resolution-mechanics signals

Accept when:

- scores exist in canonical outputs
- q-fin stranded results can be surfaced without LLM interpretation

Current status:

- canonical `stranding_scores` foundation is implemented and live
- current live score counts:
  - `scored_papers`: `17,323`
  - `positive_score_papers`: `747`
  - `realized_market_positive_papers`: `238`
  - `stranded_alpha_positive_papers`: `654`
  - `top_score`: `0.377925`
- the stage is complete: the sparse prior is now continuous, negation-aware, IDF-dampened, weighted across five positive signal families, and guarded by structured penalties rather than a hard floor
- the sparse layer is now mature enough to serve as a stranding overlay inside the later composite rank; further changes belong in downstream bridge, composition, translation-gap, and shortlist stages unless live `S09+` results expose a concrete scorer defect

### `S09` Bridge / Composition / Contrast Operators

Build:

- near-A / far-B retrieval
- bridge-node scoring
- multi-anchor composition scoring
- negative-space search

Accept when:

- at least some surfaced regions come from bridge or composition logic, not only local similarity

Current status:

- canonical `bridge_candidates`, `composition_candidates`, `contrast_candidates`, and `negative_space_candidates` foundations are implemented and live
- current live bridge counts:
  - `positive_anchor_count`: `6`
  - `anchor_pair_count`: `15`
  - `pairs_with_candidates`: `15`
  - `bridge_candidate_count`: `300`
  - `top_score`: `2.441005`
- current live composition counts:
  - `positive_anchor_count`: `6`
  - `anchor_pair_count`: `15`
  - `pairs_with_candidates`: `15`
  - `composition_candidate_count`: `300`
  - `top_score`: `3.202651`
- current live contrast counts:
  - `contrast_pattern_count`: `4`
  - `patterns_with_candidates`: `4`
  - `contrast_candidate_count`: `80`
  - `top_score`: `3.889789`
- current live negative-space counts:
  - `negative_anchor_count`: `1`
  - `anchors_with_candidates`: `1`
  - `negative_space_candidate_count`: `25`
  - `top_score`: `2.930531`
- the stage is complete: the canonical store now has live bridge, composition, contrast, and negative-space operators, so downstream review and shortlist work can use first-class region surfaces rather than local-similarity-only retrieval
- the next canonical step is `S10` review packet generation

### `S10` Review Packets

Build:

- cluster packets
- bridge dossiers
- composition packets
- stranded q-fin resurfacing packets

Accept when:

- packet generation is deterministic and wired to current canonical tables

Current status:

- canonical `review_packets` foundation is implemented and live
- current live packet counts:
  - `cluster`: `6`
  - `bridge`: `6`
  - `composition`: `6`
  - `stranded_qfin`: `6`
  - `total_packets`: `24`
- the stage is complete: packet markdown is generated deterministically from canonical tables, written to disk, and persisted in the main store for later shortlist and interpretation stages
- the next canonical step is `S11` shortlist foundation

### `S11` Shortlist

Build:

- shortlist table and rationale surface
- acceptance / rejection status
- provenance for why each item was shortlisted

Accept when:

- shortlist can mix papers, regions, bridges, and compositions
- rationale is persisted, not only rendered

Current status:

- canonical `shortlist_items` foundation is implemented and live
- current live shortlist counts:
  - `shortlist_count`: `24`
  - `bridge_or_composition_count`: `12`
  - `bridge`: `6`
  - `composition`: `6`
  - `cluster`: `6`
  - `paper`: `6`
- the stage is complete: shortlist rows, ranks, statuses, and rationale are persisted in the main store and emitted as machine-readable artifacts
- the current run exhausts the packet pool because the configured shortlist size exceeds the number of review packets, but the canonical shortlist contract itself is now in place and can be refined downstream if later stages need tighter selection pressure
- the next canonical step is `S12` selective interpretation contract

### `S12` Selective Interpretation

Build:

- strict JSON interpretation contract
- only on shortlisted slices
- no full-corpus semantic extraction

Accept when:

- only allowed outputs are emitted
- negative class is honored

Current status:

- canonical `selective_interpretations` storage contract is implemented in the main store
- strict JSON interpretation prompt and schema are checked in and live
- current live batch-preparation counts:
  - `prepared_count`: `24`
  - `bridge`: `6`
  - `composition`: `6`
  - `cluster`: `6`
  - `paper`: `6`
- current live ingestion counts:
  - `accepted_count`: `3`
  - `rejected_count`: `1`
  - `TRANSLATION_CANDIDATE`: `1`
  - `COMPOSITIONAL_CANDIDATE`: `1`
  - `NO_TRANSLATION`: `1`
- the stage is complete: selective interpretation is shortlist-gated, prompt- and schema-pinned, and canonically ingests only allowed JSON outputs while honoring the negative class
- the next canonical step is `S13` holdout echo validation

### `S13` Holdout Echo

Build:

- holdout echo scoring against `2024+` market-adjacent papers

Accept when:

- pre-2024 candidates can be checked for later discourse echoes

Current status:

- canonical `holdout_echoes` foundation is implemented and live
- current live echo counts:
  - `interpreted_shortlist_count`: `3`
  - `shortlists_with_echoes`: `3`
  - `echo_count`: `9`
  - `top_k`: `3`
- the stage is complete: interpreted shortlist items can now be checked against the canonical `holdout` corpus through the existing embedding space instead of being treated as timeless hypotheses
- the current echo score is still embedding-only proximity over representative source papers; richer discourse matching can be added later if `S14` or `S15` surfaces a concrete validation defect, but the canonical holdout-check contract now exists
- the next canonical step is `S14` Unrealized Ideas Index

### `S14` Unrealized Ideas Index

Build:

- human-facing ranked output for cross-domain and bridge-heavy discoveries

Accept when:

- items are mechanism-close and domain-far
- realized-market leakage is visibly controlled

Current status:

- canonical `unrealized_idea_index` foundation is implemented and live
- current live index counts:
  - `entry_count`: `1`
  - `TRANSLATION_CANDIDATE`: `0`
  - `COMPOSITIONAL_CANDIDATE`: `1`
  - `STRANDED_QFIN_RESULT`: `0`
  - `top_ranked_shortlist_id`: `composition:queue_value_passive_quoting__refill_lag_local_shock`
- the stage foundation is now in place: interpreted shortlist items are rendered into a human-facing markdown index and persisted as canonical ranked rows instead of living only as packet, shortlist, and validation fragments
- realized-market leakage is now visible in the ranking surface itself through `realized_market_leakage_score` and `domain_far_score`, and fully leaked rows are now excluded from publication rather than merely demoted
- the stage is complete: the human-facing index now publishes only mechanism-close, domain-far survivors and makes realized-market leakage explicit at publication time
- the current live index is narrow, but breadth expansion is no longer required for the stage contract itself and can happen later through improved shortlist and interpretation coverage
- the next canonical step is `S15` Stranded Result Ledger

### `S15` Stranded Result Ledger

Build:

- practical ledger view for stranded q-fin results

Accept when:

- each item has result, stranding rationale, modern equivalent, first test, and gap to close

Current status:

- canonical `stranded_result_ledger` foundation is implemented and live
- current live ledger counts:
  - `entry_count`: `0`
  - `p1`: `0`
  - `p2`: `0`
  - `p3`: `0`
  - `top_ranked_paper_id`: `null`
- the stage foundation is now in place: interpreted stranded q-fin paper rows can publish into a practical ledger surface with date, home domain, priority, relation type, and execution-oriented fields
- the current live run is empty because the checked-in interpretation ingestion has no surviving `STRANDED_QFIN_RESULT` rows, which is a data state rather than a ledger contract failure
- the stage is complete: the ledger contract now exists canonically, and an empty live run is acceptable because the stage requires a correct publication surface, not fabricated survivors
- the next canonical step is `S16` Active / Archive Cleanup

### `S16` Active / Archive Cleanup

Build:

- define the active staged command set explicitly
- move superseded phase scripts and one-off dead-end utilities out of the active top-level working surface
- preserve historical logic in an archival location instead of deleting context blindly

Accept when:

- `scripts/` reads like the current pipeline rather than the full archeology of prior attempts
- superseded surfaces are preserved, but they no longer compete with canonical stages

Current status:

- `scripts/archive/` is now established as the canonical home for preserved-but-inactive script surfaces
- first archived slice moved to `scripts/archive/noncanonical-pilots/`:
  - `materialize_adjacent_seeding_plan.py`
  - `materialize_discovery_benchmark.py`
  - `materialize_mixed_family_pilot.py`
- second archived slice moved to `scripts/archive/noncanonical-benchmarks/`:
  - `benchmark_retrieval_stack.py`
- third archived slice moved to `scripts/archive/noncanonical-research-packs/`:
  - `materialize_research_finding_pack.py`
  - `export_cluster_cartography.py`
- this first slice is intentionally narrow: it archives tracked pilot utilities that are not part of the canonical staged command set and do not have active package-script entrypoints
- the benchmark cleanup pass removed `retrieve:benchmark` from `package.json`, so that archived script no longer competes with the canonical staged commands
- the research-pack cleanup pass removed `research:materialize-findings` from `package.json`, and the archived runner now points at the archived export helper instead of reaching back into the active root
- historical docs still reference `materialize_mixed_family_pilot.py`, which is acceptable for `S16` because the archive preserves the file while removing it from the active script surface
- historical docs still reference `research:materialize-findings`, which is acceptable for `S16` because the archive preserves the implementation while the active package surface is reduced
- the stage remains in progress because extraction-era package commands and other superseded utilities still need later cleanup passes

---

## Development Policy

### Architecture policy

- canonical metadata and provenance belong in the main SQLite store
- `sqlite-vec` remains an embedded retrieval component only
- stage commands should be independently runnable
- stages should produce machine-readable artifacts
- fixtures or unit tests are required before a full-store pass

### Anti-regression policy

- do not reintroduce extraction-first discovery as the primary path
- do not hide canonical state in run-only markdown
- do not make shortlist logic depend on slot-filled model summaries
- do not let a new stage exist only inside the monolithic map runner

### Docs policy for commits

- update this plan first
- then commit code
- then record verification truthfully here

### Repo hygiene policy

- keep the active pipeline surface small and legible
- do not leave obsolete phase scripts in the active root just because they still run
- when a phase is superseded, move it into an archival location such as `scripts/archive/`
- any commit that introduces a new canonical stage should also decide which older scripts remain active and which move to archive
- no new one-off utility should land in the active stage surface without a clear long-term owner

---

## Additional Context For AIs And Future Work

## Current Canonical Commands

- `npm run store:materialize-corpus-memberships`
- `python3 scripts/init_local_store.py --db-path data/structural-analogy/paperview.sqlite3`
- `npm run store:materialize-text-views`
- `npm run store:materialize-view-embeddings`
- `npm run store:materialize-knn`
- `npm run store:materialize-clusters`
- `npm run store:materialize-probes`
- `npm run store:materialize-bridges`
- `npm run store:materialize-compositions`
- `npm run store:materialize-contrasts`
- `npm run store:materialize-negative-space`
- `npm run store:materialize-review-packets`
- `npm run store:materialize-shortlist`
- `npm run store:materialize-selective-interpretation-batch`
- `npm run store:ingest-selective-interpretations`
- `npm run store:materialize-holdout-echoes`
- `npm run store:materialize-unrealized-ideas-index`
- `npm run store:materialize-stranded-result-ledger`
- `npm run score:materialize-stranding`

## Current Canonical Config Inputs

- [corpus.yaml](../../configs/corpus.yaml)
- [embedding_spaces.yaml](../../configs/embedding_spaces.yaml)
- [anchors.yaml](../../configs/anchors.yaml)
- [probes.yaml](../../configs/probes.yaml)
- [cluster.yaml](../../configs/cluster.yaml)
- [shortlist_rules.yaml](../../configs/shortlist_rules.yaml)
- [stranding_signals.yaml](../../configs/stranding_signals.yaml)

## Current Live Artifacts

- text views:
  - `data/structural-analogy/runs/text-views-materialization-20260328/text_view_metrics.json`
- embeddings:
  - `data/structural-analogy/runs/view-embeddings-materialization-20260328/embedding_metrics.json`
- knn:
  - `data/structural-analogy/runs/knn-materialization-20260328/knn_metrics.json`
- clusters:
  - `data/structural-analogy/runs/cluster-materialization-20260328/cluster_metrics.json`
- probes:
  - `data/structural-analogy/runs/probe-materialization-20260328/probe_metrics.json`
- bridges:
  - `data/structural-analogy/runs/bridge-materialization-20260328/bridge_metrics.json`
  - `data/structural-analogy/runs/bridge-materialization-20260328/bridges.jsonl`
- compositions:
  - `data/structural-analogy/runs/composition-materialization-20260328/composition_metrics.json`
  - `data/structural-analogy/runs/composition-materialization-20260328/compositions.jsonl`
- contrasts:
  - `data/structural-analogy/runs/contrast-materialization-20260328/contrast_metrics.json`
  - `data/structural-analogy/runs/contrast-materialization-20260328/contrasts.jsonl`
- negative space:
  - `data/structural-analogy/runs/negative-space-materialization-20260328/negative_space_metrics.json`
  - `data/structural-analogy/runs/negative-space-materialization-20260328/negative_space.jsonl`
- review packets:
  - `data/structural-analogy/runs/review-packet-materialization-20260328/review_packet_metrics.json`
  - `data/structural-analogy/runs/review-packet-materialization-20260328/review_packets/`
- shortlist:
  - `data/structural-analogy/runs/shortlist-materialization-20260328/shortlist_metrics.json`
  - `data/structural-analogy/runs/shortlist-materialization-20260328/shortlist.jsonl`
- selective interpretation batch:
  - `data/structural-analogy/runs/selective-interpretation-batch-20260328/interpretation_batch_metrics.json`
  - `data/structural-analogy/runs/selective-interpretation-batch-20260328/interpretation_batch.jsonl`
- selective interpretation ingestion:
  - `data/structural-analogy/runs/selective-interpretation-ingestion-20260328/interpretation_ingestion_metrics.json`
  - `data/structural-analogy/runs/selective-interpretation-ingestion-20260328/interpretation_rejections.jsonl`
- holdout echoes:
  - `data/structural-analogy/runs/holdout-echo-materialization-20260328/holdout_echo_metrics.json`
  - `data/structural-analogy/runs/holdout-echo-materialization-20260328/holdout_echoes.jsonl`
- unrealized ideas index:
  - `data/structural-analogy/runs/unrealized-ideas-index-20260328/unrealized_ideas_index_metrics.json`
  - `data/structural-analogy/runs/unrealized-ideas-index-20260328/unrealized_ideas_index.jsonl`
  - `data/structural-analogy/runs/unrealized-ideas-index-20260328/unrealized_ideas_index.md`
- stranded result ledger:
  - `data/structural-analogy/runs/stranded-result-ledger-20260328/stranded_result_ledger_metrics.json`
  - `data/structural-analogy/runs/stranded-result-ledger-20260328/stranded_result_ledger.jsonl`
  - `data/structural-analogy/runs/stranded-result-ledger-20260328/stranded_result_ledger.md`
- corpus memberships:
  - `data/structural-analogy/runs/corpus-membership-materialization-20260328/corpus_membership_metrics.json`
- stranding scores:
  - `data/structural-analogy/runs/stranding-score-materialization-20260328/stranding_score_metrics.json`
  - `data/structural-analogy/runs/stranding-score-materialization-20260328/stranding_score_top.jsonl`

## Active Signoff Block

- Commit scope: `s16-active-archive-cleanup-foundation`
- Why this commit exists: continue the cleanup pass by removing the noncanonical `schemas:validate` package command, which is not part of the canonical staged command set
- Stages touched: `S16`
- Code paths touched: `docs/briefings/2026-03-25-structural-analogy-engine-plan.md`, `package.json`
- Commands run: `npm run codecontext:scope -- docs/briefings/2026-03-25-structural-analogy-engine-plan.md`, `git grep -n '\"schemas:validate\"' package.json docs scripts tests`, `git ls-files scripts/validate_schema_examples.py`, `git status --short package.json scripts/validate_schema_examples.py`, `npm run docs:lint`
- Tests run: `npm run docs:lint`
- Artifacts produced: `none`
- Acceptance result: `the active package surface is smaller: schemas:validate is removed because it is not part of the canonical staged command set while the tracked helper script remains in place for a later archive decision`
- Open risks after commit: `tracked noncanonical scripts still remain in the active root, so this slice only removes the schema-validation package entrypoint while leaving broader archival decisions for follow-up commits`
- Next intended commit: `S16 active/archive cleanup foundation`
- Signoff status: `ready`
- Last updated: `2026-03-28`
