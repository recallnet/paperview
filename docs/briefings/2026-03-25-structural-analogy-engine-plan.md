---
doc_type: briefing
owner: devrel
review_policy: periodic-7
reviewed: 2026-03-28
status: active
summary: Canonical active development plan for building the Unrealized Idea Index with Stranding Overlay and Transition-State Workbench from the current embedding-first arXiv discovery system.
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

**Unrealized Idea Index with Stranding Overlay and Transition-State Workbench**

One unified system over arXiv with three scoring layers and four publication surfaces.

### Three Scoring Layers

1. **Latent discovery** — broad search over arXiv using embeddings, bridge/composition operators, and challenge-anchor affinity
2. **Stranding overlay** — pragmatic q-fin rescue using sparse BM25/TF-IDF-style features as a prior
3. **Transition-state workbench** — dedicated operator family for the microstructure seams the current run already identifies as the richest evidence cluster

### Four Publication Surfaces

1. **Unrealized Ideas Index** — cross-domain, bridge-heavy, mechanism-close and domain-far
2. **Stranded Result Ledger** — mostly q-fin, directly practical, date-aware
3. **Findings and Throwaways** — required every run: top survivors, top rejected, why rejected, top near-misses by operator family
4. **Transition-State Microstructure Ledger** — dedicated surface for queue x refill, auction x refill, auction x queue, maker-retreat x queue, parity-propagation x refill

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
- transition-state score
- genericity penalty
- realized-market leakage penalty

The intended shape is:

`unrealized_idea_score = translation_gap + challenge_affinity + positive_anchor_affinity + bridge_score + composition_score + stranding_score + holdout_echo + transition_state_score - negative_anchor_affinity - genericity_penalty - realized_market_leakage`

### Transition-State Score

Boost candidates that sit near:

- queue-value / passive quoting
- refill-lag / resiliency
- auction handoff / continuous-market transition
- maker-retreat / inventory stress
- parity propagation with delayed repair

This is a first-class score family derived from the current run's strongest evidence cluster.

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
| `S07` | realized-market firewall corpus | `done` | canonical corpus memberships + realized-market anti-realization set |
| `S08` | stranding sparse scoring layer | `done` | stranding features + scores |
| `S09` | bridge / composition / contrast operators | `done` | bridge, composition, contrast, and negative-space artifacts |
| `S10` | review packet generation | `done` | region packets and dossiers |
| `S11` | shortlist stage | `done` | shortlist rows + rationale |
| `S12` | selective interpretation contract | `done` | JSON interpretations only |
| `S13` | holdout echo validation | `done` | holdout echo metrics |
| `S14` | Unrealized Ideas Index | `done` | human-facing index |
| `S15` | Stranded Result Ledger | `done` | human-facing ledger |
| `S16` | active / archive cleanup | `done` | clean active pipeline surface |
| `S17` | transition-state anchor and probe config | `done` | transition-state anchors, probes, and probe hits |
| `S18` | transition-state score materializer | `done` | `transition_state_scores` table + metrics |
| `S19` | transition-state operator | `done` | `transition_state_candidates` table + artifacts |
| `S20` | stranded q-fin resurfacing operator | `done` | `stranded_resurfacing_candidates` table + artifacts |
| `S21` | findings and throwaways materializer | `done` | `findings_and_throwaways.*` per-run report |
| `S22` | transition-state microstructure ledger | `done` | `transition_state_ledger.*` publication surface |
| `S23` | enhanced interpretation batch | `draft` | expanded top-10-20 per operator family interpretation |
| `S24` | re-materialize all publication surfaces | `pending` | all four publication outputs from a single run |

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

## Stage Status Detail

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
- the stage is complete: the canonical membership surface now powers the time firewall, explicit realized-market discourse slice, stranded-alpha slice, and holdout split used by the later live scoring, shortlist, interpretation, and validation stages
- later stages already depend on this same membership surface in production, so the firewall contract is no longer provisional even though downstream scoring layers add extra anti-realization pressure on top of it

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
- fourth archived slice moved to `scripts/archive/noncanonical-corpus-helpers/`:
  - `corpus_status.py`
  - `corpus_inventory.py`
  - `corpus_readiness_report.py`
- fifth archived slice moved to `scripts/archive/noncanonical-corpus-pipeline/`:
  - `launch_qfin_download.py`
  - `reconcile_failures.py`
  - `retry_failures.py`
  - `run_qfin_pipeline.py`
