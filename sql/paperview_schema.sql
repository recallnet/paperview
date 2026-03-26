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
  label_kind TEXT NOT NULL,
  label_value TEXT NOT NULL,
  notes TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (mechanism_instance_id) REFERENCES mechanism_instances(mechanism_instance_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_family_id) REFERENCES candidate_families(candidate_family_id) ON DELETE CASCADE,
  FOREIGN KEY (benchmark_pair_id) REFERENCES benchmark_pairs(benchmark_pair_id) ON DELETE CASCADE
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
ON analyst_labels (mechanism_instance_id, candidate_family_id, benchmark_pair_id);

CREATE INDEX IF NOT EXISTS idx_paper_extractions_paper_id
ON paper_extractions (paper_id);

CREATE INDEX IF NOT EXISTS idx_paper_fingerprints_paper_id
ON paper_fingerprints (paper_id);

CREATE INDEX IF NOT EXISTS idx_paper_embeddings_paper_id
ON paper_embeddings (paper_id);

CREATE INDEX IF NOT EXISTS idx_paper_edges_source_target
ON paper_edges (source_paper_id, target_paper_id);

CREATE INDEX IF NOT EXISTS idx_strategy_candidates_status
ON strategy_candidates (candidate_status);
