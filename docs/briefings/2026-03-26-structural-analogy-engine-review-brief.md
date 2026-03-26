---
doc_type: briefing
owner: devrel
review_policy: periodic-7
reviewed: 2026-03-26
status: active
summary: Review brief describing the exact research plan, technical stack, execution phases, and expected end-state outputs for the structural analogy engine.
tags:
  - docs
  - briefing
  - proposal
  - research
  - strategy-discovery
written: 2026-03-26
---

# Structural Analogy Engine Review Brief

## Summary

We are building a local-first research system that turns the literature corpus into a search surface for transferable market mechanisms, not a generic paper-clustering tool. The purpose is to find strategy primitives from adjacent literatures that could plausibly transfer into novel event and prediction markets before they are fully crowded.

The system’s end state is not “a pile of embeddings.” It is a reviewed pipeline that extracts mechanism records from papers, normalizes them into a controlled ontology, generates structural fingerprints, retrieves non-obvious analogs across domains, scores them for `tradecore` fit and novelty, and outputs a ranked review queue of candidate strategy mechanisms. This document is the exact plan, stack, and expected deliverables so the project can be reviewed before we push deeper.

The repo now also has a first persisted scoring surface for `exposure_score`,
`underexploited_score`, and a bootstrap `worth_followup_score`, plus a
persisted queryless mining queue, analyst-adjudicated reranks with learned mode
weights, a hard-gated ranked family queue, and generated strategy briefs. The
repo now also has a persisted Gate C review path over those briefs, and the
live SQLite store has been reconciled onto the mechanism-first schema with
legacy valid extractions promoted into `mechanism_instances`. The next critical
path is therefore evaluating the first live downstream brief surface, which now
exists under the `live-legacy-bootstrap` run prefix, and deciding whether that
legacy slice is worth analyst review or whether newer mixed-family extraction
output is required before deeper evaluation.

---

## What We Are Building

The structural analogy engine is a research pipeline with five functional layers:

1. Corpus layer
   - Harvest and track the relevant literature corpus locally.
   - Stamp imported records with canonical `literature_family` and holdout/tuning split metadata.
   - Maintain metadata, PDFs, completeness state, and failure/retry accounting.

2. Extraction layer
   - Convert paper metadata and abstracts, then later full text, into structured mechanism records.
   - Require insight type, fragility fields, and anti-transfer rationale on surfaced mechanisms.
   - Reject outputs that are schema-valid but semantically wrong.

3. Normalization layer
   - Map raw extracted claims into a fixed vocabulary of market domains, edge sources, execution styles, failure modes, and portability judgments.
   - Generate structural fingerprints that make cross-domain analogy search possible.

4. Retrieval and scoring layer
   - Embed normalized summaries and fingerprints.
   - Build similarity, bridge-paper, and far-analog retrieval surfaces.
   - Benchmark retrieval against adjudicated lexical/structural bucket pairs before calling it useful.
   - Score candidates by novelty, plausibility, evidence, and `tradecore` fit.

5. Strategy output layer
   - Produce a ranked queue of candidate mechanisms.
   - Package the best ones into reviewable strategy briefs that can inform future executor design.

The system is explicitly designed to answer:

1. Which literature mechanisms are structurally close to the kinds of strategies `tradecore` can already express?
2. Which mechanisms live in non-obvious domains rather than standard q-fin or prediction-market literature?
3. Which of those mechanisms have a plausible transfer path into novel markets and remain underexploited?

---

## What This Is Not

This is not:

- a generic embedding map of academic papers
- a topic-modeling exercise
- a citation-network browser
- an automated alpha generator
- a direct backtesting system

Embeddings are only one component. The real product is a mechanism-discovery and transfer-review system.

---

## Research Thesis

The working thesis is:

1. Many useful strategy primitives are described in literatures that prediction-market participants do not usually read.
2. The right unit of transfer is not paper topic but structural mechanism.
3. If we can represent papers as normalized mechanism records plus structural fingerprints, we can retrieve analogs that are invisible to surface-level keyword search.
4. The most valuable outputs are likely to come from “diamonds in the rough”:
   - structurally relevant
   - semantically non-obvious
   - operationally compatible with `tradecore`
   - not already overexposed in standard prediction-market discourse

Examples of adjacent literatures we expect to matter:

- market microstructure
- inventory-based market making
- auction theory
- betting and sportsbook pricing
- pari-mutuel and tournament pricing
- DeFi / AMM design
- electricity, freight, carbon, and other fragmented special markets
- options relative-value and term-structure literature
- constrained-arbitrage and forced-flow papers

