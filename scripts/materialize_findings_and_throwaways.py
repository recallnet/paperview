#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
PUBLISHED_ROOT = ROOT / "reports" / "published"
POSITIVE_CLASSIFICATIONS = {
    "TRANSLATION_CANDIDATE",
    "COMPOSITIONAL_CANDIDATE",
    "STRANDED_QFIN_RESULT",
    "TRANSITION_SEAM",
}
NEAR_MISS_OPERATOR_FAMILIES = (
    "bridge",
    "composition",
    "contrast",
    "negative_space",
    "transition_state",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize the canonical findings and throwaways report.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="findings-and-throwaways-20260328")
    parser.add_argument("--shortlist-run-id", default="shortlist-materialization-20260328")
    parser.add_argument("--interpretation-source", choices=("selective", "enhanced", "diamond"), default="selective")
    parser.add_argument("--interpretation-run-id", default="selective-interpretation-ingestion-20260328")
    parser.add_argument("--interpretation-rejections-path", default=None)
    parser.add_argument("--bridge-run-id", default="bridge-materialization-20260328")
    parser.add_argument("--composition-run-id", default="composition-materialization-20260328")
    parser.add_argument("--contrast-run-id", default="contrast-materialization-20260328")
    parser.add_argument("--negative-space-run-id", default="negative-space-materialization-20260328")
    parser.add_argument("--transition-run-id", default="transition-state-candidate-materialization-20260328")
    parser.add_argument("--resurfacing-run-id", default="stranded-resurfacing-materialization-20260328")
    parser.add_argument("--stranded-ledger-run-id", default="stranded-result-ledger-20260328")
    parser.add_argument("--output-dir", default=None)
    # @context decision -- the mandatory human-facing findings surface is still required every run,
    # but the checked-in canonical location is reports/published rather than the repo root.
    parser.add_argument("--root-markdown-path", default=str(PUBLISHED_ROOT / "findings_and_throwaways.md"))
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def default_rejections_path(interpretation_run_id: str) -> Path:
    if interpretation_run_id.startswith("enhanced-interpretation-ingestion-"):
        return DEFAULT_OUTPUT_ROOT / interpretation_run_id / "enhanced_interpretation_rejections.jsonl"
    return DEFAULT_OUTPUT_ROOT / interpretation_run_id / "interpretation_rejections.jsonl"


def fetch_positive_findings(connection: sqlite3.Connection, shortlist_run_id: str, interpretation_run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          si.packet_kind AS operator_family,
          si.shortlist_id,
          si.shortlist_rank,
          si.item_type,
          si.item_ref,
          rp.title,
          interp.classification,
          interp.result_summary,
          interp.first_step,
          interp.why_stranded_or_unrealized,
          interp.modern_equivalent,
          interp.confidence
        FROM selective_interpretations interp
        JOIN shortlist_items si
          ON si.run_id = interp.shortlist_run_id
         AND si.shortlist_id = interp.shortlist_id
        JOIN review_packets rp
          ON rp.run_id = si.packet_run_id
         AND rp.packet_kind = si.packet_kind
         AND rp.item_ref = si.packet_item_ref
        WHERE interp.run_id = ?
          AND si.run_id = ?
        ORDER BY si.shortlist_rank ASC, si.shortlist_id ASC
        """,
        (interpretation_run_id, shortlist_run_id),
    ).fetchall()
    findings = []
    for row in rows:
        if row["classification"] not in POSITIVE_CLASSIFICATIONS:
            continue
        findings.append(
            {
                "section": "accepted",
                "operator_family": row["operator_family"],
                "shortlist_id": row["shortlist_id"],
                "shortlist_rank": int(row["shortlist_rank"]),
                "item_type": row["item_type"],
                "item_ref": row["item_ref"],
                "title": row["title"],
                "classification": row["classification"],
                "confidence": row["confidence"],
                "result_summary": row["result_summary"],
                "first_step": row["first_step"],
                "why": row["why_stranded_or_unrealized"],
                "modern_equivalent": row["modern_equivalent"],
            }
        )
    return findings


def fetch_positive_enhanced_findings(connection: sqlite3.Connection, interpretation_run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          operator_family,
          batch_item_id,
          family_rank,
          source_ref,
          packet_title,
          classification,
          result_summary,
          first_step,
          why_stranded_or_unrealized,
          modern_equivalent,
          confidence
        FROM enhanced_interpretations
        WHERE run_id = ?
        ORDER BY operator_family ASC, family_rank ASC, batch_item_id ASC
        """,
        (interpretation_run_id,),
    ).fetchall()
    findings = []
    for row in rows:
        if row["classification"] not in POSITIVE_CLASSIFICATIONS:
            continue
        findings.append(
            {
                "section": "accepted",
                "operator_family": row["operator_family"],
                "shortlist_id": row["batch_item_id"],
                "shortlist_rank": int(row["family_rank"]),
                "item_type": row["operator_family"],
                "item_ref": row["source_ref"],
                "title": row["packet_title"],
                "classification": row["classification"],
                "confidence": row["confidence"],
                "result_summary": row["result_summary"],
                "first_step": row["first_step"],
                "why": row["why_stranded_or_unrealized"],
                "modern_equivalent": row["modern_equivalent"],
            }
        )
    findings.sort(key=lambda row: (row["operator_family"], row["shortlist_rank"], row["shortlist_id"]))
    return findings


