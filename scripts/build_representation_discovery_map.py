#!/usr/bin/env python3

import argparse
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from materialize_text_views import build_section_derived_views
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from sqlite_vec_adapter import (
    connect as connect_vec_store,
    ensure_schema as ensure_vec_schema,
    ensure_vec_table,
    insert_text_views,
    query_knn,
    stable_short_id,
    upsert_embedding_space,
    write_embeddings,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_EMBEDDING_SPACES_PATH = ROOT / "configs" / "embedding_spaces.yaml"
DEFAULT_PROBES_PATH = ROOT / "configs" / "probes.yaml"

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_/-]{2,}")
STOPWORDS = {
    "using",
    "study",
    "paper",
    "model",
    "models",
    "market",
    "markets",
    "financial",
    "data",
    "analysis",
    "based",
    "evidence",
    "dynamic",
    "dynamics",
    "empirical",
    "theory",
    "results",
    "approach",
    "method",
    "methods",
    "risk",
    "trading",
    "price",
    "prices",
    "order",
    "orders",
}
STOPWORDS |= set(ENGLISH_STOP_WORDS)

POSITIVE_ANCHORS = {
    "parity_propagation": {
        "paper_ids": ["2002.02583", "0812.0913", "1902.04690", "1803.09432"],
        "keywords": [
            "triangular arbitrage",
            "cross-currency",
            "lead-lag",
            "fragmentation",
            "parity",
            "cross-market",
            "currency peg",
        ],
        "min_keyword_hits": 2,
        "allowed_categories": ["q-fin", "econ", "physics", "cond-mat"],
        "why": "Repeated positive anchor around linked-market parity, propagation, and fragmentation.",
    },
    "queue_value_passive_quoting": {
        "paper_ids": ["2502.18625", "2206.05410", "0711.3581"],
        "keywords": [
            "fill probability",
            "post-fill",
            "market maker",
            "queue",
            "passive quoting",
            "inventory risk",
            "liquidity provider",
            "maker-taker",
        ],
        "min_keyword_hits": 2,
        "allowed_categories": ["q-fin", "econ", "physics", "cond-mat"],
        "why": "Cleanest recurring microstructure anchor around fill-quality, queue, and quoting behavior.",
    },
    "refill_lag_local_shock": {
        "paper_ids": ["0901.0495", "physics/0608032", "0711.3581"],
        "keywords": [
            "large price changes",
            "liquidity crises",
            "order book",
            "market impact",
            "limit order book",
            "gaps in the book",
            "extreme price changes",
        ],
        "min_keyword_hits": 2,
        "allowed_categories": ["q-fin", "physics", "cond-mat"],
        "why": "Recurring local-shock / refill-lag motif from prior passes.",
    },
    "maker_stress_inventory_retreat": {
        "paper_ids": ["2206.05410", "2505.07761", "2008.00470"],
        "keywords": [
            "inventory management",
            "inventory risk",
            "defending a currency peg",
            "market makers",
            "inventory accumulation",
            "liquidity provision",
            "impermanent loss",
        ],
        "min_keyword_hits": 2,
        "allowed_categories": ["q-fin", "econ", "physics"],
        "why": "Prior positive anchor for maker-stress and inventory retreat dynamics.",
    },
    "amm_settlement_latency": {
        "paper_ids": ["2205.14699"],
        "keywords": [
            "decentralized finance",
            "defi",
            "automated market maker",
            "constant function market maker",
            "amm",
            "liquidity pool",
            "uniswap",
            "sushiswap",
            "stablecoin",
            "settlement",
            "blockchain",
            "bridge",
            "cross-chain",
            "mev",
            "liquid staking",
        ],
        "min_keyword_hits": 2,
        "allowed_categories": ["q-fin", "cs", "econ", "eess"],
        "why": "Likely non-q-fin seam for settlement latency and design-induced games.",
    },
    "auction_parimutuel_design": {
        "paper_ids": ["0902.2429", "0905.0582", "nlin/0102016", "0905.4171"],
        "keywords": [
            "pari-mutuel",
            "auction",
            "prediction market",
            "call auction",
            "bid distributions",
            "contingent claim",
            "order matching",
            "parlay",
        ],
        "min_keyword_hits": 2,
        "allowed_categories": ["q-fin", "econ", "cs", "nlin", "physics"],
        "why": "Anchor for allocation, event-market design, and contingent-claim structure.",
    },
}

# @context decision -- The current family/ranking stack collapses too much of the corpus into
# `research-dead-end-worth-excluding`. The representation-first reset uses those repeated failure
# surfaces only as negative anchors, never as the main neighborhood structure, so discovery is not
# trapped inside the old suppression ontology.
NEGATIVE_PATTERNS = [
    "research-dead-end-worth-excluding",
    "paper_describes_general_market_property_only",
    "paper_describes_theory_without_tradeable_monitorable_implication",
    "no_edge_hypothesis",
]


@dataclass
class ProbeConfig:
    name: str
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    lexical_far_from: tuple[str, ...] = ()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a representation-first discovery map over the current corpus."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="representation-discovery-qfin-full")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--embedding-spaces-path", default=str(DEFAULT_EMBEDDING_SPACES_PATH))
    parser.add_argument("--probes-path", default=str(DEFAULT_PROBES_PATH))
    parser.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--embed-batch-size", type=int, default=128)
    parser.add_argument("--cluster-count", type=int, default=48)
    parser.add_argument("--cluster-count-small", type=int, default=18)
    parser.add_argument("--cluster-count-large", type=int, default=96)
    parser.add_argument("--svd-components", type=int, default=96)
    parser.add_argument("--top-clusters", type=int, default=18)
    parser.add_argument("--top-neighbors", type=int, default=12)
    parser.add_argument("--top-contrastive", type=int, default=10)
    parser.add_argument("--top-composition", type=int, default=8)
    parser.add_argument("--shortlist-size", type=int, default=30)
    return parser.parse_args()


def tokenize(text: str):
    return [token.lower() for token in TOKEN_RE.findall(text or "")]


