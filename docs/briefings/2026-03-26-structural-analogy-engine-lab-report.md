---
doc_type: briefing
owner: devrel
review_policy: historical
reviewed: 2026-04-08
status: historical
summary: Historical lab-facing report for the structural analogy engine before mdream became the repo's primary user-facing surface.
tags:
  - docs
  - briefing
  - research
  - report
  - strategy-discovery
written: 2026-03-26
---

# Structural Analogy Engine Lab Report

## Summary

We are building a local-first research system that reads the `q_fin` literature as a source of reusable market mechanisms rather than as a list of isolated papers. The immediate goal is not to produce a paper embedding map or an automated alpha generator. The goal is to convert a very large `q_fin` corpus into a structured search surface that can surface non-obvious, testable strategy ideas, missing executor primitives, regime filters, and failure modes.

As of `2026-03-26`, the local SQLite store contains `24,203` `q_fin` papers, and a full `q_fin` abstract-extraction run is now in flight under `abstract_extraction-v22-qfin-full-study`. The working bet is that meaningful results will come not from raw semantic similarity, but from extracting mechanism-level structure, normalizing it, and then ranking candidate hypotheses by evidence, portability, novelty, and explicit failure conditions.

The current full `q_fin` run is a baseline corpus-scale study, not the intended boundary of the research engine. The engine is meant to generalize to adjacent literatures wherever structurally similar mechanisms may live.

---

## What We Are Doing

The project treats the literature as a mechanism-discovery problem.

Each paper is processed into one of three outcomes:

- it contains no useful transferable mechanism
- it contains a mechanism that is interesting but not executable
- it contains a mechanism that may support a real strategy hypothesis, a regime filter, or a concrete anti-pattern

That means the pipeline is designed to answer questions like:

- Which `q_fin` papers describe execution or pricing mechanisms rather than generic forecasting?
- Which mechanisms recur across subfields such as microstructure, options, portfolio management, risk management, and statistical finance?
- Which mechanisms look structurally relevant to `tradecore`, even if the paper itself was not written with our target market in mind?
- Which candidate ideas are likely to fail, decay, or depend on assumptions we do not have?

The system is therefore not optimized for “find the most similar paper.” It is optimized for “find the most structurally informative mechanism.”

## Why This Approach

A plain literature review does not scale across `24k+` papers, and a plain embedding workflow usually returns obvious neighbors. That is not enough for this lab.

We are instead trying to build a machine-assisted research loop with these properties:

- it can reject irrelevant papers early
- it can separate surface topic from reusable mechanism
- it can preserve blocker and fragility information, not just upside claims
- it can generate candidate research outputs that are explicit enough to test

The central thesis is that a useful result is not “this cluster of papers looks interesting.” A useful result is one of:

- a candidate strategy primitive worth validation
- a missing executor primitive that suggests what `tradecore` should learn to express
- a regime filter that tells us when a class of strategies should or should not work
- a failure mode that prevents us from chasing a false analogy

## How The Pipeline Works

The current pipeline has five layers.

### 1. Corpus Layer

We keep a canonical local SQLite store of papers, metadata, and downstream artifacts. Right now the active study is `q_fin`-first, and the store contains `24,203` `q_fin` papers.

### 2. Extraction Layer

A local model reads each abstract and emits `0..N` `mechanism_instances` per paper. The extraction contract forces the model to state:

- what the mechanism is
- what kind of insight it represents
- what assumptions it relies on
- what fragility and failure conditions apply
- why the idea may have been missed or underused

This matters because we do not want a pile of papers labeled “interesting.” We want a queue of claims that are structured enough to support ranking and criticism.

### 3. Normalization Layer

Accepted mechanisms are normalized into a controlled ontology. This step converts heterogeneous paper language into comparable structural facets, including:

- market domain
- instrument type
- edge source
- execution style
- holding horizon
- market conditions
- failure modes

This is how the system can compare a market-making paper to a term-structure paper without depending on raw vocabulary overlap.

### 4. Retrieval And Scoring Layer

Mechanisms are turned into a multi-view discovery stack rather than a single semantic search index. The retrieval surface is built from five signals:

1. structured fingerprint matching
2. sparse lexical retrieval
3. dense vector embeddings
4. graph relations across mechanism families
5. local reranking for transfer plausibility and blocker awareness

The ranking logic is trying to reward:

- structural relevance
- lexical non-obviousness
- plausible transfer path
- explicit evidence
- underexploited or frontier-like mechanisms

It is also trying to penalize:

- vague or weak evidence
- catastrophic blockers
- high-fit claims without specific failure context
- research dead ends that only sound adjacent

