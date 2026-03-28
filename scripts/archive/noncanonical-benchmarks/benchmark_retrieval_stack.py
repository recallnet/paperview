#!/usr/bin/env python3

import argparse
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"
DEFAULT_RETRIEVAL_VERSION = "c10-retrieval-v1"
DEFAULT_RUN_KIND = "retrieval_benchmark"
DENSE_BASELINE_VIEW = "dense_mechanism_summary"
KEYWORD_BASELINE_VIEW = "sparse"
CITATION_BASELINE_VIEW = "citation_neighbor"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Benchmark the multi-view retrieval stack against benchmark_pairs."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-sql-path",
        default=str(DEFAULT_SCHEMA_SQL_PATH),
        help="Path to the SQL schema to apply before benchmarking.",
    )
    parser.add_argument(
        "--retrieval-run-id",
        required=True,
        help="Retrieval build run id produced by build_retrieval_stack.py.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit benchmark run id.",
    )
    parser.add_argument(
        "--retrieval-version",
        default=DEFAULT_RETRIEVAL_VERSION,
        help="Retrieval contract version to benchmark.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def tokenize(text):
    return [token for token in re.split(r"[^a-z0-9]+", (text or "").lower()) if token]


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


def avg(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))


def ensure_run(connection, run_id: str | None, retrieval_version: str, retrieval_run_id: str):
    resolved_run_id = run_id or (
        f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    config = {
        "retrieval_version": retrieval_version,
        "retrieval_run_id": retrieval_run_id,
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
                retrieval_run_id,
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
                retrieval_run_id,
                retrieval_version,
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def load_documents(connection, retrieval_run_id: str, retrieval_version: str):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          mechanism_instance_id,
          paper_id,
          mechanism_summary_text,
          causal_chain_text,
          transfer_rationale_text,
          fingerprint_text,
          sparse_document_text,
          evidence_text,
          source_json
        FROM mechanism_retrieval_documents
        WHERE run_id = ?
          AND retrieval_version = ?
        ORDER BY mechanism_instance_id
        """,
        (retrieval_run_id, retrieval_version),
    ).fetchall()
    documents = {}
    for row in rows:
        source_json = parse_json_object(row["source_json"])
        documents[row["mechanism_instance_id"]] = {
            "paper_id": row["paper_id"],
            "mechanism_summary_text": row["mechanism_summary_text"],
            "causal_chain_text": row["causal_chain_text"],
            "transfer_rationale_text": row["transfer_rationale_text"],
            "fingerprint_text": row["fingerprint_text"],
            "sparse_document_text": row["sparse_document_text"],
            "evidence_text": row["evidence_text"],
            "source_json": source_json,
            "literature_family": source_json.get("literature_family", "unknown"),
        }
    return documents


def load_dense_embeddings(connection, retrieval_run_id: str, retrieval_version: str):
    rows = connection.execute(
        """
        SELECT mechanism_instance_id, embedding_surface, vector_json
        FROM mechanism_dense_embeddings
        WHERE run_id = ?
          AND retrieval_version = ?
        ORDER BY mechanism_instance_id, embedding_surface
        """,
        (retrieval_run_id, retrieval_version),
    ).fetchall()
    embeddings = defaultdict(dict)
    for mechanism_instance_id, embedding_surface, vector_json in rows:
        embeddings[mechanism_instance_id][embedding_surface] = json.loads(vector_json)
    return embeddings


def load_graph_edges(connection, retrieval_run_id: str, retrieval_version: str):
    rows = connection.execute(
        """
        SELECT source_mechanism_instance_id, target_mechanism_instance_id, edge_weight
        FROM mechanism_graph_edges
        WHERE run_id = ?
          AND retrieval_version = ?
        """,
        (retrieval_run_id, retrieval_version),
    ).fetchall()
    graph = defaultdict(dict)
    for source_id, target_id, edge_weight in rows:
        graph[source_id][target_id] = edge_weight
    return graph


def load_paper_edges(connection):
    rows = connection.execute(
        """
        SELECT source_paper_id, target_paper_id, COALESCE(score, 1.0)
        FROM paper_edges
        """
    ).fetchall()
    edge_map = defaultdict(dict)
    for source_paper_id, target_paper_id, score in rows:
        edge_map[source_paper_id][target_paper_id] = score
    return edge_map


def load_benchmark_pairs(connection):
    rows = connection.execute(
        """
        SELECT
          benchmark_pair_id,
          benchmark_key,
          benchmark_bucket,
          pair_kind,
          source_mechanism_instance_id,
          candidate_mechanism_instance_id
        FROM benchmark_pairs
        WHERE source_mechanism_instance_id IS NOT NULL
          AND candidate_mechanism_instance_id IS NOT NULL
        ORDER BY benchmark_pair_id
        """
    ).fetchall()
    return [
        {
            "benchmark_pair_id": row[0],
            "benchmark_key": row[1],
            "benchmark_bucket": row[2],
            "pair_kind": row[3],
            "source_mechanism_instance_id": row[4],
            "candidate_mechanism_instance_id": row[5],
        }
        for row in rows
    ]


def cosine(vector_a, vector_b):
    if not vector_a or not vector_b:
        return 0.0
    return sum(left * right for left, right in zip(vector_a, vector_b))


def jaccard(values_a, values_b):
    set_a = set(values_a)
    set_b = set(values_b)
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def build_sparse_stats(documents):
    doc_tokens = {}
    document_frequency = Counter()
    for mechanism_id, document in documents.items():
        tokens = tokenize(document["sparse_document_text"])
        doc_tokens[mechanism_id] = Counter(tokens)
        for token in set(tokens):
            document_frequency[token] += 1
    return doc_tokens, document_frequency, len(documents)


def sparse_score(query_id, candidate_id, doc_tokens, document_frequency, corpus_size):
    query_terms = doc_tokens[query_id]
    candidate_terms = doc_tokens[candidate_id]
    score = 0.0
    for token, query_tf in query_terms.items():
        candidate_tf = candidate_terms.get(token, 0)
        if candidate_tf == 0:
            continue
        idf = math.log((corpus_size + 1.0) / (document_frequency[token] + 1.0)) + 1.0
        score += idf * query_tf * candidate_tf
    return score


def structured_score(source_doc, candidate_doc):
    source_facets = source_doc["source_json"].get("fingerprint_facets", {})
    candidate_facets = candidate_doc["source_json"].get("fingerprint_facets", {})
    return (
        0.30 * jaccard(source_facets.get("trigger", []), candidate_facets.get("trigger", []))
        + 0.25 * jaccard(
            source_facets.get("market_topology", []),
            candidate_facets.get("market_topology", []),
        )
        + 0.15 * jaccard(
            source_facets.get("execution_shape", []),
            candidate_facets.get("execution_shape", []),
        )
        + 0.15 * jaccard(
            source_facets.get("actor_structure", []),
            candidate_facets.get("actor_structure", []),
        )
        + 0.15 * jaccard(
            source_facets.get("pricing_path", []),
            candidate_facets.get("pricing_path", []),
        )
    )


def graph_score(source_id, candidate_id, graph):
    outgoing = graph.get(source_id, {})
    if not outgoing:
        return 0.0
    max_weight = max(outgoing.values())
    if max_weight == 0:
        return 0.0
    return outgoing.get(candidate_id, 0.0) / max_weight


def citation_neighbor_score(source_doc, candidate_doc, paper_edges):
    source_paper_id = source_doc["paper_id"]
    candidate_paper_id = candidate_doc["paper_id"]
    outgoing = paper_edges.get(source_paper_id, {})
    if not outgoing:
        return 0.0
    max_weight = max(outgoing.values())
    if max_weight == 0:
        return 0.0
    return outgoing.get(candidate_paper_id, 0.0) / max_weight


def hybrid_score(view_scores, candidate_doc):
    source_json = candidate_doc["source_json"]
    worth_followup_score = source_json.get("worth_followup_score", 0.0)
    underexploited_score = source_json.get("underexploited_score", 0.0)
    return (
        0.28 * view_scores["structured"]
        + 0.15 * view_scores["sparse"]
        + 0.22 * view_scores["dense_fingerprint_text"]
        + 0.12 * view_scores["dense_transfer_rationale"]
        + 0.13 * view_scores["graph"]
        + 0.10 * ((worth_followup_score + underexploited_score) / 2.0)
    )


def rank_candidates(
    source_id,
    documents,
    embeddings,
    graph,
    paper_edges,
    doc_tokens,
    document_frequency,
    corpus_size,
):
    scores_by_view = defaultdict(dict)
    source_doc = documents[source_id]
    for candidate_id, candidate_doc in documents.items():
        if candidate_id == source_id:
            continue
        dense_scores = {}
        for surface in (
            "mechanism_summary",
            "causal_chain",
            "transfer_rationale",
            "fingerprint_text",
        ):
            dense_scores[f"dense_{surface}"] = cosine(
                embeddings[source_id].get(surface, []),
                embeddings[candidate_id].get(surface, []),
            )
        view_scores = {
            "structured": structured_score(source_doc, candidate_doc),
            "sparse": sparse_score(
                source_id, candidate_id, doc_tokens, document_frequency, corpus_size
            ),
            "graph": graph_score(source_id, candidate_id, graph),
            CITATION_BASELINE_VIEW: citation_neighbor_score(
                source_doc, candidate_doc, paper_edges
            ),
        }
        view_scores.update(dense_scores)
        view_scores["hybrid"] = hybrid_score(view_scores, candidate_doc)
        for view_name, score in view_scores.items():
            scores_by_view[view_name][candidate_id] = score
    ranked = {}
    for view_name, candidate_scores in scores_by_view.items():
        ranked[view_name] = sorted(
            candidate_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )
    return ranked


def rank_position(ranked_candidates, target_id):
    for index, (candidate_id, _) in enumerate(ranked_candidates, start=1):
        if candidate_id == target_id:
            return index
    return None


def top_candidate_ids(ranked_candidates, limit=20):
    return [candidate_id for candidate_id, _ in ranked_candidates[:limit]]


def reciprocal_rank(rank):
    return 1.0 / rank if rank else 0.0


def persist_results(connection, run_id: str, retrieval_version: str, results):
    for result in results:
        connection.execute(
            """
            INSERT INTO retrieval_benchmark_results (
              benchmark_pair_id,
              source_mechanism_instance_id,
              candidate_mechanism_instance_id,
              run_id,
              retrieval_version,
              view_name,
              candidate_rank,
              reciprocal_rank,
              hit_at_5,
              hit_at_20,
              top_candidate_ids_json,
              metrics_json,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(benchmark_pair_id, run_id, retrieval_version, view_name) DO UPDATE SET
              candidate_rank = excluded.candidate_rank,
              reciprocal_rank = excluded.reciprocal_rank,
              hit_at_5 = excluded.hit_at_5,
              hit_at_20 = excluded.hit_at_20,
              top_candidate_ids_json = excluded.top_candidate_ids_json,
              metrics_json = excluded.metrics_json,
              updated_at = excluded.updated_at
            """,
            (
                result["benchmark_pair_id"],
                result["source_mechanism_instance_id"],
                result["candidate_mechanism_instance_id"],
                run_id,
                retrieval_version,
                result["view_name"],
                result["candidate_rank"],
                result["reciprocal_rank"],
                result["hit_at_5"],
                result["hit_at_20"],
                json.dumps(result["top_candidate_ids"]),
                json.dumps(result["metrics"], sort_keys=True),
                now_utc(),
            ),
        )


def summarize(results, documents):
    by_view = defaultdict(list)
    far_analog_results = defaultdict(list)
    accepted_non_seed = set()
    hybrid_top_families = []
    for result in results:
        by_view[result["view_name"]].append(result)
        if result["benchmark_bucket"] == "lexically_far_structurally_near":
            far_analog_results[result["view_name"]].append(result)
        if result["view_name"] == "hybrid":
            candidate_family = documents[result["candidate_mechanism_instance_id"]][
                "literature_family"
            ]
            if candidate_family != "q_fin" and result["candidate_rank"] and result["candidate_rank"] <= 20:
                accepted_non_seed.add(result["candidate_mechanism_instance_id"])
                hybrid_top_families.append(candidate_family)

    summary_views = {}
    for view_name, view_results in by_view.items():
        summary_views[view_name] = {
            "pair_count": len(view_results),
            "mean_reciprocal_rank": avg(
                result["reciprocal_rank"] for result in view_results
            ),
            "hit_at_20_rate": avg(result["hit_at_20"] for result in view_results),
            "far_analog_mrr": avg(
                result["reciprocal_rank"] for result in far_analog_results[view_name]
            ),
        }

    hybrid_far_mrr = summary_views["hybrid"]["far_analog_mrr"]
    keyword_far_mrr = summary_views.get(KEYWORD_BASELINE_VIEW, {}).get("far_analog_mrr", 0.0)
    dense_far_mrr = summary_views.get(DENSE_BASELINE_VIEW, {}).get("far_analog_mrr", 0.0)
    citation_far_mrr = summary_views.get(CITATION_BASELINE_VIEW, {}).get("far_analog_mrr", 0.0)
    duplicate_family_rate = 0.0
    if hybrid_top_families:
        duplicate_family_rate = (
            len(hybrid_top_families) - len(set(hybrid_top_families))
        ) / len(hybrid_top_families)

    return {
        "views": summary_views,
        "acceptance_metrics": {
            "beats_keyword_baseline_on_lexically_far_structurally_near": (
                hybrid_far_mrr / keyword_far_mrr if keyword_far_mrr > 0 else float("inf")
            ),
            "beats_dense_baseline_on_lexically_far_structurally_near": (
                hybrid_far_mrr / dense_far_mrr if dense_far_mrr > 0 else float("inf")
            ),
            "beats_citation_neighbor_baseline_on_lexically_far_structurally_near": (
                hybrid_far_mrr / citation_far_mrr
                if citation_far_mrr > 0
                else float("inf")
            ),
            "top_20_accepted_non_seed_candidates": len(accepted_non_seed),
            "duplicate_family_rate": duplicate_family_rate,
        },
    }


def write_summary(run_id: str, summary):
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "retrieval_benchmark_summary.json"
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
        run_id = ensure_run(
            connection, args.run_id, args.retrieval_version, args.retrieval_run_id
        )
        connection.commit()
        documents = load_documents(
            connection, args.retrieval_run_id, args.retrieval_version
        )
        embeddings = load_dense_embeddings(
            connection, args.retrieval_run_id, args.retrieval_version
        )
        graph = load_graph_edges(connection, args.retrieval_run_id, args.retrieval_version)
        paper_edges = load_paper_edges(connection)
        benchmark_pairs = load_benchmark_pairs(connection)
        if not documents or not benchmark_pairs:
            raise SystemExit(
                "retrieval documents or benchmark pairs are missing; build C10 surfaces and resolve benchmark mechanisms first"
            )

        doc_tokens, document_frequency, corpus_size = build_sparse_stats(documents)
        results = []
        for pair in benchmark_pairs:
            source_id = pair["source_mechanism_instance_id"]
            candidate_id = pair["candidate_mechanism_instance_id"]
            if source_id not in documents or candidate_id not in documents:
                continue
            ranked = rank_candidates(
                source_id,
                documents,
                embeddings,
                graph,
                paper_edges,
                doc_tokens,
                document_frequency,
                corpus_size,
            )
            for view_name, ranked_candidates in ranked.items():
                candidate_rank = rank_position(ranked_candidates, candidate_id)
                results.append(
                    {
                        "benchmark_pair_id": pair["benchmark_pair_id"],
                        "benchmark_bucket": pair["benchmark_bucket"],
                        "pair_kind": pair["pair_kind"],
                        "source_mechanism_instance_id": source_id,
                        "candidate_mechanism_instance_id": candidate_id,
                        "view_name": view_name,
                        "candidate_rank": candidate_rank,
                        "reciprocal_rank": reciprocal_rank(candidate_rank),
                        "hit_at_5": 1 if candidate_rank and candidate_rank <= 5 else 0,
                        "hit_at_20": 1 if candidate_rank and candidate_rank <= 20 else 0,
                        "top_candidate_ids": top_candidate_ids(ranked_candidates, limit=20),
                        "metrics": {
                            "retrieval_run_id": args.retrieval_run_id,
                            "score_at_candidate": next(
                                (
                                    score
                                    for mechanism_id, score in ranked_candidates
                                    if mechanism_id == candidate_id
                                ),
                                0.0,
                            ),
                        },
                    }
                )

        connection.execute("BEGIN")
        try:
            persist_results(connection, run_id, args.retrieval_version, results)
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

    summary = summarize(results, documents)
    summary["run_id"] = run_id
    summary["retrieval_run_id"] = args.retrieval_run_id
    summary["retrieval_version"] = args.retrieval_version
    summary["benchmark_pair_count"] = len(benchmark_pairs)
    summary_path = write_summary(run_id, summary)
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
