#!/usr/bin/env python3

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

from sqlite_vec_adapter import connect as connect_vec_store, query_knn


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_ANCHORS_PATH = ROOT / "configs" / "anchors.yaml"
DEFAULT_PROBES_PATH = ROOT / "configs" / "probes.yaml"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize anchors, agitator patterns, and canonical probe hits.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="probe-materialization-20260328")
    parser.add_argument("--embedding-run-id", default="view-embeddings-materialization-20260328")
    parser.add_argument("--embedding-metrics-path", default=None)
    parser.add_argument("--vec-db-path", default=None)
    parser.add_argument("--anchors-path", default=str(DEFAULT_ANCHORS_PATH))
    parser.add_argument("--probes-path", default=str(DEFAULT_PROBES_PATH))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--top-k", type=int, default=25)
    parser.add_argument("--candidate-pool", type=int, default=200)
    return parser.parse_args()


def load_yaml(path: Path, default):
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def vector_from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def lexical_distance(seed_terms: list[str], text: str) -> float:
    if not seed_terms:
        return 1.0
    text_lower = (text or "").lower()
    hits = sum(1 for term in seed_terms if term.lower() in text_lower)
    return 1.0 - (hits / max(1, len(seed_terms)))


def load_embedding_metrics(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def upsert_anchors(connection: sqlite3.Connection, anchors_payload: dict) -> None:
    for anchor in anchors_payload.get("anchors", []):
        connection.execute(
            """
            INSERT INTO anchors (anchor_id, label, anchor_type, paper_id, notes, tags_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(anchor_id) DO UPDATE SET
              label = excluded.label,
              anchor_type = excluded.anchor_type,
              paper_id = excluded.paper_id,
              notes = excluded.notes,
              tags_json = excluded.tags_json
            """,
            (
                anchor["anchor_id"],
                anchor["label"],
                anchor["anchor_type"],
                anchor.get("paper_id"),
                anchor.get("notes"),
                json.dumps(
                    {
                        "paper_ids": anchor.get("paper_ids", []),
                        "keywords": anchor.get("keywords", []),
                        "allowed_categories": anchor.get("allowed_categories", []),
                        "min_keyword_hits": anchor.get("min_keyword_hits"),
                        "family_patterns": anchor.get("family_patterns", []),
                        "tags": anchor.get("tags", []),
                    },
                    sort_keys=True,
                ),
            ),
        )


def upsert_patterns(connection: sqlite3.Connection, probes_payload: dict) -> None:
    for pattern in probes_payload.get("patterns", []):
        synthetic_text = normalize_text(
            f"{pattern['label']} | include: {', '.join(pattern.get('include', []))} | exclude: {', '.join(pattern.get('exclude', []))}"
        )
        connection.execute(
            """
            INSERT INTO agitator_patterns (
              pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pattern_id) DO UPDATE SET
              label = excluded.label,
              kind = excluded.kind,
              text = excluded.text,
              positive_tags_json = excluded.positive_tags_json,
              negative_tags_json = excluded.negative_tags_json,
              active = excluded.active
            """,
            (
                pattern["pattern_id"],
                pattern["label"],
                pattern["kind"],
                synthetic_text,
                json.dumps(pattern.get("include", []), sort_keys=True),
                json.dumps(pattern.get("exclude", []), sort_keys=True),
                1,
            ),
        )


def table_name_for_space(space_name: str, dims: int) -> str:
    return f"vec_{space_name}_{dims}".replace("-", "_")


def resolve_anchor_paper_ids(connection: sqlite3.Connection, anchor: dict) -> list[str]:
    explicit = list(anchor.get("paper_ids", []))
    patterns = anchor.get("family_patterns", [])
    if not patterns:
        return explicit
    resolved = set(explicit)
    for pattern in patterns:
        rows = connection.execute(
            """
            SELECT DISTINCT mi.paper_id
            FROM mechanism_instances mi
            JOIN candidate_family_members cfm
              ON cfm.candidate_mechanism_instance_id = mi.mechanism_instance_id
            JOIN candidate_families cf
              ON cf.candidate_family_id = cfm.candidate_family_id
            WHERE lower(cf.family_name) LIKE ?
            """,
            (f"%{pattern.lower()}%",),
        ).fetchall()
        resolved.update(row["paper_id"] for row in rows)
    return sorted(resolved)


def load_space_vectors(vec_connection: sqlite3.Connection, table_name: str) -> tuple[dict[int, np.ndarray], list[int]]:
    rows = vec_connection.execute(f"SELECT rowid, embedding FROM {table_name} ORDER BY rowid").fetchall()
    vectors = {int(rowid): vector_from_blob(blob) for rowid, blob in rows}
    return vectors, sorted(vectors)


def build_anchor_centroids(
    canonical_connection: sqlite3.Connection,
    vectors_by_view_id: dict[int, np.ndarray],
    view_type: str,
    anchors_payload: dict,
) -> dict[str, np.ndarray]:
    centroids = {}
    for anchor in anchors_payload.get("anchors", []):
        paper_ids = resolve_anchor_paper_ids(canonical_connection, anchor)
        if not paper_ids:
            continue
        placeholders = ",".join("?" for _ in paper_ids)
        rows = canonical_connection.execute(
            f"""
            SELECT view_id
            FROM text_views
            WHERE view_type = ?
              AND paper_id IN ({placeholders})
            """,
            (view_type, *paper_ids),
        ).fetchall()
        vectors = [vectors_by_view_id[int(row["view_id"])] for row in rows if int(row["view_id"]) in vectors_by_view_id]
        if vectors:
            centroids[anchor["anchor_id"]] = np.mean(np.stack(vectors), axis=0)
    return centroids


def prepare_space_payloads(
    canonical_connection: sqlite3.Connection,
    vec_connection: sqlite3.Connection,
    embedding_metrics: dict,
    anchors_payload: dict,
) -> list[dict]:
    space_payloads = []
    for space in embedding_metrics["spaces"]:
        table_name = space.get("table_name") or table_name_for_space(space["name"], space["dims"])
        vectors_by_view_id, _view_ids = load_space_vectors(vec_connection, table_name)
        # @context decision -- Preload vectors and centroids once per embedding
        # space, not once per pattern. The live corpus has enough probe patterns
        # and vectors that recomputing this inside the pattern loop makes the
        # canonical S17 probe materialization effectively non-terminating.
        centroids = build_anchor_centroids(
            canonical_connection,
            vectors_by_view_id,
            space["view_type"],
            anchors_payload,
        )
        space_payloads.append(
            {
                "space": space,
                "table_name": table_name,
                "vectors_by_view_id": vectors_by_view_id,
                "centroids": centroids,
            }
        )
    return space_payloads


def build_pattern_query(pattern: dict, centroids: dict[str, np.ndarray]) -> np.ndarray | None:
    include_centroids = [centroids[anchor_id] for anchor_id in pattern.get("include", []) if anchor_id in centroids]
    if not include_centroids:
        return None
    return np.mean(np.stack(include_centroids), axis=0)


def probe_space(
    canonical_connection: sqlite3.Connection,
    vectors_by_view_id: dict[int, np.ndarray],
    view_type: str,
    pattern: dict,
    centroids: dict[str, np.ndarray],
    nearest_rows: list[sqlite3.Row],
) -> dict[int, dict]:
    negative_centroids = [centroids[anchor_id] for anchor_id in pattern.get("exclude", []) if anchor_id in centroids]

    hits = {}
    for row in nearest_rows:
        view_id = int(row["rowid"])
        view_row = canonical_connection.execute(
            """
            SELECT paper_id, text
            FROM text_views
            WHERE view_id = ?
            """,
            (view_id,),
        ).fetchone()
        positive_score = 1.0 / (1.0 + float(row["distance"]))
        negative_penalty = 0.0
        if negative_centroids:
            vector = vectors_by_view_id.get(view_id)
            if vector is None:
                continue
            negative_penalty = max(float(np.dot(vector, neg)) for neg in negative_centroids)
        lexical_bonus = 0.0
        if pattern.get("lexical_far_from"):
            lexical_bonus = 0.2 * lexical_distance(pattern["lexical_far_from"], view_row["text"])
        score = positive_score - 0.5 * negative_penalty + lexical_bonus
        current = hits.get(view_row["paper_id"])
        payload = {
            "view_id": view_id,
            "paper_id": view_row["paper_id"],
            "score": score,
        }
        if current is None or score > current["score"]:
            hits[view_row["paper_id"]] = payload
    return hits


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.embedding_metrics_path:
        embedding_metrics_path = Path(args.embedding_metrics_path).resolve()
    else:
        embedding_metrics_path = DEFAULT_OUTPUT_ROOT / args.embedding_run_id / "embedding_metrics.json"
    embedding_metrics = load_embedding_metrics(embedding_metrics_path)
    vec_db_path = Path(args.vec_db_path).resolve() if args.vec_db_path else Path(embedding_metrics["vec_db_path"]).resolve()

    anchors_payload = load_yaml(Path(args.anchors_path), {"anchors": []})
    probes_payload = load_yaml(Path(args.probes_path), {"patterns": []})

    canonical_connection = sqlite3.connect(str(db_path))
    canonical_connection.row_factory = sqlite3.Row
    vec_connection = connect_vec_store(vec_db_path)
    try:
        log_run_event(
            canonical_connection,
            args.run_id,
            "probe",
            "started",
            {
                "embedding_run_id": args.embedding_run_id,
                "top_k": args.top_k,
                "candidate_pool": args.candidate_pool,
            },
        )
        upsert_anchors(canonical_connection, anchors_payload)
        upsert_patterns(canonical_connection, probes_payload)
        canonical_connection.execute("DELETE FROM probe_hits WHERE run_id = ?", (args.run_id,))

        space_payloads = prepare_space_payloads(
            canonical_connection,
            vec_connection,
            embedding_metrics,
            anchors_payload,
        )
        pattern_rows = []
        for pattern in probes_payload.get("patterns", []):
            per_pattern = {}
            for space_payload in space_payloads:
                space = space_payload["space"]
                query_vector = build_pattern_query(pattern, space_payload["centroids"])
                nearest_rows = (
                    query_knn(
                        vec_connection,
                        space_payload["table_name"],
                        query_vector,
                        args.candidate_pool,
                    )
                    if query_vector is not None
                    else []
                )
                hits = probe_space(
                    canonical_connection,
                    space_payload["vectors_by_view_id"],
                    space["view_type"],
                    pattern,
                    space_payload["centroids"],
                    nearest_rows,
                )
                for paper_id, payload in hits.items():
                    current = per_pattern.get(paper_id)
                    if current is None:
                        per_pattern[paper_id] = payload.copy()
                        per_pattern[paper_id]["score"] = payload["score"]
                    else:
                        current["score"] += payload["score"]
                        if payload["score"] > current.get("best_component_score", current["score"]):
                            current["view_id"] = payload["view_id"]
                    per_pattern[paper_id]["best_component_score"] = max(
                        payload["score"],
                        per_pattern[paper_id].get("best_component_score", payload["score"]),
                    )
            ranked = sorted(per_pattern.values(), key=lambda item: (-item["score"], item["paper_id"]))[: args.top_k]
            for rank, item in enumerate(ranked, start=1):
                pattern_rows.append(
                    (
                        args.run_id,
                        pattern["pattern_id"],
                        item["view_id"],
                        float(item["score"]),
                        rank,
                    )
                )

        canonical_connection.executemany(
            """
            INSERT INTO probe_hits (run_id, pattern_id, view_id, score, rank)
            VALUES (?, ?, ?, ?, ?)
            """,
            pattern_rows,
        )
        metrics = {
            "run_id": args.run_id,
            "embedding_run_id": args.embedding_run_id,
            "anchor_count": len(anchors_payload.get("anchors", [])),
            "pattern_count": len(probes_payload.get("patterns", [])),
            "probe_hit_count": len(pattern_rows),
            "top_k": args.top_k,
        }
        metrics_path = output_dir / "probe_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(
            canonical_connection,
            args.run_id,
            "probe",
            "completed",
            {"metrics_path": str(metrics_path), **metrics},
        )
        canonical_connection.commit()
    finally:
        vec_connection.close()
        canonical_connection.close()

    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