The repo now carries a checked-in adjacent-family seed registry, per-family
jargon lexicons, and a reserved holdout policy so cross-domain expansion is
explicit instead of ad hoc.

The repo now also carries a checked-in discovery benchmark definition with
adjudicated near/far bucket labels and explicit retrieval acceptance thresholds.

---

## Exact Research Plan

## Phase 0: Corpus Readiness

Purpose:
- Make the corpus operationally trustworthy before deeper processing.

Work:
- harvest full q-fin metadata
- run local PDF pull
- track completeness, failures, and retryable misses
- materialize readiness and inventory artifacts

Exit condition:
- metadata is complete
- corpus state is reviewable and reproducible
- downloader behavior is classified rather than opaque

Current state:
- largely built
- still operationally open until the full pull completes

## Phase 1: Schema and Local Store

Purpose:
- freeze the initial data contract before large-scale extraction.

Work:
- define extraction schema
- define structural fingerprint schema
- define controlled vocabularies
- initialize canonical local store
- populate `papers` from harvested metadata

Exit condition:
- checked-in schema files are the source of truth
- SQLite store exists and is queryable

Current state:
- largely built

## Phase 2: Text Preparation

Purpose:
- prepare the corpus for section-aware extraction beyond abstracts.

Work:
- add PDF text extraction and sectioning
- capture parse failures and text quality issues
- align parsed sections with local store

Exit condition:
- papers can be processed at abstract-first and full-text levels

Current state:
- in progress
- a repo-native section parser now stores parsed PDF text in `paper_sections`
- unreadable or missing PDFs now land in `parse_failures` with
  `failure_stage = section_parse`
- canonical evidence spans can now be upgraded from abstract fallback to
  section-backed snippets when parsed sections provide a stronger match

## Phase 3: Local Extraction Pipeline

Purpose:
- produce reliable structured mechanism records from paper inputs.

Work:
- create extraction runs from the pilot batch
- run local model inference
- validate against schema
- apply semantic quality review
- require insight type plus falsifiable blocker fields on promising outputs
- gate ingestion on blocking failures
- tune prompts until widened slices stay clean enough to ingest

Exit condition:
- abstract extraction is batch-stable on meaningful pilot slices
- validated outputs are captured in a transitional `paper_extractions` buffer
- accepted mechanism records are promoted into canonical `mechanism_instances`
  with evidence spans

Current state:
- in progress
- benchmark slices and widened slices are already running through a real gate
- one 25-paper widened slice has already been ingested
- the active ingest path now accepts `0..N` mechanism instances per paper and
  backfills older valid staging rows into the canonical mechanism store
- a checked-in mixed-family pilot definition now exists, and the quality gate
  reports Gate A rollout metrics on wrapper-style `mechanism_instances` outputs

## Phase 4: Normalization and Fingerprinting

Purpose:
- transform extracted rows into comparable structural objects.

Work:
- normalize free-form outputs to controlled enums
- generate structural fingerprints
- persist normalized artifacts in the local store
- detect and review ambiguous or unsupported mappings

Exit condition:
- every accepted extraction has a normalized record and fingerprint

Current state:
- in progress
- active mechanism instances can now be normalized into controlled structural
  facets defined by `schemas/fingerprint.schema.json`
- normalization writes deterministic `fingerprint_text` plus full
  `mechanism_fingerprints` records in SQLite
- lossy or weak-evidence mappings are now queued explicitly in
  `normalization_reviews`

## Phase 5: Embeddings, Graph, and Retrieval

Purpose:
- create the search surfaces needed for structural analogy discovery.

Work:
- embed mechanism summaries and fingerprints
- build similarity edges
- support:
  - nearest-fit retrieval
  - far-analog retrieval
  - bridge-paper retrieval
- store embeddings and graph links locally

Exit condition:
- the system can retrieve non-obvious but structurally relevant papers

Current state:
- in progress
- the repo now persists `mechanism_retrieval_documents`,
  `mechanism_dense_embeddings`, `mechanism_graph_edges`, and
  `retrieval_benchmark_results`
- separate structured, sparse, dense, graph, citation-baseline, and hybrid
  views can now be benchmarked against the checked-in discovery benchmark
- the first shipped dense baseline is deterministic so the retrieval contract
  is runnable before the canonical local embedder is wired in
