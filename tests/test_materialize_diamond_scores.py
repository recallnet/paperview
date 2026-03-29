import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_diamond_scores.py"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at) VALUES
          ('p-market', 'arxiv', 'Venue rules and dark queue priority', 'econ.GN', '2021-01-02'),
          ('p-transition', 'arxiv', 'Auction refill asymmetry', 'q-fin.ST', '2021-01-01'),
          ('p-stranded', 'arxiv', 'Impact-aware execution control', 'q-fin.TR', '2021-01-04');

        INSERT INTO diamond_lane_scores (
          run_id, paper_id, membership_run_id, probe_run_id, bridge_run_id, composition_run_id,
          transition_score_run_id, stranded_run_id, score_version, transition_state_score,
          market_design_score, settlement_resolution_score, participant_pathologies_score, state_graph_score,
          stranded_qfin_score, lifecycle_aux_score, top_lane, top_lane_score, positive_lane_count, feature_json
        ) VALUES
          (
            'lane-run', 'p-market', 'membership-run', 'probe-run', 'bridge-run', 'composition-run',
            'transition-score-run', 'stranded-run', 'fixture', 0.15, 0.35, 0.05, 0.18, 0.04, 0.0, 0.3,
            'market_design', 0.35, 2,
            '{\"lane_components\": {\"market_design\": {\"operator_score\": 0.35, \"probe_score\": 0.6, \"study_score\": 0.2, \"holdout_score\": 0.0, \"evidence_refs\": [{\"source\": \"bridge\", \"score\": 0.35}]}, \"transition_state\": {\"operator_score\": 0.1, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"settlement_resolution\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"participant_pathologies\": {\"operator_score\": 0.18, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"state_graph\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"stranded_qfin\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"lifecycle\": {\"operator_score\": 0.0, \"probe_score\": 0.2, \"study_score\": 0.4, \"holdout_score\": 0.0, \"evidence_refs\": []}}}'
          ),
          (
            'lane-run', 'p-transition', 'membership-run', 'probe-run', 'bridge-run', 'composition-run',
            'transition-score-run', 'stranded-run', 'fixture', 0.82, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            'transition_state', 0.82, 1,
            '{\"lane_components\": {\"market_design\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"transition_state\": {\"operator_score\": 0.82, \"probe_score\": 0.5, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": [{\"source\": \"composition\", \"score\": 0.4}]}, \"settlement_resolution\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"participant_pathologies\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"state_graph\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"stranded_qfin\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"lifecycle\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}}}'
          ),
          (
            'lane-run', 'p-stranded', 'membership-run', 'probe-run', 'bridge-run', 'composition-run',
            'transition-score-run', 'stranded-run', 'fixture', 0.0, 0.0, 0.0, 0.0, 0.0, 0.66, 0.0,
            'stranded_qfin', 0.66, 1,
            '{\"lane_components\": {\"market_design\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"transition_state\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"settlement_resolution\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"participant_pathologies\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"state_graph\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"stranded_qfin\": {\"operator_score\": 0.66, \"probe_score\": 0.0, \"study_score\": 0.7, \"holdout_score\": 0.0, \"evidence_refs\": []}, \"lifecycle\": {\"operator_score\": 0.0, \"probe_score\": 0.0, \"study_score\": 0.0, \"holdout_score\": 0.0, \"evidence_refs\": []}}}'
          );
        """
    )
    connection.commit()


class MaterializeDiamondScoresTests(unittest.TestCase):
    def test_materializes_unified_diamond_scores_and_views(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            reports_dir = tmp_path / "reports"
            reports_dir.mkdir()

            connection = sqlite3.connect(db_path)
            seed_fixture(connection)
            connection.close()

            capsules_path = tmp_path / "challenge_capsules.yaml"
            capsules_path.write_text(
                """