- sixth archived slice moved to `scripts/archive/noncanonical-edge-reset/`:
  - `materialize_edge_reset_slice.py`
  - `generate_edge_cards.py`
  - `generate_edge_reset_funnel_report.py`
  - `export_edge_semantic_trace.py`
  - `edge_semantic_validity.py`
- seventh archived slice moved to `scripts/archive/noncanonical-ranking-stack/`:
  - `normalize_mechanism_fingerprints.py`
  - `score_mechanism_exposure.py`
  - `build_retrieval_stack.py`
  - `mine_queryless_candidates.py`
  - `bootstrap_queryless_labels.py`
  - `run_analyst_adjudication.py`
  - `build_candidate_family_ranking.py`
- eighth archived slice moved to `scripts/archive/noncanonical-downstream-review/`:
  - `generate_strategy_briefs.py`
  - `materialize_live_downstream_run.py`
  - `assess_live_brief_queue.py`
  - `prepare_gate_c_review.py`
  - `review_gate_c.py`
- ninth archived slice moved to `scripts/archive/noncanonical-extraction-workflow/`:
  - `create_pilot_batch.py`
  - `create_extraction_run.py`
  - `ingest_extraction_responses.py`
  - `review_extraction_quality.py`
  - `run_local_mlx_extraction.py`
  - `review_and_ingest_extractions.py`
  - `prepare_section_evidence.py`
  - `promote_paper_extractions.py`
- this first slice is intentionally narrow: it archives tracked pilot utilities that are not part of the canonical staged command set and do not have active package-script entrypoints
- the benchmark cleanup pass removed `retrieve:benchmark` from `package.json`, so that archived script no longer competes with the canonical staged commands
- the research-pack cleanup pass removed `research:materialize-findings` from `package.json`, and the archived runner now points at the archived export helper instead of reaching back into the active root
- the corpus-helper cleanup pass removed the old `corpus:*` helper entrypoints from `package.json` and moved the untracked helper files into the archive, so those root-level status utilities no longer compete with the canonical stages
- the corpus-pipeline cleanup pass moved the old launch, retry, reconcile, and pipeline runners into the archive and patched their internal imports and subprocess paths so the archived workflow remains self-contained
- the edge-reset cleanup pass moved the old edge-reset runner, card generator, funnel report, and semantic helpers into the archive, and the archived runner now points at its archived card generator instead of the former root path
- the ranking-stack cleanup pass moved the old fingerprint, retrieval, queryless, adjudication, and ranking scripts into the archive, and the archived edge-reset runner now points at the archived ranking stack instead of the former root paths
- the downstream-review cleanup pass moved the old briefing, queue, and Gate C review scripts into the archive, and the archived downstream orchestrator now points at its archived review steps instead of the former root paths
- the extraction-workflow cleanup pass moved the old pilot, extraction, review, and promotion scripts into the archive, patched the archived edge-reset runner to call those archived scripts, and fixed the moved scripts to resolve the real repo root from `scripts/archive/...`
- historical docs still reference `materialize_mixed_family_pilot.py`, which is acceptable for `S16` because the archive preserves the file while removing it from the active script surface
- historical docs still reference `research:materialize-findings`, which is acceptable for `S16` because the archive preserves the implementation while the active package surface is reduced
- the stage is complete: the active `package.json` command surface is now canonical, the major superseded workflow clusters have been moved into `scripts/archive/`, and the remaining dirty or untracked files are local worktree state rather than active canonical pipeline surface
- the canonical `S00–S16` execution path is now complete end to end

## Enhancement Stages (S17–S24)

### `S17` Transition-State Anchor and Probe Config

Build:

- add 5 transition-state anchor families to `configs/anchors.yaml`:
  - `queue_value_passive_quoting`
  - `refill_lag_resiliency`
  - `auction_handoff`
  - `maker_retreat_inventory_stress`
  - `parity_propagation_delayed_repair`
- add transition-state agitator probes to `configs/probes.yaml`
- re-materialize probes against the existing embedding space

Accept when:

- transition-state anchors are queryable in the canonical store
- probe hits exist for transition-state patterns

Current status:

- the plan has been reopened beyond `S16` because the completed pipeline still under-surfaces the actual microstructure findings and near-misses
- the first `S17` commit added the exact transition-state anchor families to `configs/anchors.yaml`:
  - `queue_value_passive_quoting`
  - `refill_lag_resiliency`
  - `auction_handoff`
  - `maker_retreat_inventory_stress`
  - `parity_propagation_delayed_repair`