- queryless candidate discovery now persists ranked `queryless_candidate_hits`
  across structural-near / lexical-far, tradecore-near / jargon-far, bridge,
  holdout, contradiction, and rare-fingerprint mining modes

## Phase 6: Scoring and Review Queue

Purpose:
- rank candidates in a way that is useful for strategy discovery.

Work:
- score by:
  - evidence strength
  - novelty
  - portability
  - `tradecore` fit
  - likely crowding
  - implementation burden
- generate a ranked review queue
- package “why this surfaced” explanations

Exit condition:
- we can inspect a candidate queue instead of raw retrieval output

Current state:
- in progress
- the repo now persists a first ranked candidate queue in
  `queryless_candidate_hits`
- each hit carries explicit structural, lexical-distance, transfer, and blocker
  sub-scores plus evidence/rationale payloads
- analyst adjudication now persists `analyst_labels`,
  `analyst_weight_updates`, and `adjudicated_queryless_hits`
- hard-gated ranking now persists `candidate_families`,
  `candidate_family_members`, `transfer_hypotheses`, and
  `candidate_family_rankings`
- the remaining gap is brief generation, not queue materialization, weight
  learning, or family assembly

## Phase 7: Strategy Output and Handoff

Purpose:
- turn promising mechanism hits into human-reviewable strategy research artifacts.

Work:
- produce candidate mechanism briefs
- map each candidate to likely `tradecore` executor shapes
- identify open questions, required data, and why the mechanism may still be underexploited

Exit condition:
- the system produces usable candidate packets, not just metadata and scores

Current state:
- in progress
- `generate_strategy_briefs.py` now writes persisted `strategy_briefs` plus
  run-folder markdown/json brief packets from the ranked family queue
- `prepare_gate_c_review.py` now exports those briefs into analyst-ready Gate C
  review bundles with editable JSONL templates and packet indexes
- `review_gate_c.py` now writes persisted `gate_c_brief_reviews` and
  `gate_c_review_summaries` over those brief packets
- the live DB now also contains reconciled canonical `mechanism_instances` from
  legacy valid extraction rows, and `materialize_live_downstream_run.py` now
  materializes the first live downstream queue from that surface
- the remaining question is whether that live legacy brief queue is worth
  analyst time and whether newer mixed-family extraction output is needed
- not started

---

## Technologies and Stack

The intended stack is deliberately local-first and lightweight.

## Data and Storage

- `SQLite`
  - canonical local write store for v1
  - tables for papers, sections, extractions, fingerprints, exposure scores,
    retrieval documents, mechanism embeddings, graph edges, benchmark results,
    and candidates
- `JSONL`
  - run artifacts
  - request/response files
  - quality reports
- local filesystem
  - PDFs
  - reports
  - run directories

Why:
- simple, inspectable, and easy to move around
- low operational overhead
- sufficient for pilot-scale local research work

## Pipeline Runtime

- `Python 3`
  - standard-library-first approach where practical
- local scripts under `scripts/`
  - ingestion
  - corpus ops
  - extraction run prep
  - quality review
  - gate-and-ingest

Why:
- transparent and easy to audit
- easy to review and modify in-repo

## Local Model Runtime

- `mlx-lm`
- current working backend:
  - `mlx-community/Qwen2.5-3B-Instruct-4bit`

Why:
- runs locally on Apple Silicon
- no external API dependency required for pilot extraction work
- already operational in this repo

Important limitation:
- prompt tuning is required because small local models are prone to enum drift and semantic overreach

## Governance and Repo Workflows

- `codecontext`
  - for repo workflow and context checks
- docs governance / remark setup
  - for docs policy and linting
- local prompt files under `prompts/`
  - versioned prompt iterations

## Planned Near-Term Additions

Not all of these are built yet, but they are part of the planned stack:

- PDF text extraction / sectioning
  - likely via a local parser path
- local embedding model
  - MLX is the primary intended Apple Silicon path, with `sentence-transformers` as the fallback baseline
- retrieval / graph tooling
  - likely Python-native over local stored embeddings, with `sqlite-vec` now available for SQLite-native vector search

## Local Toolchain Status

- `sqlite-vec` v0.1.6 is already installed locally, including the Python binding
- MLX is already the local extraction backend and is the intended primary local embedding runtime on this Mac Studio once the current install completes
- `sentence-transformers` is the preferred local fallback and baseline embedding path

