---
doc_type: briefing
owner: devrel
review_policy: periodic-7
reviewed: 2026-04-08
status: active
summary: Canonical playbook for turning future structural-analogy findings into purified motifs, evidence packs, and measurement specs.
tags:
  - docs
  - briefing
  - research
  - strategy-discovery
written: 2026-03-26
---

# Structural Analogy Research Finding Playbook

## Purpose

Use this playbook whenever a new snapshot or final run produces ranked candidate families and we want operator-usable research outputs instead of only cluster labels.

The output standard is fixed:

1. `cluster-cartography`
2. `thesis_seed_pack`
3. `motif_evidence_pack`
4. `measurement_spec_pack`

Each later artifact must be derived from the earlier one, not hand-written from memory.

## Canonical Command

Use:

```bash
npm run research:materialize-findings -- --run-id <candidate_family_ranking_run_id>
```

This command:

- selects the highest-ranked non-dead-end families for the supplied run
- applies the cluster purity pass
- emits purified cartography
- derives thesis seeds
- derives motif evidence
- derives measurement specs
- writes a `finding_pack_manifest.json` alongside the artifacts

If a run needs explicit family selection:

```bash
npm run research:materialize-findings -- --run-id <run_id> --family-name <family_a> --family-name <family_b>
```

## Artifact Contract

### 1. Cluster Cartography

Goal:
- expose the paper-level member set
- label each member as `core evidence`, `peripheral analogue`, or `contamination / misclustered`
- recompute subclusters and motif interpretation using retained evidence only

Hard rules:
- no contamination-backed interpretation
- purity ratio must be shown
- top contamination cases must be shown

### 2. Thesis Seed Pack

Goal:
- convert purified motifs into compact candidate trade theses

Hard rules:
- one row per motif
- no motif row without paper support
- no vague cluster headlines
- every row must carry a concrete observable and blocker

### 3. Motif Evidence Pack

Goal:
- make it obvious which motifs are real, which are thin, and which are mostly analogical

Hard rules:
- every claim must be tied to exact extracted mechanism text
- every motif must state the baseline comparison
- every motif must state the strongest reason to believe and the strongest reason to doubt
- one-paper motifs must say they are one-paper-thin explicitly

### 4. Measurement Spec Pack

Goal:
- turn each surviving motif into a trigger / trade / measure template that research or engineering can run

Hard rules:
- every motif needs a trigger condition
- every motif needs primary and secondary observables
- every motif needs minimum data fields and derived features
- every motif needs a spherical-cow edge formula and capacity formula
- every motif needs exactly one decision:
  - `build now`
  - `measure first`
  - `defer`
  - `kill`

## Review Loop

For every new snapshot:

1. Run `research:materialize-findings`.
2. Read `motif_evidence_pack.md` first.
3. If a motif is too thin or contaminated, mark it as `kill` or `defer`.
4. Read `measurement_spec_pack.md`.
5. Start only the `build now` and `measure first` rows.

The review question is not "did the system emit something?"

The review question is:

- does this motif survive purity?
- is it really distinct from the baseline?
- do we have the data to measure it?
- is it worth engineering work?

## Failure Modes

If the run looks repetitive or low-value, diagnose it in this order:

1. low corpus coverage
2. ontology collapse into generic buckets
3. analog search contamination
4. reranking bias
5. only theory/control papers surviving

Do not call a motif "novel" just because the label is unfamiliar.

## Operating Standard For Final Run

The final run should use the same artifact chain as interim snapshots.

Do not invent a special final-report workflow.

The final run is only a larger invocation of the same pipeline:

- same purity pass
- same thesis seed contract
- same evidence pack contract
- same measurement spec contract

That keeps interim and final results comparable and prevents the final run from collapsing back into vague synthesis.
