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

---

## What We Are Building

The structural analogy engine is a research pipeline with five functional layers:

1. Corpus layer
   - Harvest and track the relevant literature corpus locally.
   - Maintain metadata, PDFs, completeness state, and failure/retry accounting.

2. Extraction layer
   - Convert paper metadata and abstracts, then later full text, into structured mechanism records.
   - Reject outputs that are schema-valid but semantically wrong.

3. Normalization layer
   - Map raw extracted claims into a fixed vocabulary of market domains, edge sources, execution styles, failure modes, and portability judgments.
   - Generate structural fingerprints that make cross-domain analogy search possible.

4. Retrieval and scoring layer
   - Embed normalized summaries and fingerprints.
   - Build similarity, bridge-paper, and far-analog retrieval surfaces.
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
- not started

## Phase 3: Local Extraction Pipeline

Purpose:
- produce reliable structured mechanism records from paper inputs.

Work:
- create extraction runs from the pilot batch
- run local model inference
- validate against schema
- apply semantic quality review
- gate ingestion on blocking failures
- tune prompts until widened slices stay clean enough to ingest

Exit condition:
- abstract extraction is batch-stable on meaningful pilot slices
- validated outputs are ingested into a transitional `paper_extractions` buffer
- accepted mechanism records are promoted into canonical `mechanism_instances`

Current state:
- in progress
- benchmark slices and widened slices are already running through a real gate
- one 25-paper widened slice has already been ingested

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
- not started

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
- not started

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
- not started

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
- not started

---

## Technologies and Stack

The intended stack is deliberately local-first and lightweight.

## Data and Storage

- `SQLite`
  - canonical local write store for v1
  - tables for papers, sections, extractions, fingerprints, embeddings, edges, and candidates
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
  - for summary and fingerprint embeddings
- retrieval / graph tooling
  - likely Python-native over local stored embeddings

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
- fingerprint records for each accepted paper

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
   - finish abstract extraction stability before full-text parsing, normalization, and embeddings

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

## Current Non-Implemented Surfaces

- full-text PDF parsing and sectioning
- normalization pass into fingerprints
- embeddings layer
- graph layer
- candidate scoring
- final strategy-brief generation

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
