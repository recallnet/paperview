#!/usr/bin/env python3

import argparse
import json
import math
import sqlite3
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_REPORTS_DIR = ROOT / "reports"
DEFAULT_CAPSULES_PATH = ROOT / "configs" / "challenge_capsules.yaml"


def parse_args():
    parser = argparse.ArgumentParser(description="Run DS1 translation-gap search over the current broadened arXiv-only system.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--challenge-capsules-path", default=str(DEFAULT_CAPSULES_PATH))
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--probe-run-id", default="probe-materialization-20260328-broadened")
    parser.add_argument("--bridge-run-id", default="bridge-materialization-20260328-broadened")
    parser.add_argument("--composition-run-id", default="composition-materialization-20260328-broadened")
    parser.add_argument("--transition-run-id", default="transition-state-candidate-materialization-20260328-broadened")
    parser.add_argument("--resurfacing-run-id", default="stranded-resurfacing-materialization-20260328")
    parser.add_argument("--negative-space-run-id", default="negative-space-materialization-20260328")
    parser.add_argument("--top-k", type=int, default=100)
    return parser.parse_args()


def load_yaml(path: Path, default):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return default


def home_domain(primary_category: str | None) -> str:
    return (primary_category or "unknown").strip() or "unknown"


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def normalized_operator_score(source_type: str, raw_score: float) -> float:
    if source_type == "bridge":
        return min(1.5, raw_score / 2.5)
    if source_type == "composition":
        return min(1.8, raw_score / 3.0)
    if source_type == "transition_state":
        return min(1.4, raw_score / 0.8)
    if source_type == "stranded_qfin":
        return min(1.4, raw_score / 0.45)
    if source_type == "probe":
        return min(1.0, raw_score)
    return 0.0


