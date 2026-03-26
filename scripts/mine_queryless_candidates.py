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
DEFAULT_MINING_VERSION = "c11-queryless-v1"
DEFAULT_RUN_KIND = "queryless_mining"
DEFAULT_TOP_K_PER_MODE = 10
FINGERPRINT_FIELDS = (
    "trigger",
    "state_variables",
    "actor_structure",
    "market_topology",
    "pricing_path",
    "execution_shape",
    "liquidity_regime",
    "capacity_limit",
    "boundary_conditions",
)
TRAIT_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.35, "other": 0.35}
EVIDENCE_SCORE = {"high": 1.0, "medium": 0.65, "low": 0.3, "unscored": 0.45}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mine queryless candidate pairs and persist reranked hits."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-sql-path",
        default=str(DEFAULT_SCHEMA_SQL_PATH),
        help="Path to the SQL schema to apply before mining.",
    )
    parser.add_argument(
        "--retrieval-run-id",
        required=True,
        help="Retrieval build run id produced by build_retrieval_stack.py.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit queryless mining run id.",
    )
    parser.add_argument(
        "--retrieval-version",
        default=DEFAULT_RETRIEVAL_VERSION,
        help="Retrieval contract version to read.",
    )
    parser.add_argument(
        "--mining-version",
        default=DEFAULT_MINING_VERSION,
        help="Queryless mining contract version to persist.",
    )
    parser.add_argument(
        "--top-k-per-mode",
        type=int,
        default=DEFAULT_TOP_K_PER_MODE,
        help="Max hits to persist per source mechanism and mining mode.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


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


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))