- the first `S17` commit also added matching transition-state composition probes to `configs/probes.yaml`
- fixture coverage now guards those checked-in config ids directly in `tests/test_materialize_probes.py`
- `scripts/materialize_probes.py` now preloads vectors and centroids once per embedding space instead of once per pattern, which removed the live-run stall on the canonical corpus
- the rerun `npm run store:materialize-probes -- --run-id probe-materialization-20260328-transition-state` completed successfully with `11` anchors, `15` patterns, and `375` total probe hits
- each new transition-state pattern now has live canonical hits in `probe_hits` for that run:
  - `near_transition_queue_refill`: `25`
  - `near_transition_auction_refill`: `25`
  - `near_transition_auction_queue`: `25`
  - `near_transition_maker_queue`: `25`
  - `near_transition_parity_repair`: `25`
- the stage is complete: transition-state anchors are queryable in the canonical store and live probe hits exist for the new transition-state patterns

### `S18` Transition-State Score Materializer

Build:

- canonical `transition_state_scores` table and staged materializer
- sparse + embedding-proximity scoring for the 5 transition-state families
- papers near these anchors in embedding space get boosted

Accept when:

- transition-state scores exist in canonical outputs
- scores are continuous, not binary

Current status:

- the `S18` commit adds the canonical score surface in `scripts/materialize_transition_state_scores.py`
- the score stage is paper-level and discovery-scoped, using transition-state anchor keyword evidence plus normalized probe-hit proximity from the completed `S17` run
- the canonical table surface is `transition_state_scores`, with family-level subscores and auditable `feature_json` provenance
- fixture coverage in `tests/test_materialize_transition_state_scores.py` proves that the stage writes continuous scores instead of binary flags
- the live rerun `npm run store:materialize-transition-state-scores -- --run-id transition-state-score-materialization-20260328` completed successfully with:
  - `scored_papers`: `17,323`
  - `positive_score_papers`: `805`
  - `top_score`: `0.5390968411673467`
- family-level positive paper counts are now live in canonical outputs:
  - `queue_value_score`: `281`
  - `refill_resiliency_score`: `384`
  - `auction_handoff_score`: `66`
  - `maker_retreat_score`: `102`
  - `parity_repair_score`: `361`
- the stage is complete: transition-state scores now exist in canonical outputs and remain continuous rather than binary

### `S19` Transition-State Operator

Build:

- dedicated retrieval operator that surfaces papers and regions about: shock recovery, local depletion, delayed repair, handoff between matching regimes, queue reformation, asynchronous refill
- canonical `transition_state_candidates` table with run-scoped provenance

Accept when:

- transition-state candidates exist in the main store
- candidates come from embedding proximity to transition-state anchors, not just keyword matching

Current status:

- the `S19` commit adds the canonical operator in `scripts/materialize_transition_state_candidates.py`
- the operator is pattern-scoped and paper-level, consuming only the completed `S17` probe hits plus the completed `S18` transition-state score surface
- the canonical table surface is `transition_state_candidates`, with representative probe views and rationale payloads for later review-packet and publication stages
- fixture coverage in `tests/test_materialize_transition_state_candidates.py` proves the operator ranks probe-supported papers rather than falling back to a keyword-only path
- the live rerun `npm run store:materialize-transition-state-candidates -- --run-id transition-state-candidate-materialization-20260328` completed successfully with:
  - `transition_pattern_count`: `5`
  - `transition_candidate_count`: `95`
  - `patterns_with_candidates`: `5`
  - `top_score`: `0.702172`
- live pattern coverage is now canonical:
  - `near_transition_queue_refill`: `20`
  - `near_transition_auction_refill`: `20`
  - `near_transition_auction_queue`: `20`
  - `near_transition_maker_queue`: `15`
  - `near_transition_parity_repair`: `20`
- the stage is complete: transition-state candidates now exist in the main store and they are derived from live probe proximity plus the canonical `S18` paper-level prior rather than keyword matching alone

### `S20` Stranded Q-Fin Resurfacing Operator

Build:

- dedicated operator running only over the stranded-alpha slice (q-fin 2015–2023)
- ranking by: stranding score, result specificity, low survey/empirical-only penalty, low realized leakage, closeness to current venue mechanics
- canonical `stranded_resurfacing_candidates` table

Accept when:

- resurfacing candidates are ranked and queryable
- the operator is distinct from the general stranding scorer

Current status:

