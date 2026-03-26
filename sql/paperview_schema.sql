PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS papers (
  paper_id TEXT PRIMARY KEY,
  source_corpus TEXT NOT NULL,
  literature_family TEXT NOT NULL DEFAULT 'q_fin',
  evaluation_split TEXT NOT NULL DEFAULT 'tuning',
  title TEXT,
  abstract TEXT,
  authors_json TEXT,
  categories_json TEXT,
  primary_category TEXT,
  published_at TEXT,
  updated_at TEXT,
  metadata_path TEXT,
  pdf_path TEXT,
  ingest_status TEXT NOT NULL DEFAULT 'metadata_only',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at_record TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS extraction_runs (
  run_id TEXT PRIMARY KEY,
  run_kind TEXT NOT NULL,
  model_name TEXT,
  prompt_version TEXT,
  config_json TEXT,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT,
  run_status TEXT NOT NULL DEFAULT 'created'
);

CREATE TABLE IF NOT EXISTS paper_sections (
  section_id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id TEXT NOT NULL,
  section_label TEXT NOT NULL,
  section_order INTEGER NOT NULL DEFAULT 0,
  content_text TEXT NOT NULL,
  content_hash TEXT,
  extraction_method TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  UNIQUE (paper_id, section_label, section_order)
);

CREATE TABLE IF NOT EXISTS parse_failures (
  failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id TEXT NOT NULL,
  failure_stage TEXT NOT NULL,
  failure_type TEXT NOT NULL,
  failure_reason TEXT,
  source_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
);

-- @context decision: `mechanism_instances` is the canonical analysis unit from C01 onward.
-- One paper may map to zero, one, or many mechanism instances, so later retrieval and ranking
-- must not assume a 1:1 paper-to-mechanism contract.
CREATE TABLE IF NOT EXISTS mechanism_instances (
  mechanism_instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id TEXT NOT NULL,
  source_extraction_id INTEGER,
  run_id TEXT,
  source_stage TEXT NOT NULL DEFAULT 'abstract_extraction',
  mechanism_label TEXT NOT NULL,
  mechanism_summary TEXT,
  insight_type TEXT NOT NULL DEFAULT 'research_dead_end_worth_excluding',
  evidence_confidence TEXT NOT NULL DEFAULT 'unscored',
  required_assumptions_json TEXT NOT NULL DEFAULT '[]',
  assumption_violations_json TEXT NOT NULL DEFAULT '[]',
  fragility_flags_json TEXT NOT NULL DEFAULT '[]',
  capacity_constraints_json TEXT NOT NULL DEFAULT '[]',
  failure_regimes_json TEXT NOT NULL DEFAULT '[]',
  mechanism_json TEXT NOT NULL DEFAULT '{}',
  lifecycle_status TEXT NOT NULL DEFAULT 'draft',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (source_extraction_id) REFERENCES paper_extractions(extraction_id) ON DELETE SET NULL,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE SET NULL,
  UNIQUE (paper_id, source_extraction_id, mechanism_label)
);

CREATE TABLE IF NOT EXISTS mechanism_evidence_spans (
  evidence_span_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mechanism_instance_id INTEGER NOT NULL,
  paper_id TEXT NOT NULL,
  section_id INTEGER,
  evidence_kind TEXT NOT NULL DEFAULT 'abstract_span',
  char_start INTEGER,
  char_end INTEGER,
  evidence_text TEXT NOT NULL,
  provenance_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (section_id) REFERENCES paper_sections(section_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS candidate_families (
  candidate_family_id INTEGER PRIMARY KEY AUTOINCREMENT,
  family_name TEXT NOT NULL,
  family_status TEXT NOT NULL DEFAULT 'queued',
  family_summary TEXT,
  blocker_requirement_status TEXT NOT NULL DEFAULT 'not_reviewed',
  family_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (family_name)
);

CREATE TABLE IF NOT EXISTS transfer_hypotheses (
  transfer_hypothesis_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mechanism_instance_id INTEGER NOT NULL,
  candidate_family_id INTEGER,
  target_domain TEXT,
  hypothesis_status TEXT NOT NULL DEFAULT 'queued',
  negative_transfer_rationale_json TEXT NOT NULL DEFAULT '[]',
  rationale_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_family_id) REFERENCES candidate_families(candidate_family_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS benchmark_pairs (
  benchmark_pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
  benchmark_key TEXT NOT NULL,
  source_paper_id TEXT,
  candidate_paper_id TEXT,
  source_mechanism_instance_id INTEGER,
  candidate_mechanism_instance_id INTEGER,
  benchmark_bucket TEXT NOT NULL DEFAULT 'lexically_far_structurally_near',
  pair_kind TEXT NOT NULL,
  label_status TEXT NOT NULL DEFAULT 'proposed',
  benchmark_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (source_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  UNIQUE (benchmark_key)
);

CREATE TABLE IF NOT EXISTS analyst_labels (
  analyst_label_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mechanism_instance_id INTEGER,
  candidate_family_id INTEGER,
  benchmark_pair_id INTEGER,
  queryless_candidate_hit_id INTEGER,
  label_kind TEXT NOT NULL,
  label_value TEXT NOT NULL,
  notes TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_family_id) REFERENCES candidate_families(candidate_family_id) ON DELETE CASCADE,
  FOREIGN KEY (benchmark_pair_id) REFERENCES benchmark_pairs(benchmark_pair_id) ON DELETE CASCADE,
  FOREIGN KEY (queryless_candidate_hit_id) REFERENCES queryless_candidate_hits(queryless_candidate_hit_id) ON DELETE CASCADE
);

-- @context requirement: `paper_extractions` remains in the store because the current abstract-first
-- ingest pipeline writes validated model output here, but from C01 onward it is only a transitional
-- staging surface. C05 will map or replace this path with canonical `mechanism_instances` persistence.
CREATE TABLE IF NOT EXISTS paper_extractions (
  extraction_id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  extraction_version TEXT NOT NULL,
  extraction_json TEXT NOT NULL,
  response_contract_version TEXT NOT NULL DEFAULT 'legacy-single-mechanism-v1',
  validation_status TEXT NOT NULL DEFAULT 'unvalidated',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (paper_id, run_id, extraction_version)
);

-- @context decision: C08 moves the retrieval fingerprint surface onto
-- `mechanism_instances`, not papers. A paper can hold multiple active mechanisms,
-- so a paper-level fingerprint would collapse exactly the distinctions later
-- retrieval and family assembly need to preserve.
CREATE TABLE IF NOT EXISTS mechanism_fingerprints (
  mechanism_fingerprint_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mechanism_instance_id INTEGER NOT NULL,
  paper_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  fingerprint_version TEXT NOT NULL,
  trigger_json TEXT NOT NULL,
  state_variables_json TEXT NOT NULL,
  actor_structure_json TEXT NOT NULL,
  market_topology_json TEXT NOT NULL,
  pricing_path_json TEXT NOT NULL,
  execution_shape_json TEXT NOT NULL,
  liquidity_regime_json TEXT NOT NULL,
  capacity_limit_json TEXT NOT NULL,
  boundary_conditions_json TEXT NOT NULL,
  portability_blockers_json TEXT NOT NULL,
  ambiguity_flags_json TEXT NOT NULL DEFAULT '[]',
  serializer_version TEXT NOT NULL,
  fingerprint_text TEXT NOT NULL,
  fingerprint_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (mechanism_instance_id, run_id, fingerprint_version)
);

CREATE TABLE IF NOT EXISTS normalization_reviews (
  normalization_review_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mechanism_instance_id INTEGER NOT NULL,
  paper_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  fingerprint_version TEXT NOT NULL,
  review_status TEXT NOT NULL DEFAULT 'queued',
  ambiguity_flags_json TEXT NOT NULL DEFAULT '[]',
  candidate_mappings_json TEXT NOT NULL DEFAULT '{}',
  review_notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (mechanism_instance_id, run_id, fingerprint_version)
);

-- `paper_fingerprints` remains only as a transitional table for older local
-- files that predate C08. New normalization work should write
-- `mechanism_fingerprints`.
CREATE TABLE IF NOT EXISTS paper_fingerprints (
  fingerprint_id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  fingerprint_version TEXT NOT NULL,
  fingerprint_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (paper_id, run_id, fingerprint_version)
);

-- @context decision: C09 persists exposure and follow-up priors at the
-- `mechanism_instance` level because later retrieval, analyst feedback, and
-- family assembly all operate on mechanisms rather than paper wrappers.
CREATE TABLE IF NOT EXISTS mechanism_exposure_scores (
  exposure_score_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mechanism_instance_id INTEGER NOT NULL,
  paper_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  score_version TEXT NOT NULL,
  literature_family TEXT NOT NULL,
  evaluation_split TEXT NOT NULL,
  exposure_score REAL NOT NULL,
  underexploited_score REAL NOT NULL,
  worth_followup_score REAL NOT NULL,
  family_share REAL NOT NULL,
  trigger_share REAL NOT NULL,
  topology_share REAL NOT NULL,
  duplicate_share REAL NOT NULL,
  benchmark_support REAL NOT NULL,
  ambiguity_burden REAL NOT NULL,
  portability_burden REAL NOT NULL,
  evidence_strength_score REAL NOT NULL,
  tradecore_fit_score REAL NOT NULL,
  crowding_score REAL NOT NULL,
  feature_json TEXT NOT NULL,
  model_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (mechanism_instance_id, run_id, score_version)
);

-- @context decision: C10 persists retrieval-ready text surfaces separately from
-- raw extractions so structured, sparse, dense, and graph views can share one
-- canonical mechanism-level corpus without each view rebuilding ad hoc text.
CREATE TABLE IF NOT EXISTS mechanism_retrieval_documents (
  retrieval_document_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mechanism_instance_id INTEGER NOT NULL,
  paper_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  retrieval_version TEXT NOT NULL,
  mechanism_summary_text TEXT NOT NULL,
  causal_chain_text TEXT NOT NULL,
  transfer_rationale_text TEXT NOT NULL,
  fingerprint_text TEXT NOT NULL,
  sparse_document_text TEXT NOT NULL,
  evidence_text TEXT NOT NULL,
  source_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (mechanism_instance_id, run_id, retrieval_version)
);

CREATE TABLE IF NOT EXISTS mechanism_dense_embeddings (
  mechanism_dense_embedding_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mechanism_instance_id INTEGER NOT NULL,
  paper_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  retrieval_version TEXT NOT NULL,
  embedding_backend TEXT NOT NULL,
  model_name TEXT NOT NULL,
  embedding_surface TEXT NOT NULL,
  embedding_dim INTEGER NOT NULL,
  vector_json TEXT NOT NULL,
  source_text_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (mechanism_instance_id, run_id, retrieval_version, embedding_surface, model_name)
);

CREATE TABLE IF NOT EXISTS mechanism_graph_edges (
  mechanism_graph_edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_mechanism_instance_id INTEGER NOT NULL,
  target_mechanism_instance_id INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  retrieval_version TEXT NOT NULL,
  edge_kind TEXT NOT NULL,
  edge_weight REAL NOT NULL,
  rationale_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (target_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (source_mechanism_instance_id, target_mechanism_instance_id, run_id, retrieval_version, edge_kind)
);

CREATE TABLE IF NOT EXISTS retrieval_benchmark_results (
  retrieval_benchmark_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
  benchmark_pair_id INTEGER NOT NULL,
  source_mechanism_instance_id INTEGER NOT NULL,
  candidate_mechanism_instance_id INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  retrieval_version TEXT NOT NULL,
  view_name TEXT NOT NULL,
  candidate_rank INTEGER,
  reciprocal_rank REAL NOT NULL,
  hit_at_5 INTEGER NOT NULL DEFAULT 0,
  hit_at_20 INTEGER NOT NULL DEFAULT 0,
  top_candidate_ids_json TEXT NOT NULL DEFAULT '[]',
  metrics_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (benchmark_pair_id) REFERENCES benchmark_pairs(benchmark_pair_id) ON DELETE CASCADE,
  FOREIGN KEY (source_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (benchmark_pair_id, run_id, retrieval_version, view_name)
);

-- @context decision: C11 persists queryless mining hits as a first-class
-- pairwise surface because later analyst adjudication and family assembly need
-- auditable reranker sub-scores, evidence anchors, and mining-mode provenance.
-- Reconstructing those later from transient top-k outputs would erase the exact
-- reason a pair was surfaced and make C12/C13 impossible to debug.
CREATE TABLE IF NOT EXISTS queryless_candidate_hits (
  queryless_candidate_hit_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_mechanism_instance_id INTEGER NOT NULL,
  candidate_mechanism_instance_id INTEGER NOT NULL,
  source_paper_id TEXT NOT NULL,
  candidate_paper_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  retrieval_run_id TEXT NOT NULL,
  retrieval_version TEXT NOT NULL,
  mining_version TEXT NOT NULL,
  mining_mode TEXT NOT NULL,
  source_literature_family TEXT NOT NULL,
  candidate_literature_family TEXT NOT NULL,
  source_evaluation_split TEXT NOT NULL,
  candidate_evaluation_split TEXT NOT NULL,
  rank_within_source INTEGER NOT NULL,
  is_cross_family INTEGER NOT NULL DEFAULT 0,
  structural_similarity_score REAL NOT NULL,
  lexical_distance_score REAL NOT NULL,
  transfer_plausibility_score REAL NOT NULL,
  blocker_penalty_score REAL NOT NULL,
  reranker_score REAL NOT NULL,
  rationale_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (source_paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (retrieval_run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (source_mechanism_instance_id, candidate_mechanism_instance_id, run_id, mining_version, mining_mode)
);

-- @context decision: C12 persists learned analyst weights separately from raw
-- C11 mining hits so the system can compare original reranker behavior against
-- post-adjudication adjustments. Folding the learned coefficients into the hit
-- rows would destroy auditability and make later ranking regressions opaque.
CREATE TABLE IF NOT EXISTS analyst_weight_updates (
  analyst_weight_update_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  queryless_run_id TEXT NOT NULL,
  exposure_run_id TEXT,
  mining_version TEXT NOT NULL,
  score_version TEXT NOT NULL,
  mining_mode TEXT NOT NULL,
  update_kind TEXT NOT NULL DEFAULT 'mode_reranker',
  target_label_kind TEXT NOT NULL DEFAULT 'accept',
  training_example_count INTEGER NOT NULL DEFAULT 0,
  positive_example_count INTEGER NOT NULL DEFAULT 0,
  negative_example_count INTEGER NOT NULL DEFAULT 0,
  weights_json TEXT NOT NULL DEFAULT '{}',
  metrics_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (queryless_run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (exposure_run_id) REFERENCES extraction_runs(run_id) ON DELETE SET NULL,
  UNIQUE (run_id, mining_mode, update_kind, target_label_kind)
);

CREATE TABLE IF NOT EXISTS adjudicated_queryless_hits (
  adjudicated_queryless_hit_id INTEGER PRIMARY KEY AUTOINCREMENT,
  queryless_candidate_hit_id INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  analyst_weight_update_id INTEGER,
  queryless_run_id TEXT NOT NULL,
  mining_mode TEXT NOT NULL,
  source_mechanism_instance_id INTEGER NOT NULL,
  candidate_mechanism_instance_id INTEGER NOT NULL,
  adjusted_score REAL NOT NULL,
  adjusted_rank_within_source INTEGER NOT NULL,
  score_delta REAL NOT NULL,
  support_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (queryless_candidate_hit_id) REFERENCES queryless_candidate_hits(queryless_candidate_hit_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (analyst_weight_update_id) REFERENCES analyst_weight_updates(analyst_weight_update_id) ON DELETE SET NULL,
  FOREIGN KEY (queryless_run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (source_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  UNIQUE (queryless_candidate_hit_id, run_id)
);

-- @context decision: C13 keeps family definitions (`candidate_families`) and
-- run-specific ranking outputs separate. A family should survive across reruns,
-- while the gated queue, diversity penalties, and representative members are
-- specific to one analyst-informed ranking pass.
CREATE TABLE IF NOT EXISTS candidate_family_members (
  candidate_family_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_family_id INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  adjudicated_queryless_hit_id INTEGER NOT NULL,
  source_mechanism_instance_id INTEGER NOT NULL,
  candidate_mechanism_instance_id INTEGER NOT NULL,
  member_role TEXT NOT NULL DEFAULT 'representative_hypothesis',
  support_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (candidate_family_id) REFERENCES candidate_families(candidate_family_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (adjudicated_queryless_hit_id) REFERENCES adjudicated_queryless_hits(adjudicated_queryless_hit_id) ON DELETE CASCADE,
  FOREIGN KEY (source_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  UNIQUE (candidate_family_id, run_id, adjudicated_queryless_hit_id)
);

CREATE TABLE IF NOT EXISTS candidate_family_rankings (
  candidate_family_ranking_id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_family_id INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  ranking_version TEXT NOT NULL,
  family_rank INTEGER NOT NULL,
  gate_status TEXT NOT NULL DEFAULT 'queued',
  base_utility_score REAL NOT NULL,
  diversity_penalty_score REAL NOT NULL DEFAULT 0.0,
  final_priority_score REAL NOT NULL,
  rationale_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (candidate_family_id) REFERENCES candidate_families(candidate_family_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (candidate_family_id, run_id, ranking_version)
);

CREATE TABLE IF NOT EXISTS paper_embeddings (
  embedding_id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id TEXT NOT NULL,
  run_id TEXT,
  embedding_kind TEXT NOT NULL,
  model_name TEXT NOT NULL,
  vector_json TEXT NOT NULL,
  source_text_hash TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE SET NULL,
  UNIQUE (paper_id, embedding_kind, model_name, source_text_hash)
);

CREATE TABLE IF NOT EXISTS paper_edges (
  edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_paper_id TEXT NOT NULL,
  target_paper_id TEXT NOT NULL,
  edge_kind TEXT NOT NULL,
  score REAL,
  rationale_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  FOREIGN KEY (target_paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
  UNIQUE (source_paper_id, target_paper_id, edge_kind)
);

CREATE TABLE IF NOT EXISTS strategy_candidates (
  candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_paper_id TEXT,
  candidate_name TEXT NOT NULL,
  candidate_status TEXT NOT NULL DEFAULT 'queued',
  priority_score REAL,
  review_notes TEXT,
  candidate_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_paper_id) REFERENCES papers(paper_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS strategy_briefs (
  strategy_brief_id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_family_id INTEGER NOT NULL,
  candidate_family_ranking_id INTEGER,
  run_id TEXT NOT NULL,
  brief_version TEXT NOT NULL,
  brief_name TEXT NOT NULL,
  brief_status TEXT NOT NULL DEFAULT 'drafted',
  brief_rank INTEGER,
  brief_markdown_path TEXT,
  brief_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (candidate_family_id) REFERENCES candidate_families(candidate_family_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_family_ranking_id) REFERENCES candidate_family_rankings(candidate_family_ranking_id) ON DELETE SET NULL,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  UNIQUE (candidate_family_id, run_id, brief_version)
);

CREATE TABLE IF NOT EXISTS gate_c_brief_reviews (
  gate_c_brief_review_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  strategy_brief_id INTEGER NOT NULL,
  candidate_family_id INTEGER NOT NULL,
  reviewed_by TEXT NOT NULL DEFAULT 'analyst',
  genuinely_new INTEGER,
  worth_validation INTEGER,
  new_executor_primitive INTEGER,
  new_regime_filter INTEGER,
  holdout_near_zero_overlap INTEGER,
  review_notes TEXT,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (strategy_brief_id) REFERENCES strategy_briefs(strategy_brief_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_family_id) REFERENCES candidate_families(candidate_family_id) ON DELETE CASCADE,
  UNIQUE (run_id, strategy_brief_id)
);

CREATE TABLE IF NOT EXISTS gate_c_review_summaries (
  gate_c_review_summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL UNIQUE,
  brief_run_id TEXT NOT NULL,
  reviewed_count INTEGER NOT NULL DEFAULT 0,
  genuinely_new_and_worth_validation_count INTEGER NOT NULL DEFAULT 0,
  new_executor_or_regime_count INTEGER NOT NULL DEFAULT 0,
  holdout_near_zero_overlap_count INTEGER NOT NULL DEFAULT 0,
  gate_c_passed INTEGER NOT NULL DEFAULT 0,
  summary_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (brief_run_id) REFERENCES extraction_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_papers_source_corpus
ON papers (source_corpus);

CREATE INDEX IF NOT EXISTS idx_papers_literature_family
ON papers (literature_family);

CREATE INDEX IF NOT EXISTS idx_papers_evaluation_split
ON papers (evaluation_split);

CREATE INDEX IF NOT EXISTS idx_paper_sections_paper_id
ON paper_sections (paper_id);

CREATE INDEX IF NOT EXISTS idx_parse_failures_paper_id
ON parse_failures (paper_id);

CREATE INDEX IF NOT EXISTS idx_mechanism_instances_paper_id
ON mechanism_instances (paper_id);

CREATE INDEX IF NOT EXISTS idx_mechanism_instances_run_id
ON mechanism_instances (run_id);

CREATE INDEX IF NOT EXISTS idx_mechanism_evidence_spans_mechanism_instance_id
ON mechanism_evidence_spans (mechanism_instance_id);

CREATE INDEX IF NOT EXISTS idx_transfer_hypotheses_mechanism_instance_id
ON transfer_hypotheses (mechanism_instance_id);

CREATE INDEX IF NOT EXISTS idx_transfer_hypotheses_candidate_family_id
ON transfer_hypotheses (candidate_family_id);

CREATE INDEX IF NOT EXISTS idx_candidate_families_status
ON candidate_families (family_status);

CREATE INDEX IF NOT EXISTS idx_benchmark_pairs_source_candidate
ON benchmark_pairs (source_mechanism_instance_id, candidate_mechanism_instance_id);

CREATE INDEX IF NOT EXISTS idx_analyst_labels_targets
ON analyst_labels (mechanism_instance_id, candidate_family_id, benchmark_pair_id, queryless_candidate_hit_id);

CREATE INDEX IF NOT EXISTS idx_paper_extractions_paper_id
ON paper_extractions (paper_id);

CREATE INDEX IF NOT EXISTS idx_paper_fingerprints_paper_id
ON paper_fingerprints (paper_id);

CREATE INDEX IF NOT EXISTS idx_mechanism_fingerprints_mechanism_instance_id
ON mechanism_fingerprints (mechanism_instance_id);

CREATE INDEX IF NOT EXISTS idx_mechanism_fingerprints_run_id
ON mechanism_fingerprints (run_id);

CREATE INDEX IF NOT EXISTS idx_normalization_reviews_mechanism_instance_id
ON normalization_reviews (mechanism_instance_id);

CREATE INDEX IF NOT EXISTS idx_mechanism_exposure_scores_mechanism_instance_id
ON mechanism_exposure_scores (mechanism_instance_id);

CREATE INDEX IF NOT EXISTS idx_mechanism_exposure_scores_run_id
ON mechanism_exposure_scores (run_id);

CREATE INDEX IF NOT EXISTS idx_mechanism_retrieval_documents_mechanism_instance_id
ON mechanism_retrieval_documents (mechanism_instance_id);

CREATE INDEX IF NOT EXISTS idx_mechanism_dense_embeddings_mechanism_surface
ON mechanism_dense_embeddings (mechanism_instance_id, embedding_surface);

CREATE INDEX IF NOT EXISTS idx_mechanism_graph_edges_source_target
ON mechanism_graph_edges (source_mechanism_instance_id, target_mechanism_instance_id);

CREATE INDEX IF NOT EXISTS idx_retrieval_benchmark_results_pair_view
ON retrieval_benchmark_results (benchmark_pair_id, view_name);

CREATE INDEX IF NOT EXISTS idx_queryless_candidate_hits_source_mode
ON queryless_candidate_hits (source_mechanism_instance_id, mining_mode, rank_within_source);

CREATE INDEX IF NOT EXISTS idx_queryless_candidate_hits_candidate
ON queryless_candidate_hits (candidate_mechanism_instance_id);

CREATE INDEX IF NOT EXISTS idx_analyst_weight_updates_mode
ON analyst_weight_updates (queryless_run_id, mining_mode);

CREATE INDEX IF NOT EXISTS idx_adjudicated_queryless_hits_source_mode
ON adjudicated_queryless_hits (source_mechanism_instance_id, mining_mode, adjusted_rank_within_source);

CREATE INDEX IF NOT EXISTS idx_candidate_family_members_family_run
ON candidate_family_members (candidate_family_id, run_id);

CREATE INDEX IF NOT EXISTS idx_candidate_family_rankings_run_rank
ON candidate_family_rankings (run_id, family_rank);

CREATE INDEX IF NOT EXISTS idx_paper_embeddings_paper_id
ON paper_embeddings (paper_id);

CREATE INDEX IF NOT EXISTS idx_paper_edges_source_target
ON paper_edges (source_paper_id, target_paper_id);

CREATE INDEX IF NOT EXISTS idx_strategy_candidates_status
ON strategy_candidates (candidate_status);

CREATE INDEX IF NOT EXISTS idx_strategy_briefs_run_rank
ON strategy_briefs (run_id, brief_rank);

CREATE INDEX IF NOT EXISTS idx_gate_c_brief_reviews_run_brief
ON gate_c_brief_reviews (run_id, strategy_brief_id);

CREATE INDEX IF NOT EXISTS idx_gate_c_review_summaries_brief_run
ON gate_c_review_summaries (brief_run_id);
