# Script Archive

This directory holds superseded script surfaces that are preserved for history
but are no longer part of the canonical staged pipeline described in
`docs/briefings/2026-03-25-structural-analogy-engine-plan.md`.

Current archive groups:

- `noncanonical-corpus-helpers/`
  Corpus status, inventory, and readiness helpers from the earlier launch and
  failure-recovery workflow. These are preserved for history but are not part
  of the canonical staged command surface.

- `noncanonical-corpus-pipeline/`
  Launch, retry, reconcile, and pipeline runners from the earlier q-fin corpus
  acquisition workflow. These are preserved together so the archived workflow
  remains coherent without competing from the active root.

- `noncanonical-edge-reset/`
  Edge-reset slice runners, edge-card generators, and semantic trace helpers
  from the older extraction-first reset workflow. These are preserved as a
  group so the archived flow still points at its own card generator.

- `noncanonical-ranking-stack/`
  Ranking, retrieval, queryless-mining, adjudication, and fingerprint scoring
  scripts from the older downstream ranking workflow. These are preserved as a
  group so the archived edge-reset flow can still call the archived stack.

- `noncanonical-downstream-review/`
  Downstream brief generation, queue assessment, and Gate C review scripts from
  the older analyst-facing publication workflow. These are preserved as a group
  so the archived downstream orchestrator still points at its archived review
  steps.

- `noncanonical-benchmarks/`
  Benchmark utilities that were useful for one-off retrieval evaluation but
  are not part of the canonical staged command surface.

- `noncanonical-research-packs/`
  Research-pack and export utilities that produced earlier analyst-facing
  bundles but are not part of the canonical `S01` to `S16` staged pipeline.

- `noncanonical-pilots/`
  Pilot and benchmark materializers that were useful during earlier discovery
  exploration but are not part of the active `S01` to `S16` staged command set.
