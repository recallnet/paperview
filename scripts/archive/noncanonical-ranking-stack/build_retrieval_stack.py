#!/usr/bin/env python3

import argparse
import hashlib
import json
import math
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"
DEFAULT_RETRIEVAL_VERSION = "c10-retrieval-v1"
DEFAULT_RUN_KIND = "retrieval_build"
DEFAULT_EMBEDDING_BACKEND = "hashing"
DEFAULT_MODEL_NAME = "hashing-dense-baseline-v1"
DEFAULT_EMBEDDING_DIM = 512
EMBEDDING_SURFACES = (
    "mechanism_summary",
    "causal_chain",
    "transfer_rationale",
    "fingerprint_text",
)
EMBEDDING_SURFACE_FIELD_MAP = {
    "mechanism_summary": "mechanism_summary_text",
    "causal_chain": "causal_chain_text",
    "transfer_rationale": "transfer_rationale_text",
    "fingerprint_text": "fingerprint_text",
}
POSITIVE_PAIR_KINDS = {"true_far_analog", "obvious_neighbor"}
EDGE_WEIGHTS = {
    "trigger_overlap": 0.35,
    "topology_overlap": 0.25,
    "actor_overlap": 0.15,
    "execution_overlap": 0.10,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build the multi-view retrieval stack over mechanism instances."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-sql-path",
        default=str(DEFAULT_SCHEMA_SQL_PATH),
        help="Path to the SQL schema to apply before building retrieval views.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit retrieval build run id.",
    )
    parser.add_argument(
        "--retrieval-version",
        default=DEFAULT_RETRIEVAL_VERSION,
        help="Retrieval contract version to persist.",
    )
    parser.add_argument(
        "--embedding-backend",
        default=DEFAULT_EMBEDDING_BACKEND,
        choices=("hashing",),
        help="Dense embedding backend. The deterministic hashing backend keeps local tests stable.",
    )
    parser.add_argument(
        "--embedding-model-name",
        default=DEFAULT_MODEL_NAME,
        help="Model name label to persist alongside dense vectors.",
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        default=DEFAULT_EMBEDDING_DIM,
        help="Dense vector dimension.",
    )
    parser.add_argument(
        "--paper-id",
        action="append",
        default=[],
        help="Restrict retrieval build to one or more paper ids.",
    )
    parser.add_argument(
        "--mechanism-instance-id",
        action="append",
        type=int,
        default=[],
        help="Restrict retrieval build to one or more mechanism instance ids.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of mechanism instances to build.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def parse_json_array(value):
    if not value:
        return []
    decoded = json.loads(value)
    return decoded if isinstance(decoded, list) else []


def parse_json_object(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {}


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))