def fetch_positive_diamond_findings(connection: sqlite3.Connection, interpretation_run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          batch_item_id,
          lane_family,
          operator_family,
          shortlist_rank,
          source_ref,
          packet_title,
          classification,
          result_summary,
          first_test,
          why_stranded_or_unrealized,
          modern_equivalent,
          confidence
        FROM diamond_interpretations
        WHERE run_id = ?
        ORDER BY shortlist_rank ASC, batch_item_id ASC
        """,
        (interpretation_run_id,),
    ).fetchall()
    findings = []
    for row in rows:
        if row["classification"] not in POSITIVE_CLASSIFICATIONS:
            continue
        findings.append(
            {
                "section": "accepted",
                "operator_family": row["lane_family"],
                "shortlist_id": row["batch_item_id"],
                "shortlist_rank": int(row["shortlist_rank"]),
                "item_type": row["operator_family"],
                "item_ref": row["source_ref"],
                "title": row["packet_title"],
                "classification": row["classification"],
                "confidence": row["confidence"],
                "result_summary": row["result_summary"],
                "first_step": row["first_test"],
                "why": row["why_stranded_or_unrealized"],
                "modern_equivalent": row["modern_equivalent"],
            }
        )
    return findings


def fetch_shortlist_lookup(connection: sqlite3.Connection, shortlist_run_id: str) -> dict[str, dict]:
    rows = connection.execute(
        """
        SELECT
          si.shortlist_id,
          si.packet_kind,
          si.shortlist_rank,
          rp.title
        FROM shortlist_items si
        JOIN review_packets rp
          ON rp.run_id = si.packet_run_id
         AND rp.packet_kind = si.packet_kind
         AND rp.item_ref = si.packet_item_ref
        WHERE si.run_id = ?
        """,
        (shortlist_run_id,),
    ).fetchall()
    return {
        row["shortlist_id"]: {
            "operator_family": row["packet_kind"],
            "shortlist_rank": int(row["shortlist_rank"]),
            "title": row["title"],
        }
        for row in rows
    }


def load_rejections(path: Path, shortlist_lookup: dict[str, dict], top_k: int) -> list[dict]:
    if not path.exists():
        return []
    grouped: dict[str, list[dict]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            shortlist_id = payload.get("shortlist_id")
            lookup = shortlist_lookup.get(shortlist_id or "", {})
            operator_family = lookup.get("operator_family", "unknown")
            grouped.setdefault(operator_family, []).append(
                {
                    "section": "rejected",
                    "operator_family": operator_family,
                    "shortlist_id": shortlist_id,
                    "shortlist_rank": lookup.get("shortlist_rank"),
                    "title": lookup.get("title"),
                    "reason": payload["reason"],
                    "line_number": int(payload["line_number"]),
                }
            )
    rejected = []
    for operator_family, rows in grouped.items():
        rows.sort(
            key=lambda item: (
                item["shortlist_rank"] if item["shortlist_rank"] is not None else 10**9,
                item["line_number"],
            )
        )
        rejected.extend(rows[:top_k])
    return rejected


def load_enhanced_rejections(path: Path, batch_lookup: dict[str, dict], top_k: int) -> list[dict]:
    if not path.exists():
        return []
    grouped: dict[str, list[dict]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            batch_item_id = payload.get("batch_item_id")
            lookup = batch_lookup.get(batch_item_id or "", {})
            operator_family = lookup.get("operator_family", "unknown")
            grouped.setdefault(operator_family, []).append(
                {
                    "section": "rejected",
                    "operator_family": operator_family,
                    "shortlist_id": batch_item_id,
                    "shortlist_rank": lookup.get("shortlist_rank"),
                    "title": lookup.get("title"),
                    "reason": payload["reason"],
                    "line_number": int(payload["line_number"]),
                }
            )
    rejected = []
    for operator_family, rows in grouped.items():
        rows.sort(
            key=lambda item: (
                item["shortlist_rank"] if item["shortlist_rank"] is not None else 10**9,
                item["line_number"],
            )
        )
        rejected.extend(rows[:top_k])
    return rejected


def fetch_enhanced_batch_lookup(connection: sqlite3.Connection, interpretation_run_id: str) -> dict[str, dict]:
    rows = connection.execute(
        """
        SELECT
          batch_item_id,
          operator_family,
          family_rank,
          packet_title
        FROM enhanced_interpretations
        WHERE run_id = ?
        """,
        (interpretation_run_id,),
    ).fetchall()
    return {
        row["batch_item_id"]: {
            "operator_family": row["operator_family"],
            "shortlist_rank": int(row["family_rank"]),
            "title": row["packet_title"],
        }
        for row in rows
    }


def fetch_diamond_batch_lookup(connection: sqlite3.Connection, interpretation_run_id: str) -> dict[str, dict]:
    rows = connection.execute(
        """
        SELECT
          batch_item_id,
          lane_family,
          shortlist_rank,
          packet_title
        FROM diamond_interpretations
        WHERE run_id = ?
        """,
        (interpretation_run_id,),
    ).fetchall()
    return {
        row["batch_item_id"]: {
            "operator_family": row["lane_family"],
            "shortlist_rank": int(row["shortlist_rank"]),
            "title": row["packet_title"],
        }
        for row in rows
    }


def fetch_near_misses(connection: sqlite3.Connection, args) -> list[dict]:
    families = [
        (
            "bridge",
            """
            SELECT
              'bridge' AS operator_family,
              bc.source_anchor_id || ' x ' || bc.target_anchor_id AS operator_label,
              bc.paper_id,
              COALESCE(p.title, bc.paper_id) AS title,
              bc.bridge_score AS score,
              bc.bridge_rank AS operator_rank
            FROM bridge_candidates bc
            JOIN papers p
              ON p.paper_id = bc.paper_id
            WHERE bc.run_id = ?
            ORDER BY bc.bridge_score DESC, bc.bridge_rank ASC, bc.paper_id ASC
            LIMIT ?
            """,
            args.bridge_run_id,
        ),
        (
            "composition",
            """
            SELECT
              'composition' AS operator_family,
              cc.source_anchor_id || ' x ' || cc.target_anchor_id AS operator_label,
              cc.paper_id,
              COALESCE(p.title, cc.paper_id) AS title,
              cc.composition_score AS score,
              cc.composition_rank AS operator_rank
            FROM composition_candidates cc
            JOIN papers p
              ON p.paper_id = cc.paper_id
            WHERE cc.run_id = ?
            ORDER BY cc.composition_score DESC, cc.composition_rank ASC, cc.paper_id ASC
            LIMIT ?
            """,
            args.composition_run_id,
        ),
        (
            "contrast",
            """
            SELECT
              'contrast' AS operator_family,
              ap.label AS operator_label,
              cc.paper_id,
              COALESCE(p.title, cc.paper_id) AS title,
              cc.contrast_score AS score,
              cc.contrast_rank AS operator_rank
            FROM contrast_candidates cc
            JOIN papers p
              ON p.paper_id = cc.paper_id
            JOIN agitator_patterns ap
              ON ap.pattern_id = cc.pattern_id
            WHERE cc.run_id = ?
            ORDER BY cc.contrast_score DESC, cc.contrast_rank ASC, cc.paper_id ASC
            LIMIT ?
            """,
            args.contrast_run_id,
        ),
        (
            "negative_space",
            """
            SELECT
              'negative_space' AS operator_family,
              a.label AS operator_label,
              nc.paper_id,
              COALESCE(p.title, nc.paper_id) AS title,
              nc.negative_space_score AS score,
              nc.negative_rank AS operator_rank
            FROM negative_space_candidates nc
            JOIN papers p
              ON p.paper_id = nc.paper_id
            JOIN anchors a
              ON a.anchor_id = nc.anchor_id
            WHERE nc.run_id = ?
            ORDER BY nc.negative_space_score DESC, nc.negative_rank ASC, nc.paper_id ASC
            LIMIT ?
            """,
            args.negative_space_run_id,
        ),
        (
            "transition_state",
            """
            SELECT
              'transition_state' AS operator_family,
              ap.label AS operator_label,
              tc.paper_id,
              COALESCE(p.title, tc.paper_id) AS title,
              tc.transition_state_candidate_score AS score,
              tc.transition_state_rank AS operator_rank
            FROM transition_state_candidates tc
            JOIN papers p
              ON p.paper_id = tc.paper_id
            JOIN agitator_patterns ap
              ON ap.pattern_id = tc.pattern_id
            WHERE tc.run_id = ?
            ORDER BY tc.transition_state_candidate_score DESC, tc.transition_state_rank ASC, tc.paper_id ASC
            LIMIT ?
            """,
            args.transition_run_id,
        ),
    ]
    near_misses = []
    for operator_family, query, run_id in families:
        rows = connection.execute(query, (run_id, args.top_k)).fetchall()
        for row in rows:
            near_misses.append(
                {
                    "section": "near_miss",
                    "operator_family": operator_family,
                    "operator_label": row["operator_label"],
                    "paper_id": row["paper_id"],
                    "title": row["title"],
                    "score": round(float(row["score"] or 0.0), 6),
                    "operator_rank": int(row["operator_rank"]),
                }
            )
    return near_misses


def failure_reason(shortlist_id: str | None, classification: str | None) -> str:
    if shortlist_id is None:
        return "not_shortlisted_for_interpretation"
    if classification is None:
        return "not_interpreted"
    if classification != "STRANDED_QFIN_RESULT":
        return f"interpretation_classification:{classification}"
    return "missing_from_stranded_result_ledger"


def fetch_stranded_qfin_failures(
    connection: sqlite3.Connection,
    shortlist_run_id: str,
    interpretation_run_id: str,
    resurfacing_run_id: str,
    stranded_ledger_run_id: str,
    top_k: int,
) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          src.paper_id,
          src.resurfacing_score,
          src.resurfacing_rank,
          COALESCE(p.title, src.paper_id) AS title,
          si.shortlist_id,
          interp.classification
        FROM stranded_resurfacing_candidates src
        JOIN papers p
          ON p.paper_id = src.paper_id
        LEFT JOIN shortlist_items si
          ON si.run_id = ?
         AND si.item_type = 'paper'
         AND si.item_ref = src.paper_id
        LEFT JOIN selective_interpretations interp
          ON interp.run_id = ?
         AND interp.shortlist_id = si.shortlist_id
        LEFT JOIN stranded_result_ledger ledger
          ON ledger.run_id = ?
         AND ledger.paper_id = src.paper_id
        WHERE src.run_id = ?
          AND ledger.paper_id IS NULL
        ORDER BY src.resurfacing_rank ASC, src.paper_id ASC
        LIMIT ?
        """,
        (shortlist_run_id, interpretation_run_id, stranded_ledger_run_id, resurfacing_run_id, top_k),
    ).fetchall()
    failures = []
    for row in rows:
        failures.append(
            {
                "section": "stranded_qfin_failure",
                "operator_family": "stranded_resurfacing",
                "paper_id": row["paper_id"],
                "title": row["title"],
                "resurfacing_score": round(float(row["resurfacing_score"] or 0.0), 6),
                "resurfacing_rank": int(row["resurfacing_rank"]),
                "shortlist_id": row["shortlist_id"],
                "classification": row["classification"],
                "failure_reason": failure_reason(row["shortlist_id"], row["classification"]),
            }
        )
    return failures