This means the remaining open work is increasingly about retrieval/ranking design and evaluation, not toolchain acquisition.

## Embedding Guidance

- use one primary production embedding space at a time
- current recommended primary indexer is `Qwen/Qwen3-Embedding-0.6B`
  at `512` dimensions
- keep `BAAI/bge-m3` as a separate exploratory / hybrid discovery index, not
  as mixed vectors inside the main ANN table
- keep `Alibaba-NLP/gte-Qwen2-7B-instruct` for reranking or top-k adjudication,
  not first-pass corpus embedding

Why:

- verified from model cards: `Qwen/Qwen3-Embedding-0.6B` supports `32k`
  context and user-defined output dimensions from `32` to `1024`
- verified from model cards: `BAAI/bge-m3` is a `1024`-dimensional model with
  dense, sparse, and multi-vector retrieval support over up to `8192` tokens
- verified from model cards: `Alibaba-NLP/gte-Qwen2-7B-instruct` uses a
  `3584`-dimensional embedding space and `32k` max input tokens
- inference from those contracts: vectors from different models or dimensions
  should not be treated as one comparable retrieval space

---

## Methodological Guardrails

These are core to the project, not optional polish.

1. Local-first by default
   - no dependence on remote APIs for the core pipeline

2. Schema before scale
   - large runs only happen once the contract is explicit

3. Gate before ingest
   - schema-valid but semantically bad output does not get persisted as accepted data

4. Conservative collapse over speculative labeling
   - if the model is unsure, it should use `other`, not invent a more specific mechanism

5. Targeted blocker retirement
   - new failure classes are fixed locally in smoke tests before spending another wide rerun

6. Retrieval must be structurally meaningful
   - the system is judged by the quality of surfaced mechanisms, not by pretty clusters

7. End-state outputs must be strategy-relevant
   - every downstream stage should move toward candidate mechanism briefs, not academic ornamentation

---

## Expected Outputs When This Is Done

The completed system should produce six concrete outputs.

## 1. A Local Corpus and Processing Store

Artifacts:
- complete or near-complete q-fin corpus state
- local metadata store
- PDF inventory
- parse / failure accounting

Why it matters:
- the rest of the pipeline depends on a stable substrate

## 2. A Clean Mechanism-Instance Layer

Artifacts:
- canonical `mechanism_instances` rows for accepted mechanisms
- transitional `paper_extractions` rows only while the extraction refactor is in flight
- validated, review-gated structured outputs

Why it matters:
- this is the first machine-readable mechanism layer, and it must not collapse
  back to a paper-first contract

## 3. A Normalized Structural Fingerprint Layer

Artifacts:
- normalized ontology fields
- fingerprint records for each accepted mechanism instance

Why it matters:
- this is the layer that enables analogy search rather than topic search

## 4. A Retrieval Surface

Artifacts:
- similarity search
- far-analog search
- bridge-paper search
- local embeddings and edge graph

Why it matters:
- this is how we surface non-obvious candidate mechanisms

## 5. A Ranked Candidate Queue

Artifacts:
- scored candidate list
- reasons each item surfaced
- fit, novelty, evidence, and burden fields

Why it matters:
- this is the main analyst interface

## 6. Final Strategy Candidate Briefs

Artifacts:
- top candidate packets describing:
  - source mechanism
  - original literature
  - transfer rationale
  - likely `tradecore` fit
  - why it may still be underexploited
  - what data or implementation work would be needed next

Why it matters:
- this is the real project output

---

## Definition of Success

The project is successful if, at the end:

1. We can point to a small set of candidate mechanisms that are non-obvious, structurally coherent, and plausibly transferable.
2. Those candidates are backed by a reproducible local pipeline, not ad hoc analyst intuition.
3. The system is good enough to be rerun on more corpus slices and adjacent literatures.
4. Reviewers can inspect the logic from corpus to extraction to ranking without black-box gaps.

The project is not successful if, at the end, we only have:

- embeddings
- clusters
- dashboards
- extracted JSON

without a credible candidate queue and transfer rationale.

---

## Main Risks

## 1. Extraction Quality Risk

The local model may remain too brittle for stable larger-batch extraction without substantial prompt discipline.

Mitigation:
- strict schema-aware gate
- targeted blocker retirement
- conservative enum usage

## 2. Ontology Risk

The ontology may be too narrow for adjacent domains or too broad to stay meaningful.

Mitigation:
- harden enums against pilot outputs
- review normalization failures explicitly

