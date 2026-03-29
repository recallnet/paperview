#!/usr/bin/env python3

import argparse
import json
import math
import sqlite3
from array import array
from pathlib import Path

try:
    import sqlite_vec
except ImportError:  # pragma: no cover
    sqlite_vec = None


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_REPORTS_DIR = ROOT / "reports"
DEFAULT_EMBEDDING_METRICS_PATH = ROOT / "data" / "structural-analogy" / "runs" / "view-embeddings-materialization-20260328" / "embedding_metrics.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize the DS5 holdout-echo validation report.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--embedding-metrics-path", default=str(DEFAULT_EMBEDDING_METRICS_PATH))
    parser.add_argument("--vec-db-path", default=None)
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--view-type", default="title_abs")
    parser.add_argument("--top-k-candidates", type=int, default=20)
    parser.add_argument("--top-k-echoes", type=int, default=3)
    return parser.parse_args()


def connect_vec_db(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    if sqlite_vec is not None:
        connection.enable_load_extension(True)
        sqlite_vec.load(connection)
    return connection


def vector_from_blob(blob: bytes) -> list[float]:
    values = array("f")
    values.frombytes(blob)
    return list(values)


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_candidate_pool(reports_dir: Path, top_k: int) -> list[dict]:
    candidates: list[dict] = []
    for path_str, source_surface, family_key, summary_key in [
        ("ds1-translation-gap-candidates.jsonl", "ds1_translation_gap", "challenge_capsule_matched", "why_far_from_realized"),
        ("ds3-early-market-ledger.jsonl", "ds3_early_market", "lane_family", "failure_mode"),
        ("ds4-stranded-ledger.jsonl", "ds4_stranded_rescue", "rescue_family", "modern_equivalent_now"),
    ]:
        for row in load_jsonl(reports_dir / path_str)[:top_k]:
            candidates.append(
                {
                    "paper_id": row["paper_id"],
                    "source_surface": source_surface,
                    "candidate_family": row.get(family_key, "unknown"),
                    "candidate_summary": row.get(summary_key, ""),
                }
            )
    deduped: list[dict] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate["paper_id"] in seen:
            continue
        seen.add(candidate["paper_id"])
        deduped.append(candidate)
    return deduped


def table_name_for_space(space_name: str, dims: int) -> str:
    return f"vec_{space_name}_{dims}".replace("-", "_")


# @context decision -- DS5 validates the concrete DS study outputs directly.
# Reusing the older shortlist-only holdout table would miss the broadened
# candidates from DS1/DS3/DS4 and would make the study look narrower than the
# actual diamond-hunting work now in the repo.
def load_paper_vectors(
    canonical_connection: sqlite3.Connection,
    vec_connection: sqlite3.Connection,
    embedding_metrics: dict,
    view_type: str,
) -> dict[str, list[float]]:
    matching_space = next(space for space in embedding_metrics["spaces"] if space["view_type"] == view_type)
    table_name = matching_space.get("table_name") or table_name_for_space(matching_space["name"], matching_space["dims"])
    vec_rows = vec_connection.execute(f"SELECT rowid, embedding FROM {table_name}").fetchall()
    vectors_by_view_id = {int(row["rowid"]): normalize(vector_from_blob(row["embedding"])) for row in vec_rows}
    text_rows = canonical_connection.execute(
        """
        SELECT view_id, paper_id
        FROM text_views
        WHERE view_type = ?
        """,
        (view_type,),
    ).fetchall()
    paper_vectors: dict[str, list[float]] = {}
    for row in text_rows:
        view_id = int(row["view_id"])
        if view_id in vectors_by_view_id:
            paper_vectors[row["paper_id"]] = vectors_by_view_id[view_id]
    return paper_vectors


def verdict_for(score: float) -> str:
    if score >= 0.75:
        return "validation"
    if score >= 0.68:
        return "partial"
    return "unrelated"


def log_run_event(connection: sqlite3.Connection, reports_dir: Path, meaningful_count: int, row_count: int) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (
            "ds5-holdout-echo-validation",
            "diamond_study",
            "completed",
            json.dumps(
                {
                    "reports_dir": str(reports_dir),
                    "candidate_count": row_count,
                    "meaningful_count": meaningful_count,
                    "success": meaningful_count >= 10,
                },
                sort_keys=True,
            ),
        ),
    )