def fetch_enhanced_stranded_qfin_failures(
    connection: sqlite3.Connection,
    interpretation_run_id: str,
    resurfacing_run_id: str,
    stranded_ledger_run_id: str,
    top_k: int,
) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          src.paper_id,
          src.resurfacing_score,
          src.resurfacing_rank,
          COALESCE(p.title, src.paper_id) AS title,
          interp.batch_item_id,
          interp.classification
        FROM stranded_resurfacing_candidates src
        JOIN papers p
          ON p.paper_id = src.paper_id
        LEFT JOIN enhanced_interpretations interp
          ON interp.run_id = ?
         AND interp.operator_family = 'stranded_qfin'
         AND interp.source_ref = src.paper_id
        LEFT JOIN stranded_result_ledger ledger
          ON ledger.run_id = ?
         AND ledger.paper_id = src.paper_id
        WHERE src.run_id = ?
          AND ledger.paper_id IS NULL
        ORDER BY src.resurfacing_rank ASC, src.paper_id ASC
        LIMIT ?
        """,
        (interpretation_run_id, stranded_ledger_run_id, resurfacing_run_id, top_k),
    ).fetchall()
    failures = []
    for row in rows:
        failures.append(
            {
                "section": "stranded_qfin_failure",
                "operator_family": "stranded_resurfacing",
                "paper_id": row["paper_id"],
                "title": row["title"],
                "resurfacing_score": round(float(row["resurfacing_score"] or 0.0), 6),
                "resurfacing_rank": int(row["resurfacing_rank"]),
                "shortlist_id": row["batch_item_id"],
                "classification": row["classification"],
                "failure_reason": failure_reason(row["batch_item_id"], row["classification"]),
            }
        )
    return failures


def fetch_diamond_stranded_qfin_failures(
    connection: sqlite3.Connection,
    interpretation_run_id: str,
    resurfacing_run_id: str,
    stranded_ledger_run_id: str,
    top_k: int,
) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          src.paper_id,
          src.resurfacing_score,
          src.resurfacing_rank,
          COALESCE(p.title, src.paper_id) AS title,
          interp.batch_item_id,
          interp.classification
        FROM stranded_resurfacing_candidates src
        JOIN papers p
          ON p.paper_id = src.paper_id
        LEFT JOIN diamond_interpretations interp
          ON interp.run_id = ?
         AND interp.lane_family = 'stranded_qfin'
         AND interp.source_ref = src.paper_id
        LEFT JOIN stranded_result_ledger ledger
          ON ledger.run_id = ?
         AND ledger.paper_id = src.paper_id
        WHERE src.run_id = ?
          AND ledger.paper_id IS NULL
        ORDER BY src.resurfacing_rank ASC, src.paper_id ASC
        LIMIT ?
        """,
        (interpretation_run_id, stranded_ledger_run_id, resurfacing_run_id, top_k),
    ).fetchall()
    failures = []
    for row in rows:
        failures.append(
            {
                "section": "stranded_qfin_failure",
                "operator_family": "stranded_resurfacing",
                "paper_id": row["paper_id"],
                "title": row["title"],
                "resurfacing_score": round(float(row["resurfacing_score"] or 0.0), 6),
                "resurfacing_rank": int(row["resurfacing_rank"]),
                "shortlist_id": row["batch_item_id"],
                "classification": row["classification"],
                "failure_reason": failure_reason(row["batch_item_id"], row["classification"]),
            }
        )
    return failures