- the `S20` commit adds the canonical operator in `scripts/materialize_stranded_resurfacing_candidates.py`
- the operator runs only over the time-firewalled stranded-alpha q-fin slice from `corpus_memberships`
- ranking combines the existing stranding prior with result specificity, penalty relief, realized-market leakage, and a simple current-venue closeness signal from `transition_state_scores` plus recency
- fixture coverage in `tests/test_materialize_stranded_resurfacing_candidates.py` proves that only the stranded q-fin slice is ranked and that realized-market rows are demoted rather than silently mixed with the generic scorer
- the live rerun `npm run store:materialize-stranded-resurfacing-candidates -- --run-id stranded-resurfacing-materialization-20260328` completed successfully with:
  - `candidate_count`: `50`
  - `top_score`: `0.416187`
  - `top_ranked_paper_id`: `2204.08581`
- the top five live resurfacing rows are now queryable in the canonical store:
  - `2204.08581`
  - `2106.00581`
  - `1712.10105`
  - `1903.06928`
  - `2005.04297`
- the stage is complete: resurfacing candidates are ranked and queryable, and the operator is now distinct from the generic stranding scorer because it only ranks the stranded-alpha q-fin slice with operator-specific leakage and venue-closeness terms

### `S21` Findings and Throwaways Materializer

Build:

- mandatory per-run review-summary report
- top accepted by operator
- top rejected by operator with rejection reasons
- top near-misses by operator
- top stranded q-fin rows that failed ledger conversion with reasons

Accept when:

- `findings_and_throwaways.*` artifacts exist (markdown + JSONL + metrics)
- the report covers all operator families

Current status:

- the `S21` commit adds the canonical report stage in `scripts/materialize_findings_and_throwaways.py`
- the report stays synthesis-only over canonical surfaces: selective interpretations, ingestion rejection JSONL, operator candidate pools, and stranded resurfacing rows that failed ledger conversion
- fixture coverage in `tests/test_materialize_findings_and_throwaways.py` proves the report includes accepted findings, ingestion rejections, operator near-misses, and stranded q-fin failures in one output set
- the live rerun `npm run store:materialize-findings-and-throwaways -- --run-id findings-and-throwaways-20260328` completed successfully with:
  - `accepted_count`: `2`
  - `rejected_count`: `1`
  - `near_miss_count`: `15`
  - `stranded_qfin_failure_count`: `3`
- the report now covers all operator families through dedicated sections for:
  - `bridge`
  - `composition`
  - `contrast`
  - `negative_space`
  - `transition_state`
  - `stranded_resurfacing`
- the stage is complete: `findings_and_throwaways.md`, `.jsonl`, and `_metrics.json` exist and the live report now exposes survivors, rejects, near-misses, and failed ledger conversions in one canonical artifact

### `S22` Transition-State Microstructure Ledger

Build:

- dedicated publication surface for transition-state microstructure findings
- specific pairings: queue x refill, auction x refill, auction x queue, maker-retreat x queue, parity-propagation x refill
- ledger format matching the stranded result ledger shape

Accept when:

- `transition_state_ledger.*` artifacts exist
- entries are tied to transition-state candidates and interpretations

Current status:

- the `S22` commit adds the canonical publication stage in `scripts/materialize_transition_state_ledger.py`
- the ledger binds each transition-state publication row to both a live `transition_state_candidates` representative paper and a positive accepted interpretation for the same pairing key from the current shortlist
- fixture coverage in `tests/test_materialize_transition_state_ledger.py` proves that only pairings with both candidate support and positive interpretations are published
- the live rerun `npm run store:materialize-transition-state-ledger -- --run-id transition-state-ledger-20260328` completed successfully with:
  - `entry_count`: `2`
  - `top_ranked_pattern_id`: `near_transition_queue_refill`
  - `counts_by_priority_tier`: `p1=2`, `p2=0`, `p3=0`
- the two live transition-state ledger rows are now:
  - `near_transition_queue_refill` -> `composition:queue_value_passive_quoting__refill_lag_local_shock` via representative paper `2101.03086`
  - `near_transition_auction_refill` -> `bridge:auction_parimutuel_design__refill_lag_local_shock` via representative paper `1011.6402`
- the stage is complete: `transition_state_ledger.md`, `.jsonl`, and `_metrics.json` exist and each published row is tied to both transition-state candidates and canonical interpretations

### `S23` Enhanced Interpretation Batch

Build:

- expand second-pass interpretation to cover:
  - top 10–20 cross-domain bridge packets
  - top 10–20 stranded q-fin packets
  - top 10–20 transition-state packets
- use the same strict JSON contract from S12

Accept when:

- interpretation batch covers all three operator families
- accepted/rejected counts are meaningfully larger than the S12 pilot

Current status:

- the `S23` foundation commit adds the canonical batch-prep stage in `scripts/materialize_enhanced_interpretation_batch.py`
- the batch now expands interpretation preparation across three operator families while reusing the exact S12 prompt and schema contract:
  - top bridge packets from `review_packets`
  - top stranded resurfacing rows from `stranded_resurfacing_candidates`
  - top transition-state rows from `transition_state_candidates`
- fixture coverage in `tests/test_materialize_enhanced_interpretation_batch.py` proves that the output covers all three operator families and preserves prompt/schema references in every row
- the live rerun `npm run store:materialize-enhanced-interpretation-batch -- --run-id enhanced-interpretation-batch-20260328` completed successfully with:
  - `prepared_count`: `33`
  - `bridge`: `6`
  - `stranded_qfin`: `12`
  - `transition_state`: `15`
- the stage is still in progress: the expanded batch now covers all three operator families, but the downstream accepted/rejected-count acceptance bar still depends on a larger real ingestion run

### `S24` Re-Materialize All Publication Surfaces

Build:

- re-run all four publication surfaces from the expanded interpretation:
  1. `unrealized_ideas_index.*`
  2. `stranded_result_ledger.*`
  3. `transition_state_ledger.*`
  4. `findings_and_throwaways.*`

Accept when:

- all four artifacts are non-empty and backed by the expanded interpretation run
- the findings report covers survivors, rejections, and near-misses

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

- Commit scope: `s23-enhanced-interpretation-batch-foundation`
- Why this commit exists: expand the interpretation preparation surface beyond the shortlist pilot so the next ingestion pass can cover bridge, stranded q-fin, and transition-state families under one strict contract
- Stages touched: `S23`
- Code paths touched: `docs/briefings/2026-03-25-structural-analogy-engine-plan.md`, `scripts/materialize_enhanced_interpretation_batch.py`, `tests/test_materialize_enhanced_interpretation_batch.py`, `package.json`
- Commands run: `npm run codecontext:scope -- docs/briefings/2026-03-25-structural-analogy-engine-plan.md`, `npm run codecontext:scope -- scripts/materialize_selective_interpretation_batch.py`, `npm run codecontext:scope -- scripts/materialize_transition_state_ledger.py`, `sqlite3 data/structural-analogy/paperview.sqlite3 "select packet_kind, count(*) from review_packets where run_id='review-packet-materialization-20260328' group by packet_kind order by packet_kind;"`, `sqlite3 data/structural-analogy/paperview.sqlite3 "select count(*) from stranded_resurfacing_candidates where run_id='stranded-resurfacing-materialization-20260328';"`, `sqlite3 data/structural-analogy/paperview.sqlite3 "select count(*) from transition_state_candidates where run_id='transition-state-candidate-materialization-20260328' and transition_state_rank <= 20;"`, `sqlite3 data/structural-analogy/paperview.sqlite3 "select count(*) from transition_state_ledger where run_id='transition-state-ledger-20260328';"`, `npm run codecontext:py -- scripts/materialize_enhanced_interpretation_batch.py`, `npm run codecontext:py -- tests/test_materialize_enhanced_interpretation_batch.py`, `python3 -m unittest -v tests.test_materialize_enhanced_interpretation_batch`, `npm run store:materialize-enhanced-interpretation-batch -- --run-id enhanced-interpretation-batch-20260328`, `python3 - <<'PY' ... enhanced batch metrics and family counts ... PY`, `npm run codecontext:diff -- scripts/materialize_enhanced_interpretation_batch.py`, `npm run codecontext:diff -- tests/test_materialize_enhanced_interpretation_batch.py`, `npm run docs:lint`
- Tests run: `python3 -m unittest -v tests.test_materialize_enhanced_interpretation_batch`, `npm run docs:lint`
- Artifacts produced: `data/structural-analogy/runs/enhanced-interpretation-batch-20260328/enhanced_interpretation_batch.jsonl`, `data/structural-analogy/runs/enhanced-interpretation-batch-20260328/enhanced_interpretation_batch_metrics.json`
- Acceptance result: `partial; the expanded batch now covers all three operator families with 33 prepared items, but the stage remains in progress until a larger ingestion run produces materially larger accepted/rejected counts than the S12 pilot`
- Open risks after commit: `this foundation expands batch coverage, but S23 remains incomplete until a larger real interpretation ingestion run produces materially larger accepted/rejected counts than the S12 pilot`
- Next intended commit: `S23 expanded interpretation ingestion`
- Signoff status: `ready`
- Last updated: `2026-03-28`
