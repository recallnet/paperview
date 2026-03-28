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
| `S08` | stranding sparse scoring layer | `pending` | stranding features + scores |
| `S09` | bridge / composition / contrast operators | `pending` | bridge and composition artifacts |
| `S10` | review packet generation | `pending` | region packets and dossiers |
| `S11` | shortlist stage | `pending` | shortlist rows + rationale |
| `S12` | selective interpretation contract | `pending` | JSON interpretations only |
| `S13` | holdout echo validation | `pending` | holdout echo metrics |
| `S14` | Unrealized Ideas Index | `pending` | human-facing index |
| `S15` | Stranded Result Ledger | `pending` | human-facing ledger |
| `S16` | active / archive cleanup | `pending` | clean active pipeline surface |

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
  - `positive_score_papers`: `1,076`
  - `realized_market_positive_papers`: `314`
  - `stranded_alpha_positive_papers`: `943`
  - `top_score`: `0.412661`
- the stage is not complete yet because low-diversity positives, explicit market-discourse leakage, and generic result-specificity cues are now all penalized without reintroducing a hard floor, phrase-frequency dampening is wired in, and implementation/data-availability barriers are now represented, but later commits still need richer sparse features before the signal is ready for composite ranking

### `S09` Bridge / Composition / Contrast Operators

Build:

- near-A / far-B retrieval
- bridge-node scoring
- multi-anchor composition scoring
- negative-space search

Accept when:

- at least some surfaced regions come from bridge or composition logic, not only local similarity

### `S10` Review Packets

Build:

- cluster packets
- bridge dossiers
- composition packets
- stranded q-fin resurfacing packets

Accept when:

- packet generation is deterministic and wired to current canonical tables

### `S11` Shortlist

Build:

- shortlist table and rationale surface
- acceptance / rejection status
- provenance for why each item was shortlisted

Accept when:

- shortlist can mix papers, regions, bridges, and compositions
- rationale is persisted, not only rendered

### `S12` Selective Interpretation

Build:

- strict JSON interpretation contract
- only on shortlisted slices
- no full-corpus semantic extraction

Accept when:

- only allowed outputs are emitted
- negative class is honored

### `S13` Holdout Echo

Build:

- holdout echo scoring against `2024+` market-adjacent papers

Accept when:

- pre-2024 candidates can be checked for later discourse echoes

### `S14` Unrealized Ideas Index

Build:

- human-facing ranked output for cross-domain and bridge-heavy discoveries

Accept when:

- items are mechanism-close and domain-far
- realized-market leakage is visibly controlled

### `S15` Stranded Result Ledger

Build:

- practical ledger view for stranded q-fin results

Accept when:

- each item has result, stranding rationale, modern equivalent, first test, and gap to close

### `S16` Active / Archive Cleanup

Build:

- define the active staged command set explicitly
- move superseded phase scripts and one-off dead-end utilities out of the active top-level working surface
- preserve historical logic in an archival location instead of deleting context blindly

Accept when:

- `scripts/` reads like the current pipeline rather than the full archeology of prior attempts
- superseded surfaces are preserved, but they no longer compete with canonical stages

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
- corpus memberships:
  - `data/structural-analogy/runs/corpus-membership-materialization-20260328/corpus_membership_metrics.json`
- stranding scores:
  - `data/structural-analogy/runs/stranding-score-materialization-20260328/stranding_score_metrics.json`
  - `data/structural-analogy/runs/stranding-score-materialization-20260328/stranding_score_top.jsonl`

## Active Signoff Block

- Commit scope: `s08-implementation-barrier-signals`
- Why this commit exists: add a missing sparse feature family for implementation and data-availability barriers so the stranding prior is not limited to instrument, access, result, and resolution cues
- Stages touched: `S08`
- Code paths touched: `docs/briefings/2026-03-25-structural-analogy-engine-plan.md`, `configs/stranding_signals.yaml`, `sql/paperview_schema.sql`, `scripts/init_local_store.py`, `scripts/materialize_stranding_scores.py`, `tests/test_init_local_store.py`, `tests/test_materialize_stranding_scores.py`
- Commands run: `python3 -m unittest -v tests.test_init_local_store tests.test_materialize_stranding_scores`, `python3 scripts/init_local_store.py --db-path data/structural-analogy/paperview.sqlite3`, `npm run score:materialize-stranding -- --run-id stranding-score-materialization-20260328`, `npm run codecontext:py -- scripts/init_local_store.py`, `npm run codecontext:py -- scripts/materialize_stranding_scores.py`, `npm run codecontext:diff -- scripts/init_local_store.py`, `npm run codecontext:diff -- scripts/materialize_stranding_scores.py`, `npm run docs:lint`
- Tests run: `tests.test_init_local_store`, `tests.test_materialize_stranding_scores`
- Artifacts produced: `data/structural-analogy/runs/stranding-score-materialization-20260328/stranding_score_metrics.json`
- Acceptance result: `implementation and data-availability barriers are now first-class sparse signals; the fixture proves the new family scores and the live positive surface widened from 867 to 1,076 with stranded-alpha positives rising to 943`
- Open risks after commit: `the new feature family must add useful implementation-friction coverage without reintroducing broad generic over-inclusion`
- Next intended commit: `S08 recall recovery via structured penalty refinement`
- Signoff status: `ready`
- Last updated: `2026-03-28`