## 3. Retrieval Quality Risk

The retrieval layer may recover obvious neighbors instead of real far analogs.

Mitigation:
- store fingerprints, not just embeddings
- evaluate far-analog and bridge-paper modes explicitly

## 4. Output Quality Risk

The system may produce “interesting papers” instead of actionable candidate mechanisms.

Mitigation:
- define strategy-output artifacts early
- keep scoring tied to portability and `tradecore` fit

## 5. Scope Creep Risk

The system can become a general literature platform rather than a strategy-discovery engine.

Mitigation:
- evaluate each phase against the end-state candidate packet output

---

## Review Questions

These are the questions worth reviewing now, before we push much farther:

1. Is the goal statement correct?
   - mechanism discovery for novel markets, not generic literature intelligence

2. Is the local-first stack the right tradeoff?
   - especially the use of SQLite plus MLX for the pilot phase

3. Is the output definition correct?
   - ranked candidate mechanisms and strategy briefs, not just retrieval

4. Is the current phase order correct?
   - the sequencing through extraction stability, full-text prep, and normalization is now largely done; the main remaining question is whether embeddings and retrieval should proceed exactly as planned

5. Is the ontology direction right?
   - enough structure to support analogy search without becoming rigid nonsense

6. Should any adjacent literature families be added now rather than later?

7. Should there be a tighter go/no-go criterion before we invest in full-text processing?

---

## Recommended Approval Standard

Before we go significantly further, I would want explicit agreement on:

- the goal
- the end-state outputs
- the local-first stack
- the phase order
- the definition of success

If those are approved, the remaining work becomes mostly execution and tuning rather than redefinition.

---

## Additional Context (For AIs and Deep Dives)

## Canonical Inputs

- living tracker:
  - [Structural Analogy Engine Plan](./2026-03-25-structural-analogy-engine-plan.md)
- harvested corpus:
  - `data/arxiv-qfin/`
- local store:
  - `data/structural-analogy/paperview.sqlite3`

## Current Implemented Surfaces

- corpus launch / status / inventory / readiness tooling
- checked-in extraction and fingerprint schemas
- SQLite local store bootstrap and metadata loader
- deterministic pilot batch generation
- prompt-ready extraction run generation
- MLX local extraction runner
- schema-aware quality reviewer
- gate-and-ingest workflow
- section-aware PDF parsing and evidence upgrades
- mechanism-level normalization and fingerprint persistence
- persisted retrieval documents, mechanism embeddings, graph edges, benchmark
  results, queryless candidate hits, analyst weight updates, and adjudicated
  queue rows
- persisted candidate families, family members, transfer hypotheses, and ranked
  family queue rows
- persisted strategy briefs and reviewable brief packets with minimal test plans
- analyst-ready Gate C review bundles with editable JSONL templates
- persisted Gate C brief reviews and run-level pass/fail summaries
- repo-native live-store reconciliation/backfill from valid legacy
  `paper_extractions` into canonical `mechanism_instances`
- repo-native live downstream materialization from reconciled mechanisms through
  provisional briefs and Gate C prep

## Current Non-Implemented Surfaces

- no major implementation surface remains on the canonical path; the remaining
  work is success-criterion review and any targeted quality iteration that review
  demands

## Key Definitions

- `mechanism`
  - the core trade or market-structure logic described by a paper

- `structural fingerprint`
  - a normalized representation of payoff topology, frictions, market structure, execution shape, and failure modes

- `far analog`
  - a paper with low surface similarity but high structural similarity

- `bridge paper`
  - a paper that sits between two otherwise separate mechanism clusters

- `tradecore fit`
  - how plausibly a surfaced mechanism maps to the execution capabilities we are already building

- `diamond in the rough`
  - a mechanism that is structurally relevant, semantically non-obvious, and plausibly underexploited

## Planned Final Artifact Shape

A finished candidate packet should look like:

- `candidate_name`
- `source_papers`
- `mechanism_summary`
- `original_domains`
- `transfer_target`
- `why_it_transfers`
- `why_it_may_be_underexploited`
- `tradecore_fit`
- `required_new_primitives`
- `data_requirements`
- `risks`
- `recommended_next_validation_step`

## Review-Oriented Bottom Line

The right question for this project is not “can we extract fields from papers?” The right question is “can we build a defensible local system that surfaces overlooked, structurally transferable strategy mechanisms and packages them in a form useful for real strategy design?” This proposal is meant to let that question be reviewed directly.