def lexical_distance(anchor_tokens: set[str], doc_text: str):
    if not anchor_tokens:
        return 1.0
    doc_tokens = set(tokenize(doc_text))
    if not doc_tokens:
        return 1.0
    overlap = len(anchor_tokens & doc_tokens) / max(1, len(anchor_tokens))
    return 1.0 - overlap


def normalize_text(text: str):
    return " ".join((text or "").split())


def top_terms(texts: list[str], limit: int = 10):
    counts = Counter()
    for text in texts:
        counts.update(token for token in tokenize(text) if token not in STOPWORDS)
    return [term for term, _ in counts.most_common(limit)]


def keyword_hit_count(text: str, keywords: list[str]):
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def cosine_matrix(query_vectors, matrix):
    sims = cosine_similarity(query_vectors, matrix)
    return sims if sims.ndim > 1 else sims.reshape(1, -1)


def mean_vector(matrix, indices):
    if not indices:
        return None
    vector = np.asarray(matrix[indices].mean(axis=0)).reshape(1, -1)
    return normalize(vector)


def explain_region_type(mean_negative: float, anchor_count: int, lexical_far_share: float):
    if anchor_count >= 2 and lexical_far_share >= 0.5 and mean_negative < 0.25:
        return "compositional_region"
    if mean_negative >= 0.45:
        return "dead_region"
    if lexical_far_share >= 0.6:
        return "likely_game_region"
    return "under_specified_region"


def load_corpus(connection):
    paper_rows = connection.execute(
        """
        SELECT
          paper_id,
          title,
          abstract,
          primary_category,
          literature_family,
          evaluation_split,
          ingest_status,
          published_at
        FROM papers
        WHERE abstract IS NOT NULL
          AND trim(abstract) != ''
        ORDER BY paper_id
        """
    ).fetchall()

    section_rows = connection.execute(
        """
        SELECT
          paper_id,
          section_label,
          section_order,
          content_text
        FROM paper_sections
        ORDER BY paper_id, section_order
        """
    ).fetchall()

    # @context decision -- Family membership is treated as a weak label only. The current family
    # surface is useful for anchor priors and bridge hints, but strong enough only to bias
    # exploration lightly; using it as the map itself would recreate the current collapse.
    weak_label_rows = connection.execute(
        """
        SELECT
          mi.paper_id,
          cf.family_name,
          COUNT(*) AS hits
        FROM mechanism_instances mi
        JOIN candidate_family_members cfm
          ON cfm.candidate_mechanism_instance_id = mi.mechanism_instance_id
        JOIN candidate_families cf
          ON cf.candidate_family_id = cfm.candidate_family_id
        GROUP BY mi.paper_id, cf.family_name
        """
    ).fetchall()

    negative_rows = connection.execute(
        """
        SELECT DISTINCT mi.paper_id, cf.family_name
        FROM mechanism_instances mi
        JOIN candidate_family_members cfm
          ON cfm.candidate_mechanism_instance_id = mi.mechanism_instance_id
        JOIN candidate_families cf
          ON cf.candidate_family_id = cfm.candidate_family_id
        WHERE lower(cf.family_name) LIKE '%research-dead-end-worth-excluding%'
        """
    ).fetchall()

    section_map = defaultdict(list)
    for row in section_rows:
        label = normalize_text(row["section_label"])
        text = normalize_text(row["content_text"])
        if not text:
            continue
        section_map[row["paper_id"]].append(
            {
                "label": label,
                "order": row["section_order"],
                "text": text[:1400],
            }
        )

    weak_label_map = defaultdict(list)
    for row in weak_label_rows:
        weak_label_map[row["paper_id"]].append(
            {
                "family_name": row["family_name"],
                "hits": row["hits"],
            }
        )
    for paper_id in weak_label_map:
        weak_label_map[paper_id].sort(key=lambda item: (-item["hits"], item["family_name"]))

    negative_seed_papers = {row["paper_id"] for row in negative_rows}
    corpus = []
    for row in paper_rows:
        paper_id = row["paper_id"]
        sections = section_map.get(paper_id, [])
        top_sections = sections[:4]
        weak_labels = weak_label_map.get(paper_id, [])[:3]
        section_text = "\n".join(f"[{item['label']}] {item['text']}" for item in top_sections)
        weak_label_text = ", ".join(item["family_name"] for item in weak_labels)
        title = normalize_text(row["title"])
        abstract = normalize_text(row["abstract"])
        meta_view = normalize_text(
            " | ".join(
                [
                    title,
                    abstract,
                    row["primary_category"] or "",
                    row["literature_family"] or "",
                    row["evaluation_split"] or "",
                    weak_label_text,
                ]
            )
        )
        corpus.append(
            {
                "paper_id": paper_id,
                "title": title,
                "abstract": abstract,
                "primary_category": row["primary_category"] or "",
                "literature_family": row["literature_family"] or "",
                "evaluation_split": row["evaluation_split"] or "",
                "ingest_status": row["ingest_status"] or "",
                "published_at": row["published_at"] or "",
                "section_snippets": top_sections,
                "section_view": section_text,
                "weak_labels": weak_labels,
                "weak_label_text": weak_label_text,
                "abstract_view": normalize_text(f"{title}\n{abstract}"),
                "metadata_view": meta_view,
                "negative_anchor_seed": paper_id in negative_seed_papers,
            }
        )
    return corpus


def load_yaml_config(path: Path, default):
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sha256_text(text: str):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def build_text_views(corpus):
    view_rows = []
    next_view_id = 1
    for row in corpus:
        title = row["title"]
        abstract = row["abstract"]
        categories = " ".join(
            filter(None, [row["primary_category"], row["literature_family"], row["evaluation_split"]])
        )
        section_text = row["section_view"] if row["section_view"] else ""
        section_views = build_section_derived_views(row.get("section_snippets", []))
        raw_views = {
            "title_abs": normalize_text(f"{title}\n{abstract}"),
            "abs_only": abstract,
            "title_abs_cats": normalize_text(f"{title}\n{abstract}\n{categories}"),
            "title_only": title,
            "category_string": categories,
            "section_or_abs": normalize_text(f"{title}\n{section_text or abstract}"),
            **section_views,
        }
        for view_type, text in raw_views.items():
            text = normalize_text(text)
            view_rows.append(
                {
                    "view_id": next_view_id,
                    "paper_id": row["paper_id"],
                    "view_type": view_type,
                    "text": text,
                    "token_estimate": len(tokenize(text)),
                    "text_sha256": sha256_text(text),
                }
            )
            next_view_id += 1
    return view_rows


