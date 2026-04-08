#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_RUNS_ROOT = ROOT / "data" / "structural-analogy" / "runs"
PUBLISHED_ROOT = ROOT / "reports" / "published"
POSITIVE_CLASSIFICATIONS = {
    "TRANSLATION_CANDIDATE",
    "COMPOSITIONAL_CANDIDATE",
    "STRANDED_QFIN_RESULT",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize the canonical v2 run summary.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="run-summary-20260329")
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--shortlist-run-id", default="shortlist-materialization-20260328")
    parser.add_argument("--enhanced-interpretation-run-id", default="enhanced-interpretation-ingestion-20260328-broadened")
    parser.add_argument("--unrealized-run-id", default="unrealized-ideas-index-broadened-20260328")
    parser.add_argument("--stranded-run-id", default="stranded-result-ledger-broadened-20260328")
    parser.add_argument("--transition-run-id", default="transition-state-ledger-broadened-20260328")
    parser.add_argument("--findings-run-id", default="findings-and-throwaways-broadened-20260328")
    # @context decision -- run summary is still the S28 truth checkpoint, but the checked-in
    # publication copy now lives under reports/published with the other exported surfaces.
    parser.add_argument("--output-json-path", default=str(PUBLISHED_ROOT / "run_summary.json"))
    parser.add_argument("--output-md-path", default=str(PUBLISHED_ROOT / "run_summary.md"))
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"missing_required_artifact:{path}")
    return path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def fetch_accepted_interpretations(connection: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT batch_item_id, operator_family, classification
        FROM enhanced_interpretations
        WHERE run_id = ?
          AND classification IN ('TRANSLATION_CANDIDATE', 'COMPOSITIONAL_CANDIDATE', 'STRANDED_QFIN_RESULT')
        ORDER BY operator_family ASC, batch_item_id ASC
        """,
        (run_id,),
    ).fetchall()
    return [
        {
            "batch_item_id": row["batch_item_id"],
            "operator_family": row["operator_family"],
            "classification": row["classification"],
        }
        for row in rows
    ]


def count_by_key(rows: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def build_summary(
    shortlist_metrics: dict,
    enhanced_metrics: dict,
    accepted_interpretations: list[dict],
    unrealized_metrics: dict,
    unrealized_rows: list[dict],
    stranded_metrics: dict,
    stranded_rows: list[dict],
    transition_metrics: dict,
    transition_rows: list[dict],
    findings_metrics: dict,
    findings_rows: list[dict],
    run_ids: dict,
) -> dict:
    findings_accepted_rows = [row for row in findings_rows if row.get("section") == "accepted"]
    findings_accepted_ids = {str(row["shortlist_id"]) for row in findings_accepted_rows}
    accepted_ids = {row["batch_item_id"] for row in accepted_interpretations}

    publication_items = []
    for row in unrealized_rows:
        publication_items.append({"publication_item_id": row["publication_item_id"], "lane": row["item_type"]})
    for row in stranded_rows:
        publication_items.append({"publication_item_id": row["publication_item_id"], "lane": "stranded_qfin"})
    for row in transition_rows:
        publication_items.append({"publication_item_id": row["publication_item_id"], "lane": "transition_state"})
    publication_ids = {row["publication_item_id"] for row in publication_items}

    accepted_not_in_findings = sorted(accepted_ids - findings_accepted_ids)
    accepted_not_in_publication = sorted(accepted_ids - publication_ids)
    publication_not_in_findings = sorted(publication_ids - findings_accepted_ids)

    # @context decision -- S28 is the canonical truth checkpoint. Reconciliation must be driven by
    # accepted interpretation ids versus findings/publication ids so hidden accepted evidence shows
    # up as a concrete failure surface instead of being lost in markdown summaries.
    return {
        "run_ids": run_ids,
        "counts": {
            "shortlist_count": int(shortlist_metrics.get("shortlist_count", 0)),
            "enhanced_interpretation_accepted_count": int(enhanced_metrics.get("accepted_count", 0)),
            "enhanced_interpretation_rejected_count": int(enhanced_metrics.get("rejected_count", 0)),
            "findings_accepted_count": int(findings_metrics.get("accepted_count", 0)),
            "findings_rejected_count": int(findings_metrics.get("rejected_count", 0)),
            "findings_near_miss_count": int(findings_metrics.get("near_miss_count", 0)),
            "findings_stranded_failure_count": int(findings_metrics.get("stranded_qfin_failure_count", 0)),
            "unrealized_entry_count": int(unrealized_metrics.get("entry_count", 0)),
            "stranded_entry_count": int(stranded_metrics.get("entry_count", 0)),
            "transition_entry_count": int(transition_metrics.get("entry_count", 0)),
            "published_entry_count": len(publication_items),
        },
        "accepted_by_lane": count_by_key(accepted_interpretations, "operator_family"),
        "published_by_lane": count_by_key(publication_items, "lane"),
        "reconciliation": {
            "accepted_interpretation_ids": sorted(accepted_ids),
            "findings_accepted_ids": sorted(findings_accepted_ids),
            "published_ids": sorted(publication_ids),
            "accepted_not_in_findings": accepted_not_in_findings,
            "accepted_not_in_publication": accepted_not_in_publication,
            "publication_not_in_findings": publication_not_in_findings,
            "all_accepted_items_exposed": not accepted_not_in_findings and not accepted_not_in_publication,
        },
    }


def render_markdown(summary: dict) -> str:
    counts = summary["counts"]
    reconciliation = summary["reconciliation"]
    lines = [
        "# Canonical Run Summary",
        "",
        "This is the authoritative count-reconciliation surface for the current broadened arXiv-only run.",
        "",
        "## Active Runs",
        "",
    ]
    for key, value in summary["run_ids"].items():
        lines.append(f"- {key.replace('_', ' ')}: `{value}`")

    lines.extend(
        [
            "",
            "## Reconciled Counts",
            "",
            f"- shortlist: `{counts['shortlist_count']}`",
            f"- accepted enhanced interpretations: `{counts['enhanced_interpretation_accepted_count']}`",
            f"- rejected enhanced interpretations: `{counts['enhanced_interpretation_rejected_count']}`",
            f"- findings accepted rows: `{counts['findings_accepted_count']}`",
            f"- findings rejected rows: `{counts['findings_rejected_count']}`",
            f"- findings near misses: `{counts['findings_near_miss_count']}`",
            f"- stranded q-fin failures: `{counts['findings_stranded_failure_count']}`",
            f"- unrealized index entries: `{counts['unrealized_entry_count']}`",
            f"- stranded ledger entries: `{counts['stranded_entry_count']}`",
            f"- transition ledger entries: `{counts['transition_entry_count']}`",
            f"- published entries total: `{counts['published_entry_count']}`",
            "",
            "## Accepted By Lane",
            "",
        ]
    )
    for lane, count in summary["accepted_by_lane"].items():
        lines.append(f"- {lane}: `{count}`")

    lines.extend(
        [
            "",
            "## Published By Lane",
            "",
        ]
    )
    for lane, count in summary["published_by_lane"].items():
        lines.append(f"- {lane}: `{count}`")

    lines.extend(
        [
            "",
            "## Reconciliation Checks",
            "",
            f"- accepted items missing from findings: `{len(reconciliation['accepted_not_in_findings'])}`",
            f"- accepted items missing from publication: `{len(reconciliation['accepted_not_in_publication'])}`",
            f"- published items missing from findings: `{len(reconciliation['publication_not_in_findings'])}`",
            f"- all accepted items exposed: `{str(reconciliation['all_accepted_items_exposed']).lower()}`",
        ]
    )

    if reconciliation["accepted_not_in_findings"]:
        lines.append(f"- missing in findings ids: `{', '.join(reconciliation['accepted_not_in_findings'])}`")
    if reconciliation["accepted_not_in_publication"]:
        lines.append(f"- missing in publication ids: `{', '.join(reconciliation['accepted_not_in_publication'])}`")
    if reconciliation["publication_not_in_findings"]:
        lines.append(f"- publication-only ids: `{', '.join(reconciliation['publication_not_in_findings'])}`")

    return "\n".join(lines).rstrip() + "\n"


def main():
    args = parse_args()
    runs_root = Path(args.runs_root).resolve()
    output_json_path = Path(args.output_json_path).resolve()
    output_md_path = Path(args.output_md_path).resolve()

    shortlist_metrics = load_json(require_file(runs_root / args.shortlist_run_id / "shortlist_metrics.json"))
    enhanced_metrics = load_json(
        require_file(runs_root / args.enhanced_interpretation_run_id / "enhanced_interpretation_ingestion_metrics.json")
    )
    unrealized_metrics = load_json(require_file(runs_root / args.unrealized_run_id / "unrealized_ideas_index_metrics.json"))
    unrealized_rows = load_jsonl(require_file(runs_root / args.unrealized_run_id / "unrealized_ideas_index.jsonl"))
    stranded_metrics = load_json(require_file(runs_root / args.stranded_run_id / "stranded_result_ledger_metrics.json"))
    stranded_rows = load_jsonl(require_file(runs_root / args.stranded_run_id / "stranded_result_ledger.jsonl"))
    transition_metrics = load_json(require_file(runs_root / args.transition_run_id / "transition_state_ledger_metrics.json"))
    transition_rows = load_jsonl(require_file(runs_root / args.transition_run_id / "transition_state_ledger.jsonl"))
    findings_metrics = load_json(require_file(runs_root / args.findings_run_id / "findings_and_throwaways_metrics.json"))
    findings_rows = load_jsonl(require_file(runs_root / args.findings_run_id / "findings_and_throwaways.jsonl"))

    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        accepted_interpretations = fetch_accepted_interpretations(connection, args.enhanced_interpretation_run_id)
        summary = build_summary(
            shortlist_metrics=shortlist_metrics,
            enhanced_metrics=enhanced_metrics,
            accepted_interpretations=accepted_interpretations,
            unrealized_metrics=unrealized_metrics,
            unrealized_rows=unrealized_rows,
            stranded_metrics=stranded_metrics,
            stranded_rows=stranded_rows,
            transition_metrics=transition_metrics,
            transition_rows=transition_rows,
            findings_metrics=findings_metrics,
            findings_rows=findings_rows,
            run_ids={
                "shortlist_run_id": args.shortlist_run_id,
                "enhanced_interpretation_run_id": args.enhanced_interpretation_run_id,
                "unrealized_run_id": args.unrealized_run_id,
                "stranded_run_id": args.stranded_run_id,
                "transition_run_id": args.transition_run_id,
                "findings_run_id": args.findings_run_id,
            },
        )
        output_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output_md_path.write_text(render_markdown(summary), encoding="utf-8")
        log_run_event(
            connection,
            args.run_id,
            "run_summary",
            "completed",
            {
                "enhanced_interpretation_run_id": args.enhanced_interpretation_run_id,
                "unrealized_run_id": args.unrealized_run_id,
                "stranded_run_id": args.stranded_run_id,
                "transition_run_id": args.transition_run_id,
                "findings_run_id": args.findings_run_id,
                "output_json_path": str(output_json_path),
                "output_md_path": str(output_md_path),
                "all_accepted_items_exposed": summary["reconciliation"]["all_accepted_items_exposed"],
            },
        )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