def ensure_run(connection, run_id: str | None, retrieval_version: str, args):
    resolved_run_id = run_id or (
        f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    config = {
        "retrieval_version": retrieval_version,
        "embedding_backend": args.embedding_backend,
        "embedding_model_name": args.embedding_model_name,
        "embedding_dim": args.embedding_dim,
        "embedding_surfaces": list(EMBEDDING_SURFACES),
    }
    existing = connection.execute(
        "SELECT run_id FROM extraction_runs WHERE run_id = ?",
        (resolved_run_id,),
    ).fetchone()
    if existing is None:
        connection.execute(
            """
            INSERT INTO extraction_runs (
              run_id,
              run_kind,
              model_name,
              prompt_version,
              config_json,
              started_at,
              run_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_run_id,
                DEFAULT_RUN_KIND,
                args.embedding_model_name,
                retrieval_version,
                json.dumps(config, sort_keys=True),
                now_utc(),
                "running",
            ),
        )
    else:
        connection.execute(
            """
            UPDATE extraction_runs
            SET run_kind = ?,
                model_name = ?,
                prompt_version = ?,
                config_json = ?,
                run_status = ?,
                completed_at = NULL
            WHERE run_id = ?
            """,
            (
                DEFAULT_RUN_KIND,
                args.embedding_model_name,
                retrieval_version,
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def build_filters(args):
    clauses = ["mi.lifecycle_status = 'active'"]
    params = []
    if args.paper_id:
        placeholders = ", ".join("?" for _ in args.paper_id)
        clauses.append(f"mi.paper_id IN ({placeholders})")
        params.extend(args.paper_id)
    if args.mechanism_instance_id:
        placeholders = ", ".join("?" for _ in args.mechanism_instance_id)
        clauses.append(f"mi.mechanism_instance_id IN ({placeholders})")
        params.extend(args.mechanism_instance_id)
    limit_clause = f" LIMIT {args.limit}" if args.limit is not None else ""
    return " AND ".join(clauses), params, limit_clause


def load_mechanisms(connection, args):
    connection.row_factory = sqlite3.Row
    where_clause, params, limit_clause = build_filters(args)
    query = f"""
        SELECT
          mi.mechanism_instance_id,
          mi.paper_id,
          mi.mechanism_label,
          mi.mechanism_summary,
          mi.insight_type,
          mi.evidence_confidence,
          mi.required_assumptions_json,
          mi.assumption_violations_json,
          mi.fragility_flags_json,
          mi.capacity_constraints_json,
          mi.failure_regimes_json,
          mi.mechanism_json,
          p.title,
          p.abstract,
          p.literature_family,
          p.evaluation_split,
          mf.trigger_json,
          mf.state_variables_json,
          mf.actor_structure_json,
          mf.market_topology_json,
          mf.pricing_path_json,
          mf.execution_shape_json,
          mf.liquidity_regime_json,
          mf.capacity_limit_json,
          mf.boundary_conditions_json,
          mf.portability_blockers_json,
          mf.ambiguity_flags_json,
          mf.fingerprint_text,
          COALESCE(es.exposure_score, 0.0) AS exposure_score,
          COALESCE(es.underexploited_score, 0.0) AS underexploited_score,
          COALESCE(es.worth_followup_score, 0.0) AS worth_followup_score
        FROM mechanism_instances mi
        JOIN papers p
          ON p.paper_id = mi.paper_id
        JOIN mechanism_fingerprints mf
          ON mf.mechanism_instance_id = mi.mechanism_instance_id
         AND mf.mechanism_fingerprint_id = (
           SELECT mf2.mechanism_fingerprint_id
           FROM mechanism_fingerprints mf2
           WHERE mf2.mechanism_instance_id = mi.mechanism_instance_id
           ORDER BY mf2.updated_at DESC, mf2.mechanism_fingerprint_id DESC
           LIMIT 1
         )
        LEFT JOIN mechanism_exposure_scores es
          ON es.mechanism_instance_id = mi.mechanism_instance_id
         AND es.exposure_score_id = (
           SELECT es2.exposure_score_id
           FROM mechanism_exposure_scores es2
           WHERE es2.mechanism_instance_id = mi.mechanism_instance_id
           ORDER BY es2.updated_at DESC, es2.exposure_score_id DESC
           LIMIT 1
         )
        WHERE {where_clause}
        ORDER BY mi.mechanism_instance_id
        {limit_clause}
    """
    return connection.execute(query, params).fetchall()


def load_evidence_bundles(connection, mechanism_ids):
    if not mechanism_ids:
        return {}
    placeholders = ", ".join("?" for _ in mechanism_ids)
    rows = connection.execute(
        f"""
        SELECT
          mes.mechanism_instance_id,
          mes.evidence_text,
          COALESCE(ps.section_label, mes.evidence_kind, '') AS section_label
        FROM mechanism_evidence_spans mes
        LEFT JOIN paper_sections ps
          ON ps.section_id = mes.section_id
        WHERE mes.mechanism_instance_id IN ({placeholders})
        ORDER BY mes.mechanism_instance_id, ps.section_order, mes.evidence_span_id
        """,
        mechanism_ids,
    ).fetchall()
    bundles = defaultdict(lambda: {"texts": [], "section_labels": []})
    for mechanism_instance_id, evidence_text, section_label in rows:
        if evidence_text:
            bundles[mechanism_instance_id]["texts"].append(normalize_text(evidence_text))
        if section_label:
            bundles[mechanism_instance_id]["section_labels"].append(section_label)
    return bundles


def build_causal_chain_text(row):
    segments = []
    for field_name in (
        "trigger_json",
        "state_variables_json",
        "market_topology_json",
        "pricing_path_json",
        "execution_shape_json",
    ):
        values = parse_json_array(row[field_name])
        if values:
            label = field_name.replace("_json", "")
            segments.append(f"{label}: {', '.join(values)}")
    mechanism_summary = normalize_text(row["mechanism_summary"])
    if mechanism_summary:
        segments.append(f"summary: {mechanism_summary}")
    return normalize_text(" | ".join(segments))


def build_transfer_rationale_text(row):
    mechanism_json = parse_json_object(row["mechanism_json"])
    parts = [
        f"literature family: {row['literature_family']}",
        f"insight type: {row['insight_type']}",
        f"tradecore fit: {mechanism_json.get('tradecore_fit', 'unknown')}",
        f"prediction portability: {mechanism_json.get('prediction_market_portability', 'unknown')}",
        f"novel portability: {mechanism_json.get('novel_market_portability', 'unknown')}",
    ]
    blockers = parse_json_array(row["portability_blockers_json"])
    if blockers:
        parts.append(f"portability blockers: {', '.join(blockers)}")
    assumptions = parse_json_array(row["required_assumptions_json"])
    if assumptions:
        parts.append(f"required assumptions: {', '.join(assumptions)}")
    fragility = parse_json_array(row["fragility_flags_json"])
    if fragility:
        parts.append(f"fragility: {', '.join(fragility)}")
    return normalize_text(" | ".join(parts))


def build_sparse_document_text(row, evidence_bundle):
    components = [
        normalize_text(row["title"]),
        normalize_text(row["mechanism_label"]),
        normalize_text(row["mechanism_summary"]),
        normalize_text(row["abstract"]),
    ]
    section_labels = evidence_bundle.get("section_labels", [])
    if section_labels:
        components.append("sections: " + ", ".join(section_labels))
    for evidence_text in evidence_bundle.get("texts", []):
        components.append(evidence_text)
    return normalize_text("\n".join(component for component in components if component))


def build_source_payload(row, evidence_bundle):
    mechanism_json = parse_json_object(row["mechanism_json"])
    return {
        "literature_family": row["literature_family"],
        "evaluation_split": row["evaluation_split"],
        "insight_type": row["insight_type"],
        "evidence_confidence": row["evidence_confidence"],
        "mechanism_traits": {
            "tradecore_fit": mechanism_json.get("tradecore_fit", "unknown"),
            "prediction_market_portability": mechanism_json.get(
                "prediction_market_portability", "unknown"
            ),
            "novel_market_portability": mechanism_json.get(
                "novel_market_portability", "unknown"
            ),
            "likely_crowding": mechanism_json.get("likely_crowding", "unknown"),
        },
        "invariant_type": mechanism_json.get("invariant_type", "other"),
        "invariant_statement": mechanism_json.get("invariant_statement", ""),
        "market_object": mechanism_json.get("market_object", ""),
        "trigger_window": mechanism_json.get("trigger_window", ""),
        "market_lifecycle_phase": mechanism_json.get("market_lifecycle_phase", "unknown"),
        "wrong_actor": mechanism_json.get("wrong_actor", ""),
        "why_wrong": mechanism_json.get("why_wrong", ""),
        "why_persistence": mechanism_json.get("why_persistence", ""),
        "closure_mechanism": mechanism_json.get("closure_mechanism", ""),
        "death_condition": mechanism_json.get("death_condition", ""),
        "executor_gap": mechanism_json.get("executor_gap", ""),
        "cheap_validation_step": mechanism_json.get("cheap_validation_step", ""),
        "fast_falsifier": mechanism_json.get("fast_falsifier", ""),
        "novelty_reason": mechanism_json.get("novelty_reason", ""),
        "composition_opportunity": mechanism_json.get("composition_opportunity", ""),
        "edge_confidence": mechanism_json.get("edge_confidence", "speculative"),
        "fingerprint_facets": {
            "trigger": parse_json_array(row["trigger_json"]),
            "state_variables": parse_json_array(row["state_variables_json"]),
            "actor_structure": parse_json_array(row["actor_structure_json"]),
            "market_topology": parse_json_array(row["market_topology_json"]),
            "pricing_path": parse_json_array(row["pricing_path_json"]),
            "execution_shape": parse_json_array(row["execution_shape_json"]),
            "liquidity_regime": parse_json_array(row["liquidity_regime_json"]),
            "capacity_limit": parse_json_array(row["capacity_limit_json"]),
            "boundary_conditions": parse_json_array(row["boundary_conditions_json"]),
            "portability_blockers": parse_json_array(row["portability_blockers_json"]),
            "ambiguity_flags": parse_json_array(row["ambiguity_flags_json"]),
        },
        "section_labels": evidence_bundle.get("section_labels", []),
        "required_assumptions": parse_json_array(row["required_assumptions_json"]),
        "assumption_violations": parse_json_array(row["assumption_violations_json"]),
        "fragility_flags": parse_json_array(row["fragility_flags_json"]),
        "capacity_constraints": parse_json_array(row["capacity_constraints_json"]),
        "failure_regimes": parse_json_array(row["failure_regimes_json"]),
        "exposure_score": row["exposure_score"],
        "underexploited_score": row["underexploited_score"],
        "worth_followup_score": row["worth_followup_score"],
    }


def build_document_rows(rows, evidence_bundles):
    document_rows = []
    for row in rows:
        evidence_bundle = evidence_bundles.get(
            row["mechanism_instance_id"], {"texts": [], "section_labels": []}
        )
        evidence_text = normalize_text("\n".join(evidence_bundle.get("texts", [])))
        document_rows.append(
            {
                "mechanism_instance_id": row["mechanism_instance_id"],
                "paper_id": row["paper_id"],
                "mechanism_summary_text": normalize_text(row["mechanism_summary"]),
                "causal_chain_text": build_causal_chain_text(row),
                "transfer_rationale_text": build_transfer_rationale_text(row),
                "fingerprint_text": normalize_text(row["fingerprint_text"]),
                "sparse_document_text": build_sparse_document_text(row, evidence_bundle),
                "evidence_text": evidence_text,
                "source_json": json.dumps(
                    build_source_payload(row, evidence_bundle), sort_keys=True
                ),
                "row": row,
            }
        )
    return document_rows


def tokenize(text):
    return [token for token in re.split(r"[^a-z0-9]+", text.lower()) if token]


def embed_text_hashing(text: str, dim: int):
    vector = [0.0] * dim
    for token in tokenize(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        slot = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[slot] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def hash_source_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_dense_embeddings(document_rows, args):
    dense_rows = []
    for document_row in document_rows:
        for surface in EMBEDDING_SURFACES:
            surface_text = document_row[EMBEDDING_SURFACE_FIELD_MAP[surface]]
            dense_rows.append(
                {
                    "mechanism_instance_id": document_row["mechanism_instance_id"],
                    "paper_id": document_row["paper_id"],
                    "embedding_surface": surface,
                    "vector": embed_text_hashing(surface_text, args.embedding_dim),
                    "source_text_hash": hash_source_text(surface_text),
                }
            )
    return dense_rows


def jaccard(values_a, values_b):
    set_a = set(values_a)
    set_b = set(values_b)
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def load_positive_benchmark_pairs(connection):
    positive_pairs = set()
    for source_id, candidate_id, pair_kind in connection.execute(
        """
        SELECT source_mechanism_instance_id, candidate_mechanism_instance_id, pair_kind
        FROM benchmark_pairs
        WHERE source_mechanism_instance_id IS NOT NULL
          AND candidate_mechanism_instance_id IS NOT NULL
        """
    ):
        if pair_kind not in POSITIVE_PAIR_KINDS:
            continue
        positive_pairs.add((source_id, candidate_id))
        positive_pairs.add((candidate_id, source_id))
    return positive_pairs


def _ordered_pair(left_id, right_id):
    if left_id < right_id:
        return (left_id, right_id)
    return (right_id, left_id)


def graph_edge_candidates(rows, positive_pairs):
    # @context decision -- C10 has to survive growing accepted checkpoints. The original
    # implementation rebuilt payloads for every pair and scanned all row pairs, which
    # becomes effectively quadratic on the halfway q_fin slice. We index facet tokens
    # first and only materialize pairs that share an actual supported relation so the
    # graph contract stays the same while the build remains tractable.
    row_payloads = {}
    postings = {
        "trigger_overlap": defaultdict(list),
        "topology_overlap": defaultdict(list),
        "actor_overlap": defaultdict(list),
        "execution_overlap": defaultdict(list),
    }
    candidate_state = {}
    literature_family_by_id = {}
    max_posting_size = max(500, len(rows) // 10)

    def get_candidate(candidate_key):
        if candidate_key not in candidate_state:
            candidate_state[candidate_key] = {
                "trigger_overlap": set(),
                "topology_overlap": set(),
                "actor_overlap": set(),
                "execution_overlap": set(),
                "same_family": False,
                "positive_benchmark_link": False,
            }
        return candidate_state[candidate_key]

    for row in rows:
        mechanism_id = row["mechanism_instance_id"]
        source_payload = build_source_payload(row, {"section_labels": [], "texts": []})
        facets = source_payload["fingerprint_facets"]
        row_payloads[mechanism_id] = {
            "trigger_overlap": set(facets["trigger"]),
            "topology_overlap": set(facets["market_topology"]),
            "actor_overlap": set(facets["actor_structure"]),
            "execution_overlap": set(facets["execution_shape"]),
        }
        literature_family_by_id[mechanism_id] = row["literature_family"]
        for rationale_key in EDGE_WEIGHTS:
            for value in row_payloads[mechanism_id][rationale_key]:
                postings[rationale_key][value].append(mechanism_id)

    for rationale_key, posting_map in postings.items():
        for value, mechanism_ids in posting_map.items():
            ordered_ids = sorted(set(mechanism_ids))
            if len(ordered_ids) < 2:
                continue
            if len(ordered_ids) > max_posting_size:
                continue
            for index, left_id in enumerate(ordered_ids):
                for right_id in ordered_ids[index + 1 :]:
                    get_candidate((left_id, right_id))[rationale_key].add(value)

    for left_id, right_id in positive_pairs:
        get_candidate(_ordered_pair(left_id, right_id))["positive_benchmark_link"] = True

    edge_rows = []
    for (left_id, right_id), rationale in candidate_state.items():
        weight = 0.0
        edge_rationale = {}
        for rationale_key, base_weight in EDGE_WEIGHTS.items():
            overlaps = sorted(rationale[rationale_key])
            if overlaps:
                edge_rationale[rationale_key] = overlaps
                weight += base_weight
        if literature_family_by_id.get(left_id) == literature_family_by_id.get(right_id):
            weight += 0.05
            edge_rationale["same_family"] = True
        if rationale["positive_benchmark_link"]:
            weight += 0.35
            edge_rationale["positive_benchmark_link"] = True
        if weight < 0.35:
            continue
        edge_kind = "structural_relation"
        if edge_rationale.get("positive_benchmark_link"):
            edge_kind = "benchmark_supported_relation"
        rationale_json = json.dumps(edge_rationale, sort_keys=True)
        edge_rows.append(
            {
                "source_mechanism_instance_id": left_id,
                "target_mechanism_instance_id": right_id,
                "edge_kind": edge_kind,
                "edge_weight": min(weight, 1.0),
                "rationale_json": rationale_json,
            }
        )
        edge_rows.append(
            {
                "source_mechanism_instance_id": right_id,
                "target_mechanism_instance_id": left_id,
                "edge_kind": edge_kind,
                "edge_weight": min(weight, 1.0),
                "rationale_json": rationale_json,
            }
        )
    return edge_rows


def persist_documents(connection, document_rows, run_id: str, retrieval_version: str):
    for document_row in document_rows:
        connection.execute(
            """
            INSERT INTO mechanism_retrieval_documents (
              mechanism_instance_id,
              paper_id,
              run_id,
              retrieval_version,
              mechanism_summary_text,
              causal_chain_text,
              transfer_rationale_text,
              fingerprint_text,
              sparse_document_text,
              evidence_text,
              source_json,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mechanism_instance_id, run_id, retrieval_version) DO UPDATE SET
              paper_id = excluded.paper_id,
              mechanism_summary_text = excluded.mechanism_summary_text,
              causal_chain_text = excluded.causal_chain_text,
              transfer_rationale_text = excluded.transfer_rationale_text,
              fingerprint_text = excluded.fingerprint_text,
              sparse_document_text = excluded.sparse_document_text,
              evidence_text = excluded.evidence_text,
              source_json = excluded.source_json,
              updated_at = excluded.updated_at
            """,
            (
                document_row["mechanism_instance_id"],
                document_row["paper_id"],
                run_id,
                retrieval_version,
                document_row["mechanism_summary_text"],
                document_row["causal_chain_text"],
                document_row["transfer_rationale_text"],
                document_row["fingerprint_text"],
                document_row["sparse_document_text"],
                document_row["evidence_text"],
                document_row["source_json"],
                now_utc(),
            ),
        )


def persist_dense_embeddings(connection, dense_rows, run_id: str, retrieval_version: str, args):
    for dense_row in dense_rows:
        connection.execute(
            """
            INSERT INTO mechanism_dense_embeddings (
              mechanism_instance_id,
              paper_id,
              run_id,
              retrieval_version,
              embedding_backend,
              model_name,
              embedding_surface,
              embedding_dim,
              vector_json,
              source_text_hash,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mechanism_instance_id, run_id, retrieval_version, embedding_surface, model_name)
            DO UPDATE SET
              paper_id = excluded.paper_id,
              embedding_backend = excluded.embedding_backend,
              embedding_dim = excluded.embedding_dim,
              vector_json = excluded.vector_json,
              source_text_hash = excluded.source_text_hash,
              updated_at = excluded.updated_at
            """,
            (
                dense_row["mechanism_instance_id"],
                dense_row["paper_id"],
                run_id,
                retrieval_version,
                args.embedding_backend,
                args.embedding_model_name,
                dense_row["embedding_surface"],
                args.embedding_dim,
                json.dumps(dense_row["vector"]),
                dense_row["source_text_hash"],
                now_utc(),
            ),
        )


def persist_graph_edges(connection, edge_rows, run_id: str, retrieval_version: str):
    for edge_row in edge_rows:
        connection.execute(
            """
            INSERT INTO mechanism_graph_edges (
              source_mechanism_instance_id,
              target_mechanism_instance_id,
              run_id,
              retrieval_version,
              edge_kind,
              edge_weight,
              rationale_json,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_mechanism_instance_id, target_mechanism_instance_id, run_id, retrieval_version, edge_kind)
            DO UPDATE SET
              edge_weight = excluded.edge_weight,
              rationale_json = excluded.rationale_json,
              updated_at = excluded.updated_at
            """,
            (
                edge_row["source_mechanism_instance_id"],
                edge_row["target_mechanism_instance_id"],
                run_id,
                retrieval_version,
                edge_row["edge_kind"],
                edge_row["edge_weight"],
                edge_row["rationale_json"],
                now_utc(),
            ),
        )


def summarize(rows, document_rows, dense_rows, edge_rows, run_id: str, retrieval_version: str, args):
    return {
        "run_id": run_id,
        "retrieval_version": retrieval_version,
        "mechanism_count": len(rows),
        "document_count": len(document_rows),
        "dense_embedding_count": len(dense_rows),
        "graph_edge_count": len(edge_rows),
        "embedding_backend": args.embedding_backend,
        "embedding_model_name": args.embedding_model_name,
        "embedding_dim": args.embedding_dim,
        "embedding_surfaces": list(EMBEDDING_SURFACES),
    }


def write_summary(run_id: str, summary):
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "retrieval_build_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary_path


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    schema_sql_path = Path(args.schema_sql_path).resolve()

    connection = sqlite3.connect(str(db_path))
    try:
        ensure_store_contract(connection, schema_sql_path)
        run_id = ensure_run(connection, args.run_id, args.retrieval_version, args)
        connection.commit()
        rows = load_mechanisms(connection, args)
        if not rows:
            raise SystemExit(
                "no active mechanism instances with fingerprints found; build C05/C08/C09 surfaces first"
            )
        evidence_bundles = load_evidence_bundles(
            connection, [row["mechanism_instance_id"] for row in rows]
        )
        document_rows = build_document_rows(rows, evidence_bundles)
        dense_rows = build_dense_embeddings(document_rows, args)
        positive_pairs = load_positive_benchmark_pairs(connection)
        edge_rows = graph_edge_candidates(rows, positive_pairs)

        connection.execute("BEGIN")
        try:
            persist_documents(connection, document_rows, run_id, args.retrieval_version)
            persist_dense_embeddings(
                connection, dense_rows, run_id, args.retrieval_version, args
            )
            persist_graph_edges(connection, edge_rows, run_id, args.retrieval_version)
            connection.execute(
                """
                UPDATE extraction_runs
                SET run_status = ?, completed_at = ?
                WHERE run_id = ?
                """,
                ("completed", now_utc(), run_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()

    summary = summarize(rows, document_rows, dense_rows, edge_rows, run_id, args.retrieval_version, args)
    summary_path = write_summary(run_id, summary)
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