def build_representation(corpus, output_dir: Path, embedding_spaces_path: Path, embedding_model: str, embed_batch_size: int):
    from sentence_transformers import SentenceTransformer

    view_rows = build_text_views(corpus)
    run_db_path = output_dir / "discovery.sqlite3"
    if run_db_path.exists():
        run_db_path.unlink()
    vec_connection = connect_vec_store(run_db_path)
    ensure_vec_schema(vec_connection)
    insert_text_views(vec_connection, view_rows)

    default_spaces = {
        "spaces": [
            {
                "name": "s1_surprise_sections_main",
                "view_type": "surprise_sections",
                "weight": 0.40,
                "prompt_style": "surprise_sections",
            },
            {
                "name": "s2_mechanism_sections_main",
                "view_type": "mechanism_sections",
                "weight": 0.30,
                "prompt_style": "mechanism_sections",
            },
            {
                "name": "s3_regime_sections_main",
                "view_type": "regime_sections",
                "weight": 0.20,
                "prompt_style": "regime_sections",
            },
            {
                "name": "s4_all_sections_main",
                "view_type": "all_sections",
                "weight": 0.10,
                "prompt_style": "all_sections",
            },
        ]
    }
    space_config = load_yaml_config(embedding_spaces_path, default_spaces)
    spaces = space_config.get("spaces", default_spaces["spaces"])

    model = SentenceTransformer(embedding_model)
    paper_order = [row["paper_id"] for row in corpus]
    matrices_by_space = {}

    for space in spaces:
        rows = [row for row in view_rows if row["view_type"] == space["view_type"]]
        texts = [row["text"] for row in rows]
        vectors = model.encode(
            texts,
            batch_size=embed_batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype(np.float32)
        dims = vectors.shape[1]
        table_name = f"vec_{space['name']}_{dims}".replace("-", "_")
        ensure_vec_table(vec_connection, table_name, dims)
        space_id = upsert_embedding_space(
            vec_connection,
            name=space["name"],
            model_name=embedding_model,
            dims=dims,
            normalized=True,
            prompt_style=space.get("prompt_style", space["view_type"]),
        )
        write_embeddings(
            vec_connection,
            table_name=table_name,
            space_id=space_id,
            view_ids=[row["view_id"] for row in rows],
            vectors=vectors,
            batch_id=space["name"],
        )
        matrices_by_space[space["name"]] = {
            "vectors": vectors,
            "rows": rows,
            "table_name": table_name,
            "weight": float(space.get("weight", 1.0)),
            "dims": dims,
        }

    combined_parts = []
    for space in spaces:
        payload = matrices_by_space[space["name"]]
        combined_parts.append(payload["vectors"] * payload["weight"])
    combined = normalize(np.hstack(combined_parts))

    return {
        "combined": combined,
        "view_rows": view_rows,
        "run_db_path": run_db_path,
        "vec_connection": vec_connection,
        "spaces": spaces,
        "matrices_by_space": matrices_by_space,
        "paper_order": paper_order,
    }


def attach_anchor_seeds(corpus):
    by_paper_id = {row["paper_id"]: idx for idx, row in enumerate(corpus)}
    anchor_indices = {}
    for anchor_name, config in POSITIVE_ANCHORS.items():
        indices = set()
        for paper_id in config["paper_ids"]:
            if paper_id in by_paper_id:
                indices.add(by_paper_id[paper_id])
        keyword_tokens = [token.lower() for token in config["keywords"]]
        for idx, row in enumerate(corpus):
            text = f"{row['title']} {row['abstract']} {row['weak_label_text']}".lower()
            keyword_hits = keyword_hit_count(text, keyword_tokens)
            category_ok = any(
                row["primary_category"].lower().startswith(prefix.lower())
                for prefix in config.get("allowed_categories", [])
            )
            if category_ok and keyword_hits >= config.get("min_keyword_hits", 1):
                indices.add(idx)
        anchor_indices[anchor_name] = sorted(indices)
    negative_indices = []
    for idx, row in enumerate(corpus):
        text = f"{row['title']} {row['abstract']} {row['weak_label_text']}".lower()
        if row["negative_anchor_seed"] or any(pattern in text for pattern in NEGATIVE_PATTERNS):
            negative_indices.append(idx)
    return anchor_indices, sorted(set(negative_indices))


def build_clusters(matrix, cluster_count: int):
    model = MiniBatchKMeans(
        n_clusters=cluster_count,
        random_state=7,
        batch_size=2048,
        n_init="auto",
    )
    labels = model.fit_predict(matrix)
    return labels, model.cluster_centers_


def representative_indices(matrix, indices, center, limit=5):
    if not indices:
        return []
    sims = cosine_similarity(matrix[indices], center.reshape(1, -1)).ravel()
    ranked = sorted(zip(indices, sims), key=lambda item: item[1], reverse=True)
    return [index for index, _ in ranked[:limit]]


def build_cluster_packets(corpus, matrix, labels, centers, top_clusters):
    cluster_to_indices = defaultdict(list)
    for idx, label in enumerate(labels):
        cluster_to_indices[int(label)].append(idx)

    packets = []
    for label, indices in cluster_to_indices.items():
        texts = [corpus[idx]["abstract_view"] for idx in indices]
        reps = representative_indices(matrix, indices, centers[label], limit=4)
        packets.append(
            {
                "cluster_id": int(label),
                "size": len(indices),
                "representative_indices": reps,
                "representative_paper_ids": [corpus[idx]["paper_id"] for idx in reps],
                "top_phrases": top_terms(texts, limit=8),
                "primary_categories": Counter(corpus[idx]["primary_category"] for idx in indices).most_common(4),
                "weak_labels": Counter(
                    family["family_name"]
                    for idx in indices
                    for family in corpus[idx]["weak_labels"][:2]
                ).most_common(6),
                "section_backed_share": round(
                    sum(1 for idx in indices if corpus[idx]["section_snippets"]) / max(1, len(indices)), 3
                ),
                "indices": indices,
            }
        )
    return packets[:top_clusters], cluster_to_indices


def score_anchor_neighborhoods(corpus, matrix, anchor_indices, negative_indices, top_neighbors):
    negative_centroid = mean_vector(matrix, negative_indices)
    anchor_reports = {}
    anchor_centroids = {}
    anchor_token_sets = {}
    for anchor_name, indices in anchor_indices.items():
        centroid = mean_vector(matrix, indices)
        if centroid is None:
            continue
        anchor_centroids[anchor_name] = centroid
        anchor_tokens = set()
        for idx in indices:
            anchor_tokens.update(tokenize(corpus[idx]["title"]))
            anchor_tokens.update(tokenize(corpus[idx]["abstract"]))
        for keyword in POSITIVE_ANCHORS[anchor_name]["keywords"]:
            anchor_tokens.update(tokenize(keyword))
        anchor_token_sets[anchor_name] = anchor_tokens

        sims = cosine_similarity(centroid, matrix).ravel()
        negative_sims = (
            cosine_similarity(negative_centroid, matrix).ravel()
            if negative_centroid is not None
            else np.zeros_like(sims)
        )
        scores = sims - 0.25 * negative_sims
        ranked = np.argsort(scores)[::-1]

        nearest = []
        lexical_far = []
        for idx in ranked:
            row = corpus[idx]
            if idx in indices:
                continue
            entry = {
                "paper_id": row["paper_id"],
                "title": row["title"],
                "score": round(float(scores[idx]), 4),
                "anchor_similarity": round(float(sims[idx]), 4),
                "negative_similarity": round(float(negative_sims[idx]), 4),
                "lexical_distance": round(lexical_distance(anchor_tokens, row["abstract_view"]), 4),
            }
            if len(nearest) < top_neighbors:
                nearest.append(entry)
            if entry["lexical_distance"] >= 0.8 and len(lexical_far) < top_neighbors:
                lexical_far.append(entry)
            if len(nearest) >= top_neighbors and len(lexical_far) >= top_neighbors:
                break

        bridges = []
        others = [name for name in anchor_indices if name != anchor_name and name in anchor_centroids]
        for other_name in others:
            other_sims = cosine_similarity(anchor_centroids[other_name], matrix).ravel()
            bridge_score = np.minimum(sims, other_sims) - 0.20 * negative_sims
            for idx in np.argsort(bridge_score)[::-1]:
                if idx in indices:
                    continue
                bridges.append(
                    {
                        "paper_id": corpus[idx]["paper_id"],
                        "title": corpus[idx]["title"],
                        "other_anchor": other_name,
                        "score": round(float(bridge_score[idx]), 4),
                    }
                )
                if len(bridges) >= top_neighbors:
                    break
            if len(bridges) >= top_neighbors:
                break

        neighborhood = np.argsort(sims)[::-1][: max(top_neighbors * 4, 30)]
        neighborhood = [idx for idx in neighborhood if idx not in indices]
        if neighborhood:
            local_center = mean_vector(matrix, neighborhood)
            local_sims = cosine_similarity(local_center, matrix[neighborhood]).ravel()
            outliers = [
                {
                    "paper_id": corpus[idx]["paper_id"],
                    "title": corpus[idx]["title"],
                    "anchor_similarity": round(float(sims[idx]), 4),
                    "local_fit": round(float(local_sims[pos]), 4),
                }
                for pos, idx in sorted(
                    enumerate(neighborhood),
                    key=lambda item: (local_sims[item[0]], -sims[item[1]]),
                )[:top_neighbors]
            ]
        else:
            outliers = []

        anchor_reports[anchor_name] = {
            "seed_count": len(indices),
            "seed_papers": [corpus[idx]["paper_id"] for idx in indices[:12]],
            "nearest_neighbors": nearest,
            "lexically_far_neighbors": lexical_far,
            "bridge_papers": bridges,
            "outliers": outliers,
        }
    return anchor_reports, anchor_centroids, anchor_token_sets


def rank_clusters_by_interest(cluster_packets, corpus, matrix, anchor_centroids, negative_indices, top_clusters):
    negative_centroid = mean_vector(matrix, negative_indices)
    negative_sims = (
        cosine_similarity(negative_centroid, matrix).ravel()
        if negative_centroid is not None
        else np.zeros(matrix.shape[0])
    )
    positive_sims = []
    for center in anchor_centroids.values():
        positive_sims.append(cosine_similarity(center, matrix).ravel())
    positive_max = np.max(np.vstack(positive_sims), axis=0) if positive_sims else np.zeros(matrix.shape[0])

    ranked_packets = []
    for packet in cluster_packets:
        indices = packet["indices"]
        local_interest = positive_max[indices] - 0.35 * negative_sims[indices]
        scored = dict(packet)
        scored["interesting_score"] = round(
            float(np.mean(np.sort(local_interest)[-max(5, len(indices) // 8) :])),
            4,
        )
        anchor_counts = Counter()
        for idx in indices:
            text = f"{corpus[idx]['title']} {corpus[idx]['abstract']}".lower()
            for anchor_name, config in POSITIVE_ANCHORS.items():
                if keyword_hit_count(text, config["keywords"]) >= config.get("min_keyword_hits", 1):
                    anchor_counts[anchor_name] += 1
        scored["anchor_mix"] = anchor_counts.most_common(4)
        scored.pop("indices", None)
        ranked_packets.append(scored)
    ranked_packets.sort(
        key=lambda item: (item["interesting_score"], math.log(item["size"] + 1)),
        reverse=True,
    )
    return ranked_packets[:top_clusters]


def build_probe_configs(probes_path: Path):
    default = {
        "patterns": [
            {"label": "near parity, far dead-end", "include": ["parity_propagation"], "exclude": ["negative_anchor"]},
            {"label": "near parity and auctions", "include": ["parity_propagation", "auction_parimutuel_design"], "exclude": ["negative_anchor"]},
            {"label": "near parity and settlement", "include": ["parity_propagation", "amm_settlement_latency"], "exclude": ["negative_anchor"]},
            {"label": "near queue-value and auctions", "include": ["queue_value_passive_quoting", "auction_parimutuel_design"], "exclude": ["negative_anchor"]},
            {"label": "near queue-value and settlement", "include": ["queue_value_passive_quoting", "amm_settlement_latency"], "exclude": ["negative_anchor"]},
            {"label": "near refill-lag and maker stress", "include": ["refill_lag_local_shock", "maker_stress_inventory_retreat"], "exclude": ["negative_anchor"]},
            {"label": "near settlement and event design", "include": ["amm_settlement_latency", "auction_parimutuel_design"], "exclude": ["negative_anchor"]},
            {"label": "near maker stress, far dead-end", "include": ["maker_stress_inventory_retreat"], "exclude": ["negative_anchor"]},
            {"label": "near auction design, lexically far", "include": ["auction_parimutuel_design"], "exclude": ["negative_anchor"], "lexical_far_from": ["auction", "pari", "prediction"]},
            {"label": "near settlement, lexically far", "include": ["amm_settlement_latency"], "exclude": ["negative_anchor"], "lexical_far_from": ["defi", "blockchain", "settlement"]},
        ]
    }
    config = load_yaml_config(probes_path, default)
    return [
        ProbeConfig(
            name=item["label"],
            include=tuple(item["include"]),
            exclude=tuple(item.get("exclude", [])),
            lexical_far_from=tuple(item.get("lexical_far_from", [])),
        )
        for item in config.get("patterns", default["patterns"])
    ]


def evaluate_contrastive_regions(corpus, matrix, anchor_centroids, anchor_token_sets, negative_indices, top_regions, probe_configs):
    negative_centroid = mean_vector(matrix, negative_indices)
    negative_sims = (
        cosine_similarity(negative_centroid, matrix).ravel()
        if negative_centroid is not None
        else np.zeros(matrix.shape[0])
    )

    regions = []
    for probe in probe_configs:
        include_centroids = [anchor_centroids[name] for name in probe.include if name in anchor_centroids]
        if not include_centroids:
            continue
        include_sim = np.mean(
            np.vstack([cosine_similarity(center, matrix).ravel() for center in include_centroids]),
            axis=0,
        )
        score = include_sim - 0.25 * negative_sims
        lexical_far_score = np.zeros_like(score)
        if probe.lexical_far_from:
            anchor_tokens = set()
            for text in probe.lexical_far_from:
                anchor_tokens.update(tokenize(text))
            lexical_far_score = np.array(
                [lexical_distance(anchor_tokens, row["abstract_view"]) for row in corpus]
            )
            score = score + 0.15 * lexical_far_score

        ranked = np.argsort(score)[::-1]
        picks = []
        for idx in ranked:
            row = corpus[idx]
            if negative_sims[idx] > 0.6:
                continue
            picks.append(
                {
                    "paper_id": row["paper_id"],
                    "title": row["title"],
                    "score": round(float(score[idx]), 4),
                    "negative_similarity": round(float(negative_sims[idx]), 4),
                    "section_backed": bool(row["section_snippets"]),
                }
            )
            if len(picks) >= 6:
                break

        if not picks:
            continue
        member_indices = [next(i for i, row in enumerate(corpus) if row["paper_id"] == pick["paper_id"]) for pick in picks]
        phrases = top_terms([corpus[idx]["abstract_view"] for idx in member_indices], limit=8)
        lexical_far_share = sum(
            1
            for idx in member_indices
            if lexical_distance(set().union(*(anchor_token_sets.get(name, set()) for name in probe.include)), corpus[idx]["abstract_view"]) >= 0.7
        ) / max(1, len(member_indices))
        region_type = explain_region_type(
            float(np.mean([negative_sims[idx] for idx in member_indices])),
            len(probe.include),
            lexical_far_share,
        )
        regions.append(
            {
                "name": probe.name,
                "include": list(probe.include),
                "exclude": list(probe.exclude),
                "region_type": region_type,
                "top_phrases": phrases,
                "papers": picks,
                "why_it_may_matter": (
                    "Combines anchor structure while staying away from known dead-end regions."
                    if len(probe.include) > 1
                    else "Finds papers structurally near the anchor but not trivially in the same lexical neighborhood."
                ),
            }
        )
    return regions[:top_regions]


def build_composition_report(corpus, matrix, anchor_centroids, negative_indices, top_pairs):
    negative_centroid = mean_vector(matrix, negative_indices)
    negative_sims = (
        cosine_similarity(negative_centroid, matrix).ravel()
        if negative_centroid is not None
        else np.zeros(matrix.shape[0])
    )
    anchor_names = list(anchor_centroids)
    regions = []
    for i, first in enumerate(anchor_names):
        for second in anchor_names[i + 1 :]:
            first_sim = cosine_similarity(anchor_centroids[first], matrix).ravel()
            second_sim = cosine_similarity(anchor_centroids[second], matrix).ravel()
            combo = np.minimum(first_sim, second_sim) - 0.20 * negative_sims
            picks = []
            for idx in np.argsort(combo)[::-1]:
                if negative_sims[idx] > 0.55:
                    continue
                picks.append(
                    {
                        "paper_id": corpus[idx]["paper_id"],
                        "title": corpus[idx]["title"],
                        "score": round(float(combo[idx]), 4),
                    }
                )
                if len(picks) >= 5:
                    break
            if not picks:
                continue
            regions.append(
                {
                    "pair": [first, second],
                    "score": round(float(np.mean([pick["score"] for pick in picks])), 4),
                    "why_stronger_together": (
                        f"{first} contributes one recurring motif while {second} adds a structurally different market-design or execution surface."
                    ),
                    "papers": picks,
                }
            )
    regions.sort(key=lambda item: item["score"], reverse=True)
    return regions[:top_pairs]


def build_shortlist(corpus, contrastive_regions, composition_regions, shortlist_size):
    selected = []
    seen = set()
    region_packets = []

    def add_region(region_name, region_kind, papers, why):
        chosen = []
        for paper in papers:
            if paper["paper_id"] in seen:
                continue
            seen.add(paper["paper_id"])
            chosen.append(paper["paper_id"])
            selected.append(paper["paper_id"])
            if len(selected) >= shortlist_size:
                break
        if chosen:
            region_packets.append(
                {
                    "region_name": region_name,
                    "region_kind": region_kind,
                    "paper_ids": chosen,
                    "why_made_cut": why,
                }
            )

    for region in contrastive_regions:
        if region["region_type"] == "dead_region":
            continue
        add_region(
            region["name"],
            region["region_type"],
            region["papers"][:4],
            region["why_it_may_matter"],
        )
        if len(selected) >= shortlist_size:
            break
    if len(selected) < shortlist_size:
        for region in composition_regions:
            add_region(
                " + ".join(region["pair"]),
                "compositional_region",
                region["papers"][:4],
                region["why_stronger_together"],
            )
            if len(selected) >= shortlist_size:
                break
    if len(selected) < shortlist_size:
        for region in contrastive_regions:
            if region["region_type"] != "dead_region":
                continue
            add_region(
                region["name"],
                region["region_type"],
                region["papers"][:2],
                region["why_it_may_matter"],
            )
            if len(selected) >= shortlist_size:
                break

    paper_lookup = {row["paper_id"]: row for row in corpus}
    shortlist = []
    for packet in region_packets:
        shortlist.extend(
            {
                "region_name": packet["region_name"],
                "region_kind": packet["region_kind"],
                "paper_id": paper_id,
                "title": paper_lookup[paper_id]["title"],
                "primary_category": paper_lookup[paper_id]["primary_category"],
                "has_sections": bool(paper_lookup[paper_id]["section_snippets"]),
                "top_weak_labels": [item["family_name"] for item in paper_lookup[paper_id]["weak_labels"][:3]],
                "why_made_cut": packet["why_made_cut"],
            }
            for paper_id in packet["paper_ids"]
        )
    return shortlist[:shortlist_size], region_packets


def write_markdown(output_path: Path, text: str):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_jsonl(output_path: Path, rows):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def render_corpus_map(run_id, corpus, clusters_small, clusters_main, clusters_large):
    lines = [
        f"# Corpus Map `{run_id}`",
        "",
        f"- total papers: `{len(corpus)}`",
        f"- papers with sections: `{sum(1 for row in corpus if row['section_snippets'])}`",
        "",
        "## Top Clusters",
    ]
    for packet in clusters_main:
        lines.extend(
            [
                "",
                f"### Cluster `{packet['cluster_id']}`",
                f"- size: `{packet['size']}`",
                f"- representative papers: {', '.join(packet['representative_paper_ids'])}",
                f"- top phrases: {', '.join(packet['top_phrases'])}",
                f"- interesting score: `{packet.get('interesting_score', 0.0)}`",
                f"- anchor mix: {', '.join(f'{name} ({count})' for name, count in packet.get('anchor_mix', [])) or 'none'}",
                f"- dominant categories: {', '.join(f'{name} ({count})' for name, count in packet['primary_categories'])}",
                f"- weak labels: {', '.join(f'{name} ({count})' for name, count in packet['weak_labels']) or 'none'}",
                f"- section-backed share: `{packet['section_backed_share']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Multi-Resolution Summary",
            "",
            f"- small resolution cluster count: `{len(clusters_small)}`",
            f"- medium resolution cluster count: `{len(clusters_main)}`",
            f"- large resolution cluster count: `{len(clusters_large)}`",
        ]
    )
    return "\n".join(lines)


def render_anchor_report(run_id, anchor_reports):
    lines = [f"# Anchor Neighborhood Report `{run_id}`"]
    for anchor_name, report in anchor_reports.items():
        lines.extend(
            [
                "",
                f"## `{anchor_name}`",
                f"- seed count: `{report['seed_count']}`",
                f"- seed papers: {', '.join(report['seed_papers'])}",
                "",
                "### Nearest Neighbors",
            ]
        )
        for item in report["nearest_neighbors"]:
            lines.append(
                f"- `{item['paper_id']}` {item['title']} | score={item['score']} | neg={item['negative_similarity']}"
            )
        lines.extend(["", "### Lexically Far Neighbors"])
        for item in report["lexically_far_neighbors"]:
            lines.append(
                f"- `{item['paper_id']}` {item['title']} | score={item['score']} | lexical_distance={item['lexical_distance']}"
            )
        lines.extend(["", "### Bridge Papers"])
        for item in report["bridge_papers"]:
            lines.append(
                f"- `{item['paper_id']}` {item['title']} | bridge_to={item['other_anchor']} | score={item['score']}"
            )
        lines.extend(["", "### Outliers"])
        for item in report["outliers"]:
            lines.append(
                f"- `{item['paper_id']}` {item['title']} | anchor_similarity={item['anchor_similarity']} | local_fit={item['local_fit']}"
            )
    return "\n".join(lines)


def render_contrastive_report(run_id, regions):
    lines = [f"# Contrastive Search Report `{run_id}`"]
    for region in regions:
        lines.extend(
            [
                "",
                f"## {region['name']}",
                f"- region type: `{region['region_type']}`",
                f"- include anchors: {', '.join(region['include'])}",
                f"- top phrases: {', '.join(region['top_phrases'])}",
                f"- why it may matter: {region['why_it_may_matter']}",
                "",
                "### Representative Papers",
            ]
        )
        for paper in region["papers"]:
            lines.append(
                f"- `{paper['paper_id']}` {paper['title']} | score={paper['score']} | neg={paper['negative_similarity']}"
            )
    return "\n".join(lines)


def render_composition_report(run_id, regions):
    lines = [f"# Composition Report `{run_id}`"]
    for region in regions:
        lines.extend(
            [
                "",
                f"## {' + '.join(region['pair'])}",
                f"- score: `{region['score']}`",
                f"- why stronger than either alone: {region['why_stronger_together']}",
                "",
                "### Region Papers",
            ]
        )
        for paper in region["papers"]:
            lines.append(f"- `{paper['paper_id']}` {paper['title']} | score={paper['score']}")
    return "\n".join(lines)


def render_shortlist(run_id, shortlist, region_packets):
    lines = [f"# Shortlist For Second-Pass Interpretation `{run_id}`", ""]
    lines.append(f"- shortlisted papers/chunks total: `{len(shortlist)}`")
    lines.append("")
    lines.append("## Regions")
    for packet in region_packets:
        lines.extend(
            [
                "",
                f"### {packet['region_name']}",
                f"- region kind: `{packet['region_kind']}`",
                f"- why this region made the cut: {packet['why_made_cut']}",
                f"- papers: {', '.join(packet['paper_ids'])}",
            ]
        )
    lines.extend(["", "## Paper Shortlist"])
    for item in shortlist:
        lines.extend(
            [
                "",
                f"- `{item['paper_id']}` {item['title']}",
                f"  - region: `{item['region_name']}`",
                f"  - kind: `{item['region_kind']}`",
                f"  - category: `{item['primary_category']}`",
                f"  - section-backed: `{item['has_sections']}`",
                f"  - weak labels: {', '.join(item['top_weak_labels']) or 'none'}",
                f"  - why: {item['why_made_cut']}",
            ]
        )
    return "\n".join(lines)


def flatten_clusters(level, packets):
    for packet in packets:
        yield {
            "level": level,
            "cluster_id": packet["cluster_id"],
            "size": packet["size"],
            "representative_paper_ids": packet["representative_paper_ids"],
            "top_phrases": packet["top_phrases"],
            "interesting_score": packet.get("interesting_score"),
            "anchor_mix": packet.get("anchor_mix", []),
            "primary_categories": packet["primary_categories"],
            "weak_labels": packet["weak_labels"],
            "section_backed_share": packet["section_backed_share"],
        }


def flatten_bridges(anchor_reports):
    for anchor_name, report in anchor_reports.items():
        for item in report["bridge_papers"]:
            yield {
                "anchor_name": anchor_name,
                "paper_id": item["paper_id"],
                "title": item["title"],
                "bridge_to": item["other_anchor"],
                "score": item["score"],
            }


def flatten_outliers(anchor_reports):
    for anchor_name, report in anchor_reports.items():
        for item in report["outliers"]:
            yield {
                "anchor_name": anchor_name,
                "paper_id": item["paper_id"],
                "title": item["title"],
                "anchor_similarity": item["anchor_similarity"],
                "local_fit": item["local_fit"],
            }


def flatten_probe_hits(contrastive_regions):
    for region in contrastive_regions:
        for rank, item in enumerate(region["papers"], start=1):
            yield {
                "region_name": region["name"],
                "region_type": region["region_type"],
                "include_anchors": region["include"],
                "rank": rank,
                "paper_id": item["paper_id"],
                "title": item["title"],
                "score": item["score"],
                "negative_similarity": item["negative_similarity"],
                "section_backed": item["section_backed"],
            }


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    embedding_spaces_path = Path(args.embedding_spaces_path).resolve()
    probes_path = Path(args.probes_path).resolve()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else (DEFAULT_OUTPUT_ROOT / args.run_id).resolve()
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        corpus = load_corpus(connection)
    finally:
        connection.close()

    rep = build_representation(
        corpus,
        output_dir=output_dir,
        embedding_spaces_path=embedding_spaces_path,
        embedding_model=args.embedding_model,
        embed_batch_size=args.embed_batch_size,
    )
    matrix = rep["combined"]

    labels_small, centers_small = build_clusters(matrix, args.cluster_count_small)
    labels_main, centers_main = build_clusters(matrix, args.cluster_count)
    labels_large, centers_large = build_clusters(matrix, args.cluster_count_large)

    anchor_indices, negative_indices = attach_anchor_seeds(corpus)
    anchor_reports, anchor_centroids, anchor_token_sets = score_anchor_neighborhoods(
        corpus,
        matrix,
        anchor_indices,
        negative_indices,
        args.top_neighbors,
    )
    probe_configs = build_probe_configs(probes_path)
    clusters_small_all, _ = build_cluster_packets(corpus, matrix, labels_small, centers_small, args.cluster_count_small)
    clusters_main_all, _ = build_cluster_packets(corpus, matrix, labels_main, centers_main, args.cluster_count)
    clusters_large_all, _ = build_cluster_packets(corpus, matrix, labels_large, centers_large, args.cluster_count_large)
    clusters_small = rank_clusters_by_interest(
        clusters_small_all,
        corpus,
        matrix,
        anchor_centroids,
        negative_indices,
        args.cluster_count_small,
    )
    clusters_main = rank_clusters_by_interest(
        clusters_main_all,
        corpus,
        matrix,
        anchor_centroids,
        negative_indices,
        args.top_clusters,
    )
    clusters_large = rank_clusters_by_interest(
        clusters_large_all,
        corpus,
        matrix,
        anchor_centroids,
        negative_indices,
        args.cluster_count_large,
    )
    contrastive_regions = evaluate_contrastive_regions(
        corpus,
        matrix,
        anchor_centroids,
        anchor_token_sets,
        negative_indices,
        args.top_contrastive,
        probe_configs,
    )
    composition_regions = build_composition_report(
        corpus,
        matrix,
        anchor_centroids,
        negative_indices,
        args.top_composition,
    )
    shortlist, region_packets = build_shortlist(
        corpus,
        contrastive_regions,
        composition_regions,
        args.shortlist_size,
    )

    manifest = {
        "run_id": args.run_id,
        "paper_count": len(corpus),
        "section_backed_paper_count": sum(1 for row in corpus if row["section_snippets"]),
        "run_db_path": str(rep["run_db_path"]),
        "embedding_model": args.embedding_model,
        "anchor_seed_counts": {name: len(indices) for name, indices in anchor_indices.items()},
        "negative_anchor_count": len(negative_indices),
        "reports": {
            "corpus_map": str(output_dir / "corpus_map.md"),
            "anchor_report": str(output_dir / "anchor_neighborhood_report.md"),
            "contrastive_report": str(output_dir / "contrastive_search_report.md"),
            "composition_report": str(output_dir / "composition_report.md"),
            "shortlist_report": str(output_dir / "shortlist_for_second_pass.md"),
            "payload": str(output_dir / "representation_discovery_payload.json"),
            "cluster_overview": str(output_dir / "cluster_overview.md"),
            "bridge_report": str(output_dir / "bridge_report.md"),
            "outlier_report": str(output_dir / "outlier_report.md"),
            "shortlist_packet": str(output_dir / "shortlist_packet.md"),
        },
        "artifacts": {
            "clusters_jsonl": str(output_dir / "clusters.jsonl"),
            "bridges_jsonl": str(output_dir / "bridges.jsonl"),
            "outliers_jsonl": str(output_dir / "outliers.jsonl"),
            "probe_hits_jsonl": str(output_dir / "probe_hits.jsonl"),
            "shortlist_jsonl": str(output_dir / "shortlist.jsonl"),
            "metrics_json": str(output_dir / "metrics.json"),
            "params_yaml": str(output_dir / "params.yaml"),
            "manifest_yaml": str(output_dir / "manifest.yaml"),
            "logs_jsonl": str(output_dir / "logs.jsonl"),
        },
    }
    payload = {
        "manifest": manifest,
        "clusters": {
            "small": clusters_small,
            "main": clusters_main,
            "large": clusters_large,
        },
        "anchor_reports": anchor_reports,
        "contrastive_regions": contrastive_regions,
        "composition_regions": composition_regions,
        "shortlist": shortlist,
        "region_packets": region_packets,
    }

    corpus_map_text = render_corpus_map(args.run_id, corpus, clusters_small, clusters_main, clusters_large)
    anchor_report_text = render_anchor_report(args.run_id, anchor_reports)
    contrastive_text = render_contrastive_report(args.run_id, contrastive_regions)
    composition_text = render_composition_report(args.run_id, composition_regions)
    shortlist_text = render_shortlist(args.run_id, shortlist, region_packets)
    write_markdown(output_dir / "corpus_map.md", corpus_map_text)
    write_markdown(output_dir / "anchor_neighborhood_report.md", render_anchor_report(args.run_id, anchor_reports))
    write_markdown(output_dir / "contrastive_search_report.md", render_contrastive_report(args.run_id, contrastive_regions))
    write_markdown(output_dir / "composition_report.md", render_composition_report(args.run_id, composition_regions))
    write_markdown(output_dir / "shortlist_for_second_pass.md", render_shortlist(args.run_id, shortlist, region_packets))
    write_markdown(output_dir / "cluster_overview.md", corpus_map_text)
    write_markdown(output_dir / "bridge_report.md", anchor_report_text)
    write_markdown(output_dir / "outlier_report.md", anchor_report_text)
    write_markdown(output_dir / "shortlist_packet.md", shortlist_text)
    write_jsonl(output_dir / "clusters.jsonl", list(flatten_clusters("coarse", clusters_small)) + list(flatten_clusters("mid", clusters_main)) + list(flatten_clusters("local", clusters_large)))
    write_jsonl(output_dir / "bridges.jsonl", flatten_bridges(anchor_reports))
    write_jsonl(output_dir / "outliers.jsonl", flatten_outliers(anchor_reports))
    write_jsonl(output_dir / "probe_hits.jsonl", flatten_probe_hits(contrastive_regions))
    write_jsonl(output_dir / "shortlist.jsonl", shortlist)
    (output_dir / "representation_discovery_payload.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    metrics = {
        "paper_count": len(corpus),
        "section_backed_paper_count": sum(1 for row in corpus if row["section_snippets"]),
        "anchor_seed_counts": {name: len(indices) for name, indices in anchor_indices.items()},
        "negative_anchor_count": len(negative_indices),
        "contrastive_region_count": len(contrastive_regions),
        "composition_region_count": len(composition_regions),
        "shortlist_count": len(shortlist),
        "embedding_spaces": [space["name"] for space in rep["spaces"]],
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "representation_discovery_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "params.yaml").write_text(
        yaml.safe_dump(
            {
                "db_path": str(db_path),
                "embedding_spaces_path": str(embedding_spaces_path),
                "probes_path": str(probes_path),
                "embedding_model": args.embedding_model,
                "embed_batch_size": args.embed_batch_size,
                "cluster_count": args.cluster_count,
                "cluster_count_small": args.cluster_count_small,
                "cluster_count_large": args.cluster_count_large,
                "top_clusters": args.top_clusters,
                "top_neighbors": args.top_neighbors,
                "top_contrastive": args.top_contrastive,
                "top_composition": args.top_composition,
                "shortlist_size": args.shortlist_size,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (output_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=True),
        encoding="utf-8",
    )
    logs = [
        {"run_id": args.run_id, "stage": "corpus", "event_type": "loaded", "payload": {"paper_count": len(corpus)}},
        {"run_id": args.run_id, "stage": "embed", "event_type": "spaces_materialized", "payload": {"spaces": [space["name"] for space in rep["spaces"]], "run_db_path": str(rep["run_db_path"])}},
        {"run_id": args.run_id, "stage": "probe", "event_type": "contrastive_regions_built", "payload": {"region_count": len(contrastive_regions)}},
        {"run_id": args.run_id, "stage": "shortlist", "event_type": "shortlist_built", "payload": {"shortlist_count": len(shortlist)}},
    ]
    write_jsonl(output_dir / "logs.jsonl", logs)
    rep["vec_connection"].close()
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