def fetch_realized_market_ids(connection: sqlite3.Connection, membership_run_id: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT paper_id
        FROM corpus_memberships
        WHERE run_id = ?
          AND corpus_id = 'realized_market'
        """,
        (membership_run_id,),
    ).fetchall()
    return {row["paper_id"] for row in rows}


def fetch_negative_space_penalties(connection: sqlite3.Connection, run_id: str) -> dict[str, float]:
    rows = connection.execute(
        """
        SELECT paper_id, MAX(negative_space_score) AS penalty
        FROM negative_space_candidates
        WHERE run_id = ?
        GROUP BY paper_id
        """,
        (run_id,),
    ).fetchall()
    return {row["paper_id"]: min(1.0, float(row["penalty"] or 0.0) / 3.0) for row in rows}


def fetch_probe_support(connection: sqlite3.Connection, run_id: str) -> dict[str, list[dict]]:
    rows = connection.execute(
        """
        SELECT
          tv.paper_id,
          ph.pattern_id,
          ap.label,
          MAX(ph.score) AS max_score
        FROM probe_hits ph
        JOIN text_views tv
          ON tv.view_id = ph.view_id
        JOIN agitator_patterns ap
          ON ap.pattern_id = ph.pattern_id
        WHERE ph.run_id = ?
        GROUP BY tv.paper_id, ph.pattern_id, ap.label
        """,
        (run_id,),
    ).fetchall()
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["paper_id"], []).append(
            {
                "pattern_id": row["pattern_id"],
                "label": row["label"],
                "score": float(row["max_score"] or 0.0),
            }
        )
    return grouped


def fetch_paper_metadata(connection: sqlite3.Connection) -> dict[str, dict]:
    rows = connection.execute(
        """
        SELECT paper_id, title, primary_category, published_at
        FROM papers
        """
    ).fetchall()
    return {
        row["paper_id"]: {
            "title": row["title"],
            "primary_category": row["primary_category"],
            "published_at": row["published_at"],
        }
        for row in rows
    }


def fetch_bridge_sources(connection: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT source_anchor_id, target_anchor_id, paper_id, bridge_score
        FROM bridge_candidates
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return [
        {
            "paper_id": row["paper_id"],
            "source_type": "bridge",
            "raw_score": float(row["bridge_score"] or 0.0),
            "anchor_ids": [row["source_anchor_id"], row["target_anchor_id"]],
            "pattern_id": None,
        }
        for row in rows
    ]


def fetch_composition_sources(connection: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT source_anchor_id, target_anchor_id, paper_id, composition_score
        FROM composition_candidates
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return [
        {
            "paper_id": row["paper_id"],
            "source_type": "composition",
            "raw_score": float(row["composition_score"] or 0.0),
            "anchor_ids": [row["source_anchor_id"], row["target_anchor_id"]],
            "pattern_id": None,
        }
        for row in rows
    ]


def fetch_transition_sources(connection: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT pattern_id, paper_id, transition_state_candidate_score
        FROM transition_state_candidates
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return [
        {
            "paper_id": row["paper_id"],
            "source_type": "transition_state",
            "raw_score": float(row["transition_state_candidate_score"] or 0.0),
            "anchor_ids": [],
            "pattern_id": row["pattern_id"],
        }
        for row in rows
    ]


def fetch_stranded_sources(connection: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT paper_id, resurfacing_score
        FROM stranded_resurfacing_candidates
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return [
        {
            "paper_id": row["paper_id"],
            "source_type": "stranded_qfin",
            "raw_score": float(row["resurfacing_score"] or 0.0),
            "anchor_ids": [],
            "pattern_id": None,
        }
        for row in rows
    ]


def fetch_probe_only_sources(probe_support: dict[str, list[dict]], far_realized_patterns: set[str]) -> list[dict]:
    rows = []
    for paper_id, supports in probe_support.items():
        for support in supports:
            if support["pattern_id"] not in far_realized_patterns:
                continue
            rows.append(
                {
                    "paper_id": paper_id,
                    "source_type": "probe",
                    "raw_score": float(support["score"] or 0.0),
                    "anchor_ids": [],
                    "pattern_id": support["pattern_id"],
                }
            )
    return rows


def best_capsule_match(source: dict, capsules: list[dict]) -> tuple[dict | None, float]:
    best_capsule = None
    best_score = 0.0
    anchor_set = set(source.get("anchor_ids", []))
    pattern_id = source.get("pattern_id")
    for capsule in capsules:
        score = 0.0
        anchor_matches = len(anchor_set.intersection(capsule.get("anchor_ids", [])))
        if anchor_matches:
            score += 0.65 * anchor_matches
            if anchor_matches >= 2:
                score += 0.35
        if pattern_id and pattern_id in set(capsule.get("pattern_ids", [])):
            score += 1.0
        if source["source_type"] == "stranded_qfin" and capsule["lane"] == "stranded_qfin":
            score += 0.9
        if source["source_type"] == "probe" and pattern_id in set(capsule.get("far_realized_patterns", [])):
            score += 0.8
        if score > best_score:
            best_score = score
            best_capsule = capsule
    return best_capsule, best_score


def outside_obvious_qfin_discourse(metadata: dict, is_realized_market: bool) -> bool:
    primary = (metadata.get("primary_category") or "").lower()
    return (not primary.startswith("q-fin")) and (not is_realized_market)


def translation_kind_for(source_type: str, capsule_score: float) -> str:
    if source_type in {"stranded_qfin", "transition_state"}:
        return "direct"
    if source_type in {"bridge", "composition"}:
        return "compositional" if capsule_score >= 1.0 else "speculative"
    return "speculative"


def summarize_far_from_realized(
    metadata: dict,
    is_realized_market: bool,
    far_supports: list[dict],
    source_type: str,
) -> str:
    reasons = []
    if not is_realized_market:
        reasons.append("not in realized_market corpus")
    primary = metadata.get("primary_category") or "unknown"
    if not primary.startswith("q-fin"):
        reasons.append(f"home domain {primary} is outside q-fin")
    if far_supports:
        best = max(far_supports, key=lambda item: item["score"])
        reasons.append(f"matched lexical-far probe {best['label']}")
    if source_type == "stranded_qfin":
        reasons.append("appears as stranded q-fin rather than realized market discourse")
    return "; ".join(reasons) if reasons else "close to realized-market discourse"


def build_candidates(
    sources: list[dict],
    capsules: list[dict],
    probe_support: dict[str, list[dict]],
    metadata_by_paper: dict[str, dict],
    realized_market_ids: set[str],
    negative_penalties: dict[str, float],
) -> list[dict]:
    aggregated: dict[str, dict] = {}
    far_realized_patterns = {
        pattern_id
        for capsule in capsules
        for pattern_id in capsule.get("far_realized_patterns", [])
    }
    for source in sources:
        paper_id = source["paper_id"]
        metadata = metadata_by_paper.get(paper_id)
        if metadata is None:
            continue
        far_supports = [
            support for support in probe_support.get(paper_id, [])
            if support["pattern_id"] in far_realized_patterns
        ]
        is_realized_market = paper_id in realized_market_ids
        capsule, challenge_affinity = best_capsule_match(source, capsules)
        if capsule is None or challenge_affinity <= 0.0:
            continue
        operator_affinity = normalized_operator_score(source["source_type"], float(source["raw_score"]))
        far_realized_affinity = max((support["score"] for support in far_supports), default=0.0)
        non_realized_bonus = 1.0 if not is_realized_market else 0.0
        non_qfin_bonus = 0.5 if not (metadata.get("primary_category") or "").startswith("q-fin") else 0.0
        negative_penalty = negative_penalties.get(paper_id, 0.0)
        realized_penalty = 0.8 if is_realized_market else 0.0
        score = challenge_affinity + operator_affinity + far_realized_affinity + non_realized_bonus + non_qfin_bonus - negative_penalty - realized_penalty
        candidate = {
            "paper_id": paper_id,
            "title": metadata["title"],
            "home_domain": home_domain(metadata["primary_category"]),
            "challenge_capsule_matched": capsule["capsule_id"],
            "translation_gap_score": round(score, 6),
            "why_far_from_realized": summarize_far_from_realized(metadata, is_realized_market, far_supports, source["source_type"]),
            "translation_kind": translation_kind_for(source["source_type"], challenge_affinity),
            "source_operator_family": source["source_type"],
            "outside_obvious_qfin_discourse": outside_obvious_qfin_discourse(metadata, is_realized_market),
            "support": {
                "challenge_affinity": round(challenge_affinity, 6),
                "operator_affinity": round(operator_affinity, 6),
                "far_realized_affinity": round(far_realized_affinity, 6),
                "non_realized_bonus": round(non_realized_bonus, 6),
                "non_qfin_bonus": round(non_qfin_bonus, 6),
                "negative_penalty": round(negative_penalty, 6),
                "realized_penalty": round(realized_penalty, 6),
            },
        }
        existing = aggregated.get(paper_id)
        if existing is None or candidate["translation_gap_score"] > existing["translation_gap_score"]:
            aggregated[paper_id] = candidate

    ranked = sorted(
        aggregated.values(),
        key=lambda item: (
            -item["translation_gap_score"],
            item["challenge_capsule_matched"],
            item["paper_id"],
        ),
    )
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    return ranked


def count_by_key(rows: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def render_report(top_rows: list[dict], metrics: dict) -> str:
    lines = [
        "# DS1 Translation-Gap Search",
        "",
        "This study ranks papers that are mechanically close to challenge capsules while remaining far from pre-2024 realized-market discourse.",
        "",
        "## Stop / Go",
        "",
        f"- outside obvious q-fin / trading discourse in top 100: `{metrics['outside_obvious_qfin_count']}`",
        f"- success threshold met: `{str(metrics['success']).lower()}`",
        "",
        "## Candidate-Family Diversity",
        "",
    ]
    for capsule, count in metrics["counts_by_capsule"].items():
        lines.append(f"- {capsule}: `{count}`")
    lines.extend(["", "## Translation-Kind Mix", ""])
    for kind, count in metrics["counts_by_translation_kind"].items():
        lines.append(f"- {kind}: `{count}`")
    lines.extend(["", "## Home-Domain Mix", ""])
    for domain, count in metrics["counts_by_home_domain"].items():
        lines.append(f"- {domain}: `{count}`")
    lines.extend(["", "## Top 20 Preview", ""])
    for row in top_rows[:20]:
        lines.extend(
            [
                f"- `{row['paper_id']}` | `{row['challenge_capsule_matched']}` | `{row['translation_kind']}` | score `{row['translation_gap_score']}`",
                f"  title: {row['title']}",
                f"  home domain: {row['home_domain']}",
                f"  far-from-realized: {row['why_far_from_realized']}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main():
    args = parse_args()
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    capsules_payload = load_yaml(Path(args.challenge_capsules_path).resolve(), {"capsules": []})
    capsules = capsules_payload.get("capsules", [])

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        metadata_by_paper = fetch_paper_metadata(connection)
        realized_market_ids = fetch_realized_market_ids(connection, args.membership_run_id)
        negative_penalties = fetch_negative_space_penalties(connection, args.negative_space_run_id)
        probe_support = fetch_probe_support(connection, args.probe_run_id)
        far_realized_patterns = {
            pattern_id
            for capsule in capsules
            for pattern_id in capsule.get("far_realized_patterns", [])
        }
        sources = []
        sources.extend(fetch_bridge_sources(connection, args.bridge_run_id))
        sources.extend(fetch_composition_sources(connection, args.composition_run_id))
        sources.extend(fetch_transition_sources(connection, args.transition_run_id))
        sources.extend(fetch_stranded_sources(connection, args.resurfacing_run_id))
        sources.extend(fetch_probe_only_sources(probe_support, far_realized_patterns))
        ranked = build_candidates(
            sources=sources,
            capsules=capsules,
            probe_support=probe_support,
            metadata_by_paper=metadata_by_paper,
            realized_market_ids=realized_market_ids,
            negative_penalties=negative_penalties,
        )[: args.top_k]

        metrics = {
            "top_k": len(ranked),
            "outside_obvious_qfin_count": sum(1 for row in ranked if row["outside_obvious_qfin_discourse"]),
            "counts_by_capsule": count_by_key(ranked, "challenge_capsule_matched"),
            "counts_by_translation_kind": count_by_key(ranked, "translation_kind"),
            "counts_by_home_domain": count_by_key(ranked, "home_domain"),
        }
        metrics["success"] = metrics["outside_obvious_qfin_count"] >= 20

        jsonl_path = reports_dir / "ds1-translation-gap-candidates.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in ranked:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown_path = reports_dir / "ds1-translation-gap-report.md"
        markdown_path.write_text(render_report(ranked, metrics), encoding="utf-8")

        log_run_event(
            connection,
            "ds1-translation-gap-search",
            "diamond_study",
            "completed",
            {
                "reports_dir": str(reports_dir),
                "top_k": len(ranked),
                "outside_obvious_qfin_count": metrics["outside_obvious_qfin_count"],
                "success": metrics["success"],
            },
        )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