## Discovery Benchmark

The lab should not treat this system as successful just because it returns plausible-looking candidates. It must show that it can recover structural-near, lexical-far mechanisms better than simpler baselines.

The benchmark buckets are:

- lexical-near / structural-near
- lexical-near / structural-far
- lexical-far / structural-near
- lexical-far / structural-far

The required baselines are:

- keyword or BM25 retrieval
- dense-only retrieval
- citation-neighbor retrieval

The success condition is hard: the hybrid multi-view system must materially outperform those baselines on lexical-far / structural-near cases. Otherwise we should interpret the system as a better relevance stack, not yet a real discovery engine.

## Proactive Discovery Modes

The system is not supposed to wait for an operator to enumerate all useful search hooks. It should also run proactive discovery jobs over the mechanism surface.

The main proactive modes are:

- structural-near, lexical-far holdout mining
- bridge-mechanism discovery across disconnected literature families
- contradiction mining for anti-transfer evidence
- rare but high-fit fingerprint combination mining
- zero-seed-vocabulary candidate surfacing

These jobs matter because the target is not only searchability. The target is active surfacing of mechanisms a researcher would not have thought to query directly.

### 5. Output Layer

The final output is a ranked set of strategy briefs. Each brief is supposed to say:

- what the mechanism family is
- why it might transfer
- what assumptions must hold
- what would cause failure
- what the cheapest validation path is

That is the point where literature processing becomes actionable research.

## What “Meaningful Results” Means Here

The lab should not judge this system by volume alone. A full run can produce thousands of intermediate artifacts and still fail to produce useful research.

For this project, a meaningful result means a candidate that is:

- not just a restatement of standard `q_fin` knowledge
- structurally specific enough to explain what the mechanism is
- bounded by clear assumptions and failure modes
- plausible enough to justify validation work

A candidate should not enter the final queue unless it has all four of:

- a mechanism statement
- a transfer path
- an explicit blocker or failure mode
- a cheapest validation path

The strongest outputs would be:

1. A genuinely new strategy primitive that looks expressible or nearly expressible in `tradecore`.
2. A missing executor primitive that tells us what capability gap matters most.
3. A regime filter that improves when and where an existing strategy class should be deployed.
4. A negative result that kills off a tempting but invalid analogy before we waste time on it.

That last category matters. A good research engine should reduce false positives, not just generate more ideas.

## How We Estimate “Underused”

The system should not treat “underexploited” as a vibe. It is estimated from proxies such as:

- distance from seed vocabulary
- distance from dominant citation neighborhoods
- cross-domain origin
- implementation friction
- evidence of high relevance but low exposure to the target discourse

Those proxies are imperfect, but they are better than leaving novelty and underuse as pure operator intuition.

## Why The Current Full q_fin Study Matters

The current run is important because it moves the project from pilot-scale plumbing to corpus-scale evidence.

The full `q_fin` study will tell us:

- how many papers in the corpus yield usable mechanism records at all
- how much of the corpus is generic forecasting or risk modeling rather than mechanism-bearing work
- which mechanism families dominate the literature
- whether the ranking surface can separate promising hypotheses from dead ends at scale
- whether the top of the queue contains reusable ideas or only familiar same-domain patterns

Even if the first full run does not produce strong final briefs, it is still valuable because it gives the lab an empirical map of the `q_fin` mechanism surface rather than a hand-wavy belief about what is “in the literature.”

A full `q_fin` run may produce mostly familiar same-family mechanisms, which would imply that the next gain is more likely to come from cross-domain expansion than deeper ranking inside `q_fin`.

## What We Expect To Learn From Here

There are four concrete outcomes we hope to get from the full `q_fin` run.

### Outcome 1: A Clean Mechanism Inventory

We expect to end up with a much larger canonical inventory of active `mechanism_instances`. This will let us quantify the real composition of the literature instead of arguing from anecdote.

### Outcome 2: A Better Separation Between Signal And Noise

Many papers in `q_fin` are likely to collapse into low-value categories such as generic forecasting, portfolio optimization, or statistical modeling without a real transferable execution mechanism. That is not failure. That filtering step is part of the result.

### Outcome 3: A Ranked Queue Of Hypotheses

If the pipeline works, the top of the queue should contain:

- mechanism families that recur across multiple papers
- candidates with strong enough structure to write a real brief
- explicit blocker and anti-transfer information

### Outcome 4: Clear Evidence About What Is Missing

If the queue remains weak, the lab still learns something important. We will know whether the bottleneck is:

- extraction quality
- normalization quality
- ranking logic
- the current `q_fin`-only scope
- or the simple fact that many papers do not actually encode reusable mechanisms