capsules:
  - capsule_id: market_design_failure
    lane: market_design
    anchor_ids: [market_design_seams]
    pattern_ids: []
    far_realized_patterns: []
  - capsule_id: queue_refill_repair
    lane: transition_state
    anchor_ids: [queue_value_passive_quoting]
    pattern_ids: []
    far_realized_patterns: []
  - capsule_id: stranded_qfin_rescue
    lane: stranded_qfin
    anchor_ids: []
    pattern_ids: []
    far_realized_patterns: []
""".strip(),
                encoding="utf-8",
            )

            write_jsonl(
                reports_dir / "ds1-translation-gap-candidates.jsonl",
                [
                    {
                        "paper_id": "p-market",
                        "challenge_capsule_matched": "market_design_failure",
                        "translation_gap_score": 6.4,
                        "outside_obvious_qfin_discourse": True,
                        "support": {
                            "challenge_affinity": 1.8,
                            "operator_affinity": 0.82,
                            "negative_penalty": 0.0,
                            "realized_penalty": 0.0,
                        },
                    }
                ],
            )
            write_jsonl(
                reports_dir / "ds3-early-market-ledger.jsonl",
                [
                    {
                        "paper_id": "p-market",
                        "failure_mode": "Venue rules create a repeatable queue-priority gap before markets professionalize.",
                        "what_closes_it": "Harmonized routing and professional liquidity provision close the seam.",
                        "likely_market_stage": "thin or weakly arbitraged electronic market",
                        "why_persists": "The rule interaction is described but not translated into a testable edge hypothesis.",
                    }
                ],
            )
            write_jsonl(
                reports_dir / "ds4-stranded-ledger.jsonl",
                [
                    {
                        "paper_id": "p-stranded",
                        "resurfacing_score": 0.41,
                        "result_plain": "Surrogate models can accelerate impact-aware execution policy search.",
                        "modern_equivalent_now": "execution policy search with fast surrogates",
                        "instrument_assumed": "liquid futures or equities",
                        "why_stranded_then": "It stayed buried in calibration language.",
                    }
                ],
            )
            write_jsonl(
                reports_dir / "ds5-holdout-echo-report.jsonl",
                [
                    {
                        "candidate_paper_id": "p-market",
                        "candidate_family": "market_design",
                        "top_echo_score": 0.74,
                        "echo_verdict": "partial",
                    }
                ],
            )

            output_dir = tmp_path / "diamond-run"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "diamond-run",
                    "--lane-score-run-id",
                    "lane-run",
                    "--membership-run-id",
                    "membership-run",
                    "--challenge-capsules-path",
                    str(capsules_path),
                    "--reports-dir",
                    str(reports_dir),
                    "--output-dir",
                    str(output_dir),
                    "--top-k",
                    "3",
                ],
                check=True,
                cwd=ROOT,
            )

            connection = sqlite3.connect(db_path)
            try:
                rows = connection.execute(
                    """
                    SELECT paper_id, diamond_score, top_lane, primary_capsule_id,
                           problem_view, mechanism_view, regime_view, stranding_view
                    FROM diamond_scores
                    WHERE run_id='diamond-run'
                    ORDER BY diamond_score DESC, paper_id
                    """
                ).fetchall()
            finally:
                connection.close()

            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0][0], "p-market")
            self.assertEqual(rows[0][2], "market_design")
            self.assertEqual(rows[0][3], "market_design_failure")
            self.assertIn("queue-priority gap", rows[0][4])
            self.assertIn("Harmonized routing", rows[0][5])
            self.assertIn("weakly arbitraged", rows[0][6])
            self.assertIn("not translated", rows[0][7])
            stranded = next(row for row in rows if row[0] == "p-stranded")
            self.assertIn("Surrogate models", stranded[4])
            self.assertIn("execution policy search", stranded[5])
            self.assertIn("liquid futures", stranded[6])
            self.assertIn("calibration language", stranded[7])

            metrics = json.loads((output_dir / "diamond_score_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["scored_papers"], 3)
            self.assertEqual(metrics["top_ranked_paper_id"], "p-market")
            self.assertGreaterEqual(metrics["top_20_lane_diversity"], 2)


if __name__ == "__main__":
    unittest.main()