def render_markdown(
    accepted: list[dict],
    rejected: list[dict],
    near_misses: list[dict],
    stranded_failures: list[dict],
) -> str:
    lines = [
        "# Findings and Throwaways",
        "",
        f"- accepted findings: `{len(accepted)}`",
        f"- rejected interpretations: `{len(rejected)}`",
        f"- near misses: `{len(near_misses)}`",
        f"- stranded q-fin failures: `{len(stranded_failures)}`",
        "",
        "## Accepted Findings",
        "",
    ]
    accepted_by_family = {
        family: []
        for family in ("bridge", "composition", "stranded_qfin", "transition_state", "market_design", "settlement_resolution", "participant_pathologies", "state_graph")
    }
    for row in accepted:
        accepted_by_family.setdefault(row["operator_family"], []).append(row)
    for family, rows in accepted_by_family.items():
        lines.append(f"### {family}")
        lines.append("")
        if not rows:
            lines.append("- none")
            lines.append("")
            continue
        for row in rows:
            lines.extend(
                [
                    f"- `{row['shortlist_id']}` | `{row['classification']}` | `{row['confidence']}`",
                    f"  title: {row['title']}",
                    f"  result: {row['result_summary']}",
                    f"  clue: {row['modern_equivalent']}",
                    f"  next step: {row['first_step']}",
                ]
            )
        lines.append("")

    lines.extend(["## Rejected Interpretations", ""])
    rejected_families = ["bridge", "composition", "stranded_qfin", "transition_state", "market_design", "settlement_resolution", "participant_pathologies", "state_graph", "unknown"]
    for family in rejected_families:
        rows = [row for row in rejected if row["operator_family"] == family]
        lines.append(f"### {family}")
        lines.append("")
        if not rows:
            lines.append("- none")
            lines.append("")
            continue
        for row in rows:
            label = row["shortlist_id"] or "unresolved"
            title = row["title"] or "no shortlist match"
            lines.extend(
                [
                    f"- `{label}` | reason `{row['reason']}`",
                    f"  title: {title}",
                ]
            )
        lines.append("")

    lines.extend(["## Near Misses By Operator", ""])
    for family in NEAR_MISS_OPERATOR_FAMILIES:
        rows = [row for row in near_misses if row["operator_family"] == family]
        lines.append(f"### {family}")
        lines.append("")
        if not rows:
            lines.append("- none")
            lines.append("")
            continue
        for row in rows:
            lines.extend(
                [
                    f"- `{row['paper_id']}` | score `{row['score']}` | rank `{row['operator_rank']}`",
                    f"  title: {row['title']}",
                    f"  operator clue: {row['operator_label']}",
                ]
            )
        lines.append("")

    lines.extend(["## Stranded Q-Fin Failures", ""])
    if not stranded_failures:
        lines.extend(["- none", ""])
    else:
        for row in stranded_failures:
            lines.extend(
                [
                    f"- `{row['paper_id']}` | resurfacing `{row['resurfacing_score']}` | reason `{row['failure_reason']}`",
                    f"  title: {row['title']}",
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    root_markdown_path = Path(args.root_markdown_path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rejections_path = (
        Path(args.interpretation_rejections_path).resolve()
        if args.interpretation_rejections_path
        else default_rejections_path(args.interpretation_run_id)
    )

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        log_run_event(
            connection,
            args.run_id,
            "findings_and_throwaways",
            "started",
            {
                "shortlist_run_id": args.shortlist_run_id,
                "interpretation_source": args.interpretation_source,
                "interpretation_run_id": args.interpretation_run_id,
                "interpretation_rejections_path": str(rejections_path),
                "stranded_ledger_run_id": args.stranded_ledger_run_id,
                "resurfacing_run_id": args.resurfacing_run_id,
                "top_k": args.top_k,
            },
        )
        if args.interpretation_source == "selective":
            accepted = fetch_positive_findings(connection, args.shortlist_run_id, args.interpretation_run_id)
            shortlist_lookup = fetch_shortlist_lookup(connection, args.shortlist_run_id)
            # @context decision -- Rejection reasons only exist as the S12 ingestion artifact, not in a
            # canonical table. S21 intentionally reads the checked-in JSONL directly so the report keeps
            # the exact rejection contract rather than reconstructing or weakening it from derived state.
            rejected = load_rejections(rejections_path, shortlist_lookup, args.top_k)
            stranded_failures = fetch_stranded_qfin_failures(
                connection,
                args.shortlist_run_id,
                args.interpretation_run_id,
                args.resurfacing_run_id,
                args.stranded_ledger_run_id,
                args.top_k,
            )
        elif args.interpretation_source == "enhanced":
            accepted = fetch_positive_enhanced_findings(connection, args.interpretation_run_id)
            batch_lookup = fetch_enhanced_batch_lookup(connection, args.interpretation_run_id)
            # @context decision -- S24 rematerialization must report the enhanced interpretation run
            # exactly as ingested, so enhanced rejection rows still come from the checked-in JSONL
            # artifact rather than being inferred from missing table rows.
            rejected = load_enhanced_rejections(rejections_path, batch_lookup, args.top_k)
            stranded_failures = fetch_enhanced_stranded_qfin_failures(
                connection,
                args.interpretation_run_id,
                args.resurfacing_run_id,
                args.stranded_ledger_run_id,
                args.top_k,
            )
        else:
            accepted = fetch_positive_diamond_findings(connection, args.interpretation_run_id)
            batch_lookup = fetch_diamond_batch_lookup(connection, args.interpretation_run_id)
            rejected = load_enhanced_rejections(rejections_path, batch_lookup, args.top_k)
            stranded_failures = fetch_diamond_stranded_qfin_failures(
                connection,
                args.interpretation_run_id,
                args.resurfacing_run_id,
                args.stranded_ledger_run_id,
                args.top_k,
            )
        near_misses = fetch_near_misses(connection, args)

        report_rows = accepted + rejected + near_misses + stranded_failures
        jsonl_path = output_dir / "findings_and_throwaways.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in report_rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown_text = render_markdown(accepted, rejected, near_misses, stranded_failures)
        markdown_path = output_dir / "findings_and_throwaways.md"
        markdown_path.write_text(markdown_text, encoding="utf-8")
        # @context decision -- S28 makes findings_and_throwaways.md a mandatory every-run surface
        # at repo root so accepted evidence is not trapped only under per-run directories.
        root_markdown_path.write_text(markdown_text, encoding="utf-8")

        metrics = {
            "run_id": args.run_id,
            "shortlist_run_id": args.shortlist_run_id,
            "interpretation_source": args.interpretation_source,
            "interpretation_run_id": args.interpretation_run_id,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "near_miss_count": len(near_misses),
            "stranded_qfin_failure_count": len(stranded_failures),
            "accepted_by_operator": {
                family: sum(1 for row in accepted if row["operator_family"] == family)
                for family in sorted({row["operator_family"] for row in accepted} | {"bridge", "composition", "stranded_qfin", "transition_state", "market_design", "settlement_resolution", "participant_pathologies", "state_graph"})
            },
            "rejected_by_operator": {
                family: sum(1 for row in rejected if row["operator_family"] == family)
                for family in sorted({row["operator_family"] for row in rejected} | {"bridge", "composition", "stranded_qfin", "transition_state", "market_design", "settlement_resolution", "participant_pathologies", "state_graph", "unknown"})
            },
            "near_miss_by_operator": {
                family: sum(1 for row in near_misses if row["operator_family"] == family)
                for family in NEAR_MISS_OPERATOR_FAMILIES
            },
            "operator_families_covered": sorted(set(NEAR_MISS_OPERATOR_FAMILIES) | {"stranded_resurfacing"}),
            "root_markdown_path": str(root_markdown_path),
        }
        metrics_path = output_dir / "findings_and_throwaways_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "findings_and_throwaways", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