That is a valid research result because it changes what the next iteration should be.

## Current State

Current operational facts:

- canonical local store: [data/structural-analogy/paperview.sqlite3](/Users/devrel/Projects/recallnet/paperview/data/structural-analogy/paperview.sqlite3)
- `q_fin` papers in store: `24,203`
- current full-study pilot batch: [data/structural-analogy/pilots/qfin-full-study/papers.jsonl](/Users/devrel/Projects/recallnet/paperview/data/structural-analogy/pilots/qfin-full-study/papers.jsonl)
- current extraction run: `abstract_extraction-v22-qfin-full-study`
- run artifacts root: [data/structural-analogy/runs/abstract_extraction-v22-qfin-full-study](/Users/devrel/Projects/recallnet/paperview/data/structural-analogy/runs/abstract_extraction-v22-qfin-full-study)

Before this full run, the repo had already validated the downstream pipeline on smaller slices and expanded the live mechanism store to `153` active mechanisms. What it did not have yet was a full-corpus `q_fin` extraction pass. That is the gap now being closed.

## Risks And Failure Modes

The main research risks are straightforward.

- The extraction model may be too conservative and collapse too many papers to low-value outputs.
- The extraction model may be too aggressive and overclaim transfer relevance on generic model papers.
- The normalized ontology may still compress distinct mechanisms into overly broad families.
- The ranking surface may prefer familiar same-domain patterns over genuinely useful new hypotheses.
- A large q_fin-only run may still produce mostly obvious same-family candidates.

None of these invalidate the project. They tell us where the next iteration should focus.

## Near-Term Success Criteria

For the next phase, success should mean:

- the full `q_fin` extraction run completes
- the accepted subset is ingested into canonical `mechanism_instances`
- the full downstream chain is rerun on that larger store
- the top-ranked outputs are inspectable as concrete briefs
- the lab can judge whether the queue contains enough genuinely testable hypotheses to warrant deeper analyst review
- the top queue contains a non-trivial share of lexically non-obvious candidates
- at least some top candidates survive analyst review into real briefs
- at least one top candidate qualifies as a holdout case with minimal seed-vocabulary overlap

In other words, the near-term goal is not to “declare victory.” It is to finish the first real corpus-scale pass and inspect whether the research surface becomes meaningfully better than the pilot slices.

## Bottom Line

The lab is building a mechanism-discovery engine over the `q_fin` literature. The current full run is the first time that idea is being applied to the entire local `q_fin` store instead of small pilot slices.

The current full `q_fin` run is a baseline corpus-scale study, not the intended boundary of the research engine. The engine is meant to generalize to adjacent literatures wherever structurally similar mechanisms may live.

If this works, the result will not be a prettier corpus browser. It will be a ranked set of mechanism-level research hypotheses with explicit assumptions, blockers, and next tests. If it does not work well enough, we will still get a high-value result: a concrete diagnosis of where the research loop fails at corpus scale.

That is the immediate purpose of the full `q_fin` study now running.

---

## Additional Context (For AIs And Deep Dives)

### Key Definitions

- `mechanism_instance`: the canonical unit of extracted strategy-relevant structure from one paper
- `strategy_brief`: a final candidate packet containing transfer rationale, assumptions, fragility, and a minimal validation plan
- `tradecore_fit`: a bounded estimate of how well a mechanism maps to the executor concepts we care about
- `research_dead_end_worth_excluding`: a useful negative label for papers that are adjacent in language but not actually useful mechanisms

### Current Artifacts

- living plan: [docs/briefings/2026-03-25-structural-analogy-engine-plan.md](/Users/devrel/Projects/recallnet/paperview/docs/briefings/2026-03-25-structural-analogy-engine-plan.md)
- canonical execution plan: [docs/briefings/2026-03-26-structural-analogy-engine-canonical-commit-plan.md](/Users/devrel/Projects/recallnet/paperview/docs/briefings/2026-03-26-structural-analogy-engine-canonical-commit-plan.md)
- technical review brief: [docs/briefings/2026-03-26-structural-analogy-engine-review-brief.md](/Users/devrel/Projects/recallnet/paperview/docs/briefings/2026-03-26-structural-analogy-engine-review-brief.md)

### Current Full-Study Execution State

- batch size: `24,203`
- literature family: `q_fin`
- prompt line: `v22`
- model path: `mlx-community/Qwen2.5-3B-Instruct-4bit`
- run id: `abstract_extraction-v22-qfin-full-study`

### Distribution Note

This document is intended for lab readers who need to understand both:

- what the system is trying to do scientifically
- what the current full-corpus execution is expected to prove or falsify