def ensure_run(connection, run_id: str | None, retrieval_run_id: str, args):
    resolved_run_id = run_id or (
        f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    config = {
        "retrieval_run_id": retrieval_run_id,
        "retrieval_version": args.retrieval_version,
        "mining_version": args.mining_version,
        "top_k_per_mode": args.top_k_per_mode,
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
                args.mining_version,
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
                args.mining_version,
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
            "mechanism_instance_id": row["mechanism_instance_id"],
            "paper_id": row["paper_id"],
            "mechanism_summary_text": row["mechanism_summary_text"],
            "causal_chain_text": row["causal_chain_text"],
            "transfer_rationale_text": row["transfer_rationale_text"],
            "fingerprint_text": row["fingerprint_text"],
            "sparse_document_text": row["sparse_document_text"],
            "evidence_text": row["evidence_text"],
            "source_json": source_json,
            "literature_family": source_json.get("literature_family", "unknown"),
            "evaluation_split": source_json.get("evaluation_split", "unknown"),
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
        """
        ,
        (retrieval_run_id, retrieval_version),
    ).fetchall()
    graph = defaultdict(dict)
    for source_id, target_id, edge_weight in rows:
        graph[source_id][target_id] = edge_weight
    return graph


def build_sparse_stats(documents):
    doc_tokens = {}
    document_frequency = Counter()
    for mechanism_id, document in documents.items():
        tokens = tokenize(document["sparse_document_text"])
        token_set = set(tokens)
        doc_tokens[mechanism_id] = token_set
        for token in token_set:
            document_frequency[token] += 1
    return doc_tokens, document_frequency


def keyword_overlap_ratio(source_tokens, candidate_tokens):
    return jaccard(source_tokens, candidate_tokens)


def inverse_document_frequency_mean(overlap_tokens, document_frequency, corpus_size):
    if not overlap_tokens:
        return 0.0
    values = []
    for token in overlap_tokens:
        values.append(math.log((corpus_size + 1.0) / (document_frequency[token] + 1.0)) + 1.0)
    max_idf = math.log((corpus_size + 1.0) / 2.0) + 1.0 if corpus_size > 1 else 1.0
    return min((sum(values) / len(values)) / max_idf, 1.0)


def trait_score(doc, trait_name):
    traits = doc["source_json"].get("mechanism_traits", {})
    return TRAIT_SCORE.get(traits.get(trait_name, "unknown"), 0.35)


def blocker_penalty(doc):
    source_json = doc["source_json"]
    blockers = len(source_json.get("fingerprint_facets", {}).get("portability_blockers", []))
    ambiguity = len(source_json.get("fingerprint_facets", {}).get("ambiguity_flags", []))
    fragility = len(source_json.get("fragility_flags", []))
    failures = len(source_json.get("failure_regimes", []))
    assumptions = len(source_json.get("assumption_violations", []))
    capacity = len(source_json.get("capacity_constraints", []))
    raw_penalty = (
        0.22 * min(blockers / 4.0, 1.0)
        + 0.18 * min(ambiguity / 3.0, 1.0)
        + 0.20 * min(fragility / 4.0, 1.0)
        + 0.16 * min(failures / 4.0, 1.0)
        + 0.12 * min(assumptions / 4.0, 1.0)
        + 0.12 * min(capacity / 4.0, 1.0)
    )
    return min(raw_penalty, 1.0)


def graph_score(source_id, candidate_id, graph):
    outgoing = graph.get(source_id, {})
    if not outgoing:
        return 0.0
    max_weight = max(outgoing.values())
    if max_weight == 0:
        return 0.0
    return outgoing.get(candidate_id, 0.0) / max_weight


def section_overlap(source_doc, candidate_doc):
    return jaccard(
        source_doc["source_json"].get("section_labels", []),
        candidate_doc["source_json"].get("section_labels", []),
    )


def fingerprint_overlap(source_doc, candidate_doc):
    source_facets = source_doc["source_json"].get("fingerprint_facets", {})
    candidate_facets = candidate_doc["source_json"].get("fingerprint_facets", {})
    field_weights = {
        "trigger": 0.16,
        "state_variables": 0.12,
        "actor_structure": 0.12,
        "market_topology": 0.16,
        "pricing_path": 0.12,
        "execution_shape": 0.12,
        "liquidity_regime": 0.08,
        "capacity_limit": 0.04,
        "boundary_conditions": 0.08,
    }
    score = 0.0
    overlaps = {}
    for field_name in FINGERPRINT_FIELDS:
        overlap = jaccard(
            source_facets.get(field_name, []), candidate_facets.get(field_name, [])
        )
        overlaps[field_name] = overlap
        score += field_weights[field_name] * overlap
    return min(score, 1.0), overlaps


def structural_similarity(source_id, candidate_id, source_doc, candidate_doc, embeddings, graph):
    fingerprint_score, facet_overlaps = fingerprint_overlap(source_doc, candidate_doc)
    causal_chain_score = cosine(
        embeddings[source_id].get("causal_chain", []),
        embeddings[candidate_id].get("causal_chain", []),
    )
    summary_score = cosine(
        embeddings[source_id].get("mechanism_summary", []),
        embeddings[candidate_id].get("mechanism_summary", []),
    )
    graph_link_score = graph_score(source_id, candidate_id, graph)
    section_score = section_overlap(source_doc, candidate_doc)
    # @context decision -- C11 uses a blended structural score rather than a
    # single dense view because the commit's job is queryless discovery across
    # jargon boundaries. Fingerprint overlap keeps mechanism identity anchored,
    # dense summaries smooth extraction wording noise, and graph edges rescue
    # benchmark-supported bridges that sparse text would miss.
    score = (
        0.38 * fingerprint_score
        + 0.22 * max(causal_chain_score, 0.0)
        + 0.18 * max(summary_score, 0.0)
        + 0.14 * graph_link_score
        + 0.08 * section_score
    )
    return min(max(score, 0.0), 1.0), {
        "fingerprint_score": fingerprint_score,
        "causal_chain_score": causal_chain_score,
        "summary_score": summary_score,
        "graph_score": graph_link_score,
        "section_score": section_score,
        "facet_overlaps": facet_overlaps,
    }


def lexical_distance_realism(
    source_id,
    candidate_id,
    source_doc,
    candidate_doc,
    embeddings,
    source_tokens,
    candidate_tokens,
    document_frequency,
    corpus_size,
):
    overlap_tokens = sorted(source_tokens & candidate_tokens)
    keyword_overlap = keyword_overlap_ratio(source_tokens, candidate_tokens)
    rarity_score = inverse_document_frequency_mean(overlap_tokens, document_frequency, corpus_size)
    summary_similarity = max(
        cosine(
            embeddings[source_id].get("mechanism_summary", []),
            embeddings[candidate_id].get("mechanism_summary", []),
        ),
        0.0,
    )
    transfer_similarity = max(
        cosine(
            embeddings[source_id].get("transfer_rationale", []),
            embeddings[candidate_id].get("transfer_rationale", []),
        ),
        0.0,
    )
    evidence_anchor = 1.0 if source_doc["evidence_text"] and candidate_doc["evidence_text"] else 0.0
    lexical_gap = 1.0 - min(keyword_overlap, 1.0)
    realism = (
        0.46 * lexical_gap
        + 0.18 * rarity_score
        + 0.16 * summary_similarity
        + 0.10 * transfer_similarity
        + 0.10 * evidence_anchor
    )
    return min(max(realism, 0.0), 1.0), {
        "keyword_overlap": keyword_overlap,
        "overlap_token_count": len(overlap_tokens),
        "rarity_score": rarity_score,
        "summary_similarity": summary_similarity,
        "transfer_similarity": transfer_similarity,
        "evidence_anchor": evidence_anchor,
        "overlap_tokens_sample": overlap_tokens[:12],
    }


def transfer_plausibility(source_doc, candidate_doc):
    source_followup = source_doc["source_json"].get("worth_followup_score", 0.0)
    candidate_followup = candidate_doc["source_json"].get("worth_followup_score", 0.0)
    source_underexploited = source_doc["source_json"].get("underexploited_score", 0.0)
    candidate_underexploited = candidate_doc["source_json"].get("underexploited_score", 0.0)
    evidence_score = avg(
        [
            EVIDENCE_SCORE.get(
                source_doc["source_json"].get("evidence_confidence", "unscored"), 0.45
            ),
            EVIDENCE_SCORE.get(
                candidate_doc["source_json"].get("evidence_confidence", "unscored"), 0.45
            ),
        ]
    )
    tradecore_alignment = avg(
        [trait_score(source_doc, "tradecore_fit"), trait_score(candidate_doc, "tradecore_fit")]
    )
    portability_alignment = avg(
        [
            trait_score(source_doc, "prediction_market_portability"),
            trait_score(candidate_doc, "prediction_market_portability"),
            trait_score(source_doc, "novel_market_portability"),
            trait_score(candidate_doc, "novel_market_portability"),
        ]
    )
    cross_family_bonus = (
        1.0 if source_doc["literature_family"] != candidate_doc["literature_family"] else 0.0
    )
    crowding_relief = 1.0 - trait_score(candidate_doc, "likely_crowding")
    score = (
        0.22 * avg([source_followup, candidate_followup])
        + 0.16 * avg([source_underexploited, candidate_underexploited])
        + 0.22 * tradecore_alignment
        + 0.16 * portability_alignment
        + 0.12 * evidence_score
        + 0.06 * cross_family_bonus
        + 0.06 * crowding_relief
    )
    return min(max(score, 0.0), 1.0), {
        "source_worth_followup_score": source_followup,
        "candidate_worth_followup_score": candidate_followup,
        "source_underexploited_score": source_underexploited,
        "candidate_underexploited_score": candidate_underexploited,
        "tradecore_alignment": tradecore_alignment,
        "portability_alignment": portability_alignment,
        "evidence_score": evidence_score,
        "cross_family_bonus": cross_family_bonus,
        "crowding_relief": crowding_relief,
    }


def contradiction_signal(source_doc, candidate_doc):
    source_traits = source_doc["source_json"].get("mechanism_traits", {})
    candidate_traits = candidate_doc["source_json"].get("mechanism_traits", {})
    disagreements = []
    for field_name in (
        "tradecore_fit",
        "prediction_market_portability",
        "novel_market_portability",
    ):
        left = source_traits.get(field_name, "unknown")
        right = candidate_traits.get(field_name, "unknown")
        if left != "unknown" and right != "unknown" and left != right:
            disagreements.append(field_name)
    source_negative = (
        len(source_doc["source_json"].get("failure_regimes", []))
        + len(source_doc["source_json"].get("fragility_flags", []))
    )
    candidate_negative = (
        len(candidate_doc["source_json"].get("failure_regimes", []))
        + len(candidate_doc["source_json"].get("fragility_flags", []))
    )
    negative_gap = abs(source_negative - candidate_negative)
    score = min(0.55 * min(len(disagreements) / 3.0, 1.0) + 0.45 * min(negative_gap / 4.0, 1.0), 1.0)
    return score, {
        "trait_disagreements": disagreements,
        "negative_signal_gap": negative_gap,
    }


def rarity_signal(doc):
    fingerprint_facets = doc["source_json"].get("fingerprint_facets", {})
    populated_fields = sum(1 for field_name in FINGERPRINT_FIELDS if fingerprint_facets.get(field_name))
    underexploited = doc["source_json"].get("underexploited_score", 0.0)
    tradecore = trait_score(doc, "tradecore_fit")
    return min(0.45 * underexploited + 0.35 * tradecore + 0.20 * min(populated_fields / 6.0, 1.0), 1.0), {
        "underexploited_score": underexploited,
        "tradecore_fit_score": tradecore,
        "populated_fingerprint_fields": populated_fields,
    }


def build_mode_scores(
    structural_score,
    lexical_score,
    transfer_score,
    blocker_penalty_score,
    source_doc,
    candidate_doc,
    contradiction_score,
    rarity_score,
):
    is_cross_family = source_doc["literature_family"] != candidate_doc["literature_family"]
    source_holdout = source_doc["evaluation_split"] == "holdout"
    candidate_holdout = candidate_doc["evaluation_split"] == "holdout"
    source_tradecore = trait_score(source_doc, "tradecore_fit")
    candidate_tradecore = trait_score(candidate_doc, "tradecore_fit")
    scores = {
        "structural_near_lexical_far": (
            0.40 * structural_score
            + 0.33 * lexical_score
            + 0.19 * transfer_score
            - 0.22 * blocker_penalty_score
            + 0.08 * (1.0 if is_cross_family else 0.0)
        ),
        "tradecore_near_jargon_far": (
            0.28 * structural_score
            + 0.24 * lexical_score
            + 0.30 * avg([source_tradecore, candidate_tradecore])
            + 0.18 * transfer_score
            - 0.20 * blocker_penalty_score
        ),
        "bridge_mechanisms_across_families": (
            0.36 * structural_score
            + 0.18 * lexical_score
            + 0.20 * transfer_score
            + 0.16 * (1.0 if is_cross_family else 0.0)
            + 0.10 * candidate_doc["source_json"].get("underexploited_score", 0.0)
            - 0.18 * blocker_penalty_score
        ),
        "zero_seed_vocabulary_holdouts": (
            0.25 * structural_score
            + 0.35 * lexical_score
            + 0.18 * transfer_score
            + 0.16 * (1.0 if (source_holdout or candidate_holdout) else 0.0)
            + 0.10 * candidate_doc["source_json"].get("underexploited_score", 0.0)
            - 0.16 * blocker_penalty_score
        ),
        "contradiction_mining": (
            0.30 * structural_score
            + 0.12 * lexical_score
            + 0.18 * contradiction_score
            + 0.10 * transfer_score
            + 0.12 * candidate_doc["source_json"].get("worth_followup_score", 0.0)
            - 0.08 * blocker_penalty_score
        ),
        "rare_fingerprint_combinations_with_high_fit": (
            0.24 * structural_score
            + 0.10 * lexical_score
            + 0.26 * transfer_score
            + 0.28 * rarity_score
            + 0.08 * candidate_doc["source_json"].get("underexploited_score", 0.0)
            - 0.14 * blocker_penalty_score
        ),
    }
    return {mode: max(score, 0.0) for mode, score in scores.items()}


def build_hits(documents, embeddings, graph, top_k_per_mode):
    doc_tokens, document_frequency = build_sparse_stats(documents)
    corpus_size = max(len(documents), 1)
    hits_by_mode_and_source = defaultdict(list)

    for source_id, source_doc in documents.items():
        source_tokens = doc_tokens[source_id]
        for candidate_id, candidate_doc in documents.items():
            if candidate_id == source_id:
                continue
            candidate_tokens = doc_tokens[candidate_id]
            structural_score, structural_support = structural_similarity(
                source_id, candidate_id, source_doc, candidate_doc, embeddings, graph
            )
            lexical_score, lexical_support = lexical_distance_realism(
                source_id,
                candidate_id,
                source_doc,
                candidate_doc,
                embeddings,
                source_tokens,
                candidate_tokens,
                document_frequency,
                corpus_size,
            )
            transfer_score, transfer_support = transfer_plausibility(source_doc, candidate_doc)
            blocker_penalty_score = avg(
                [blocker_penalty(source_doc), blocker_penalty(candidate_doc)]
            )
            contradiction_score, contradiction_support = contradiction_signal(
                source_doc, candidate_doc
            )
            rarity_score, rarity_support = rarity_signal(candidate_doc)
            mode_scores = build_mode_scores(
                structural_score,
                lexical_score,
                transfer_score,
                blocker_penalty_score,
                source_doc,
                candidate_doc,
                contradiction_score,
                rarity_score,
            )

            support = {
                "source_section_labels": source_doc["source_json"].get("section_labels", []),
                "candidate_section_labels": candidate_doc["source_json"].get("section_labels", []),
                "source_traits": source_doc["source_json"].get("mechanism_traits", {}),
                "candidate_traits": candidate_doc["source_json"].get("mechanism_traits", {}),
                "source_blockers": source_doc["source_json"].get("fingerprint_facets", {}).get(
                    "portability_blockers", []
                ),
                "candidate_blockers": candidate_doc["source_json"].get("fingerprint_facets", {}).get(
                    "portability_blockers", []
                ),
                "structural_support": structural_support,
                "lexical_support": lexical_support,
                "transfer_support": transfer_support,
                "contradiction_support": contradiction_support,
                "rarity_support": rarity_support,
                "source_evidence_excerpt": normalize_text(source_doc["evidence_text"])[:280],
                "candidate_evidence_excerpt": normalize_text(candidate_doc["evidence_text"])[:280],
            }
            hit = {
                "source_mechanism_instance_id": source_id,
                "candidate_mechanism_instance_id": candidate_id,
                "source_paper_id": source_doc["paper_id"],
                "candidate_paper_id": candidate_doc["paper_id"],
                "source_literature_family": source_doc["literature_family"],
                "candidate_literature_family": candidate_doc["literature_family"],
                "source_evaluation_split": source_doc["evaluation_split"],
                "candidate_evaluation_split": candidate_doc["evaluation_split"],
                "is_cross_family": 1
                if source_doc["literature_family"] != candidate_doc["literature_family"]
                else 0,
                "structural_similarity_score": structural_score,
                "lexical_distance_score": lexical_score,
                "transfer_plausibility_score": transfer_score,
                "blocker_penalty_score": blocker_penalty_score,
                "mode_scores": mode_scores,
                "support": support,
            }
            for mode_name, reranker_score in mode_scores.items():
                if reranker_score <= 0.0:
                    continue
                hits_by_mode_and_source[(mode_name, source_id)].append(
                    {
                        **hit,
                        "mining_mode": mode_name,
                        "reranker_score": reranker_score,
                    }
                )

    persisted_hits = []
    for (mode_name, source_id), mode_hits in hits_by_mode_and_source.items():
        ranked_hits = sorted(
            mode_hits,
            key=lambda item: (
                -item["reranker_score"],
                -item["structural_similarity_score"],
                -item["transfer_plausibility_score"],
                item["candidate_mechanism_instance_id"],
            ),
        )[:top_k_per_mode]
        for rank, hit in enumerate(ranked_hits, start=1):
            persisted_hits.append(
                {
                    **hit,
                    "rank_within_source": rank,
                    "source_mechanism_instance_id": source_id,
                    "mining_mode": mode_name,
                }
            )
    return persisted_hits


def persist_hits(connection, hits, run_id: str, retrieval_run_id: str, retrieval_version: str, mining_version: str):
    for hit in hits:
        rationale = {
            **hit["support"],
            "mode_score_breakdown": hit["mode_scores"],
        }
        connection.execute(
            """
            INSERT INTO queryless_candidate_hits (
              source_mechanism_instance_id,
              candidate_mechanism_instance_id,
              source_paper_id,
              candidate_paper_id,
              run_id,
              retrieval_run_id,
              retrieval_version,
              mining_version,
              mining_mode,
              source_literature_family,
              candidate_literature_family,
              source_evaluation_split,
              candidate_evaluation_split,
              rank_within_source,
              is_cross_family,
              structural_similarity_score,
              lexical_distance_score,
              transfer_plausibility_score,
              blocker_penalty_score,
              reranker_score,
              rationale_json,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_mechanism_instance_id, candidate_mechanism_instance_id, run_id, mining_version, mining_mode)
            DO UPDATE SET
              source_paper_id = excluded.source_paper_id,
              candidate_paper_id = excluded.candidate_paper_id,
              retrieval_run_id = excluded.retrieval_run_id,
              retrieval_version = excluded.retrieval_version,
              source_literature_family = excluded.source_literature_family,
              candidate_literature_family = excluded.candidate_literature_family,
              source_evaluation_split = excluded.source_evaluation_split,
              candidate_evaluation_split = excluded.candidate_evaluation_split,
              rank_within_source = excluded.rank_within_source,
              is_cross_family = excluded.is_cross_family,
              structural_similarity_score = excluded.structural_similarity_score,
              lexical_distance_score = excluded.lexical_distance_score,
              transfer_plausibility_score = excluded.transfer_plausibility_score,
              blocker_penalty_score = excluded.blocker_penalty_score,
              reranker_score = excluded.reranker_score,
              rationale_json = excluded.rationale_json,
              updated_at = excluded.updated_at
            """,
            (
                hit["source_mechanism_instance_id"],
                hit["candidate_mechanism_instance_id"],
                hit["source_paper_id"],
                hit["candidate_paper_id"],
                run_id,
                retrieval_run_id,
                retrieval_version,
                mining_version,
                hit["mining_mode"],
                hit["source_literature_family"],
                hit["candidate_literature_family"],
                hit["source_evaluation_split"],
                hit["candidate_evaluation_split"],
                hit["rank_within_source"],
                hit["is_cross_family"],
                hit["structural_similarity_score"],
                hit["lexical_distance_score"],
                hit["transfer_plausibility_score"],
                hit["blocker_penalty_score"],
                hit["reranker_score"],
                json.dumps(rationale, sort_keys=True),
                now_utc(),
            ),
        )


def summarize(hits, run_id: str, retrieval_run_id: str, retrieval_version: str, mining_version: str):
    by_mode = defaultdict(list)
    holdout_hits = 0
    cross_family_hits = 0
    for hit in hits:
        by_mode[hit["mining_mode"]].append(hit)
        if hit["candidate_evaluation_split"] == "holdout":
            holdout_hits += 1
        if hit["is_cross_family"]:
            cross_family_hits += 1
    mode_summary = {}
    for mode_name, mode_hits in by_mode.items():
        mode_summary[mode_name] = {
            "hit_count": len(mode_hits),
            "mean_reranker_score": avg(hit["reranker_score"] for hit in mode_hits),
            "mean_structural_similarity_score": avg(
                hit["structural_similarity_score"] for hit in mode_hits
            ),
            "mean_lexical_distance_score": avg(
                hit["lexical_distance_score"] for hit in mode_hits
            ),
            "mean_transfer_plausibility_score": avg(
                hit["transfer_plausibility_score"] for hit in mode_hits
            ),
            "mean_blocker_penalty_score": avg(
                hit["blocker_penalty_score"] for hit in mode_hits
            ),
        }
    return {
        "run_id": run_id,
        "retrieval_run_id": retrieval_run_id,
        "retrieval_version": retrieval_version,
        "mining_version": mining_version,
        "mode_summary": mode_summary,
        "queryless_hit_count": len(hits),
        "cross_family_hit_count": cross_family_hits,
        "holdout_hit_count": holdout_hits,
    }


def write_summary(run_id: str, summary):
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "queryless_mining_summary.json"
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
        run_id = ensure_run(connection, args.run_id, args.retrieval_run_id, args)
        connection.commit()

        documents = load_documents(connection, args.retrieval_run_id, args.retrieval_version)
        embeddings = load_dense_embeddings(
            connection, args.retrieval_run_id, args.retrieval_version
        )
        graph = load_graph_edges(connection, args.retrieval_run_id, args.retrieval_version)
        if not documents or not embeddings:
            raise SystemExit(
                "retrieval documents or dense embeddings are missing; build C10 surfaces before running C11 mining"
            )

        hits = build_hits(documents, embeddings, graph, args.top_k_per_mode)

        connection.execute("BEGIN")
        try:
            persist_hits(
                connection,
                hits,
                run_id,
                args.retrieval_run_id,
                args.retrieval_version,
                args.mining_version,
            )
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

    summary = summarize(
        hits,
        run_id,
        args.retrieval_run_id,
        args.retrieval_version,
        args.mining_version,
    )
    summary_path = write_summary(run_id, summary)
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
