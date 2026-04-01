#!/usr/bin/env python3

import argparse
import json
import sqlite3
import time
from pathlib import Path

import yaml

from sqlite_vec_adapter import (
    connect as connect_vec_store,
    ensure_vec_table,
    stable_short_id,
    upsert_embedding_space,
    upsert_view_embedding_meta,
    write_vectors,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_EMBEDDING_SPACES_PATH = ROOT / "configs" / "embedding_spaces.yaml"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Materialize local embeddings for canonical text views."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="view-embeddings-materialization-20260328")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--embedding-spaces-path", default=str(DEFAULT_EMBEDDING_SPACES_PATH))
    parser.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--embed-batch-size", type=int, default=128)
    parser.add_argument("--limit-per-space", type=int, default=None)
    return parser.parse_args()


def load_yaml_config(path: Path, default):
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def table_name_for_space(space_name: str, dims: int) -> str:
    return f"vec_{space_name}_{dims}".replace("-", "_")


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def load_view_rows(connection: sqlite3.Connection, view_type: str, limit_per_space: int | None) -> list[sqlite3.Row]:
    sql = """
        SELECT view_id, paper_id, text, text_sha256
        FROM text_views
        WHERE view_type = ?
        ORDER BY view_id
    """
    params: tuple[object, ...] = (view_type,)
    if limit_per_space is not None:
        sql += " LIMIT ?"
        params = (view_type, limit_per_space)
    return connection.execute(sql, params).fetchall()


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    vec_db_path = output_dir / "embeddings.sqlite3"
    if vec_db_path.exists():
        vec_db_path.unlink()

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
    spaces = load_yaml_config(Path(args.embedding_spaces_path), default_spaces).get("spaces", default_spaces["spaces"])

    canonical_connection = sqlite3.connect(str(db_path))
    canonical_connection.row_factory = sqlite3.Row
    vec_connection = connect_vec_store(vec_db_path)
    try:
        log_run_event(
            canonical_connection,
            args.run_id,
            "embed",
            "started",
            {
                "db_path": str(db_path),
                "vec_db_path": str(vec_db_path),
                "embedding_model": args.embedding_model,
                "embed_batch_size": args.embed_batch_size,
                "limit_per_space": args.limit_per_space,
            },
        )
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(args.embedding_model)
        dims = int(model.get_sentence_embedding_dimension())
        per_space = []

        for space in spaces:
            rows = load_view_rows(canonical_connection, space["view_type"], args.limit_per_space)
            texts = [row["text"] for row in rows]
            started = time.perf_counter()
            vectors = model.encode(
                texts,
                batch_size=args.embed_batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            table_name = table_name_for_space(space["name"], dims)
            ensure_vec_table(vec_connection, table_name, dims)
            write_vectors(vec_connection, table_name, [row["view_id"] for row in rows], vectors)
            space_id = upsert_embedding_space(
                canonical_connection,
                name=space["name"],
                model_name=args.embedding_model,
                dims=dims,
                normalized=True,
                prompt_style=space.get("prompt_style", space["view_type"]),
            )
            batch_id = f"{args.run_id}-{stable_short_id(space['name'])}"
            upsert_view_embedding_meta(
                canonical_connection,
                space_id=space_id,
                view_ids=[row["view_id"] for row in rows],
                batch_id=batch_id,
                embed_ms=elapsed_ms,
            )
            per_space.append(
                {
                    "name": space["name"],
                    "view_type": space["view_type"],
                    "dims": dims,
                    "table_name": table_name,
                    "view_count": len(rows),
                    "embed_ms": elapsed_ms,
                }
            )

        metrics = {
            "run_id": args.run_id,
            "embedding_model": args.embedding_model,
            "dims": dims,
            "space_count": len(per_space),
            "total_vectors": sum(item["view_count"] for item in per_space),
            "vec_db_path": str(vec_db_path),
            "spaces": per_space,
        }
        metrics_path = output_dir / "embedding_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(
            canonical_connection,
            args.run_id,
            "embed",
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