def render_report(rows: list[dict], meaningful_count: int, family_counts: dict[str, int], verdict_counts: dict[str, int]) -> str:
    lines = [
        "# DS5 Holdout Echo Report",
        "",
        "This study checks whether top pre-2024 candidates from the DS study stack echo meaningfully in later 2024+ market-adjacent papers.",
        "",
        "## Stop / Go",
        "",
        f"- pre-2024 candidates evaluated: `{len(rows)}`",
        f"- meaningful echoes (`validation` or `partial`): `{meaningful_count}`",
        f"- success threshold met: `{str(meaningful_count >= 10).lower()}`",
        "",
        "## Candidate-Family Diversity",
        "",
    ]
    for family, count in sorted(family_counts.items()):
        lines.append(f"- {family}: `{count}`")
    lines.extend(["", "## Verdict Mix", ""])
    for verdict, count in sorted(verdict_counts.items()):
        lines.append(f"- {verdict}: `{count}`")
    lines.extend(["", "## Top Candidates", ""])
    for row in rows:
        top_echo = row["top_holdout_echoes"][0]
        lines.extend(
            [
                f"- `{row['candidate_paper_id']}` | `{row['candidate_family']}` | `{row['echo_verdict']}` | score `{row['top_echo_score']}`",
                f"  candidate: {row['candidate_title']}",
                f"  top echo: {top_echo['paper_id']} — {top_echo['title']}",
                f"  why it matters: {row['candidate_summary']}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    db_path = Path(args.db_path).resolve()
    embedding_metrics = json.loads(Path(args.embedding_metrics_path).resolve().read_text(encoding="utf-8"))
    vec_db_path = Path(args.vec_db_path).resolve() if args.vec_db_path else Path(embedding_metrics["vec_db_path"]).resolve()

    canonical_connection = sqlite3.connect(str(db_path))
    canonical_connection.row_factory = sqlite3.Row
    vec_connection = connect_vec_db(vec_db_path)
    try:
        paper_vectors = load_paper_vectors(canonical_connection, vec_connection, embedding_metrics, args.view_type)
        holdout_ids = [
            row["paper_id"]
            for row in canonical_connection.execute(
                """
                SELECT paper_id
                FROM corpus_memberships
                WHERE run_id = ?
                  AND corpus_id = 'holdout'
                ORDER BY paper_id
                """,
                (args.membership_run_id,),
            ).fetchall()
            if row["paper_id"] in paper_vectors
        ]
        candidate_rows = []
        for candidate in load_candidate_pool(reports_dir, args.top_k_candidates):
            paper_id = candidate["paper_id"]
            meta = canonical_connection.execute(
                """
                SELECT paper_id, title, primary_category, published_at
                FROM papers
                WHERE paper_id = ?
                """,
                (paper_id,),
            ).fetchone()
            if meta is None or meta["published_at"] is None or meta["published_at"] >= "2024-01-01":
                continue
            if paper_id not in paper_vectors:
                continue
            scored = []
            for holdout_paper_id in holdout_ids:
                if holdout_paper_id == paper_id:
                    continue
                score = float(dot(paper_vectors[paper_id], paper_vectors[holdout_paper_id]))
                scored.append((score, holdout_paper_id))
            scored.sort(key=lambda item: (-item[0], item[1]))
            top_echoes = []
            for rank, (score, holdout_paper_id) in enumerate(scored[: args.top_k_echoes], start=1):
                holdout_meta = canonical_connection.execute(
                    """
                    SELECT paper_id, title, primary_category, published_at
                    FROM papers
                    WHERE paper_id = ?
                    """,
                    (holdout_paper_id,),
                ).fetchone()
                top_echoes.append(
                    {
                        "paper_id": holdout_paper_id,
                        "title": holdout_meta["title"],
                        "home_domain": holdout_meta["primary_category"],
                        "published_at": holdout_meta["published_at"],
                        "echo_score": round(score, 6),
                        "echo_rank": rank,
                    }
                )
            if not top_echoes:
                continue
            top_score = top_echoes[0]["echo_score"]
            candidate_rows.append(
                {
                    "candidate_paper_id": paper_id,
                    "candidate_title": meta["title"],
                    "candidate_home_domain": meta["primary_category"],
                    "candidate_published_at": meta["published_at"],
                    "source_surface": candidate["source_surface"],
                    "candidate_family": candidate["candidate_family"],
                    "candidate_summary": candidate["candidate_summary"],
                    "top_echo_score": top_score,
                    "echo_verdict": verdict_for(top_score),
                    "top_holdout_echoes": top_echoes,
                }
            )

        candidate_rows.sort(
            key=lambda row: (
                {"validation": 0, "partial": 1, "unrelated": 2}[row["echo_verdict"]],
                -row["top_echo_score"],
                row["candidate_paper_id"],
            )
        )
        meaningful_count = sum(1 for row in candidate_rows if row["echo_verdict"] != "unrelated")
        family_counts: dict[str, int] = {}
        verdict_counts: dict[str, int] = {}
        for row in candidate_rows:
            family_counts[row["candidate_family"]] = family_counts.get(row["candidate_family"], 0) + 1
            verdict_counts[row["echo_verdict"]] = verdict_counts.get(row["echo_verdict"], 0) + 1

        jsonl_path = reports_dir / "ds5-holdout-echo-report.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in candidate_rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown_path = reports_dir / "ds5-holdout-echo-report.md"
        markdown_path.write_text(render_report(candidate_rows, meaningful_count, family_counts, verdict_counts), encoding="utf-8")

        log_run_event(canonical_connection, reports_dir, meaningful_count, len(candidate_rows))
        canonical_connection.commit()
    finally:
        vec_connection.close()
        canonical_connection.close()


if __name__ == "__main__":
    main()
