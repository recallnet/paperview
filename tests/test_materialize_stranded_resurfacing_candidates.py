import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MaterializeStrandedResurfacingCandidatesTests(unittest.TestCase):
    def test_resurfacing_operator_ranks_only_stranded_qfin_slice(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical_db = tmp / "paperview.sqlite3"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "init_local_store.py"), "--db-path", str(canonical_db)],
                check=True,
                cwd=ROOT,
            )
            conn = sqlite3.connect(str(canonical_db))
            conn.executescript(
                """
                INSERT INTO papers (paper_id, source_corpus, title, abstract, primary_category, published_at) VALUES
                  ('p1', 'arxiv', 'strong stranded', 'closed-form illiquid calibration note', 'q-fin.PR', '2021-05-01'),
                  ('p2', 'arxiv', 'weaker stranded', 'older empirical result', 'q-fin.TR', '2017-05-01'),
                  ('p3', 'arxiv', 'realized leak', 'realized note', 'q-fin.PR', '2022-05-01'),
                  ('p4', 'arxiv', 'not stranded alpha', 'ignore me', 'q-fin.PR', '2021-05-01'),
                  ('p5', 'arxiv', 'wrong category', 'econ note', 'econ.EM', '2021-05-01');

                INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source) VALUES
                  ('membership-run', 'p1', 'stranded_alpha', 'fixture'),
                  ('membership-run', 'p2', 'stranded_alpha', 'fixture'),
                  ('membership-run', 'p3', 'stranded_alpha', 'fixture'),
                  ('membership-run', 'p3', 'realized_market', 'fixture'),
                  ('membership-run', 'p4', 'discovery', 'fixture'),
                  ('membership-run', 'p5', 'stranded_alpha', 'fixture');

                INSERT INTO stranding_scores (
                  run_id, paper_id, membership_run_id, score_version, stranding_score,
                  instrument_gap_score, access_barrier_score, implementation_barrier_score,
                  result_specificity_score, resolution_mechanics_score, survey_penalty_score,
                  empirical_only_penalty_score, stranded_alpha_bonus, feature_json
                ) VALUES
                  ('stranding-run', 'p1', 'membership-run', 'v1', 0.40, 0, 0, 0, 0.50, 0, 0.0, 0.0, 0, '{}'),
                  ('stranding-run', 'p2', 'membership-run', 'v1', 0.25, 0, 0, 0, 0.20, 0, 0.2, 0.3, 0, '{}'),
                  ('stranding-run', 'p3', 'membership-run', 'v1', 0.38, 0, 0, 0, 0.45, 0, 0.0, 0.0, 0, '{}'),
                  ('stranding-run', 'p4', 'membership-run', 'v1', 0.50, 0, 0, 0, 0.60, 0, 0.0, 0.0, 0, '{}'),
                  ('stranding-run', 'p5', 'membership-run', 'v1', 0.45, 0, 0, 0, 0.50, 0, 0.0, 0.0, 0, '{}');

                INSERT INTO transition_state_scores (
                  run_id, paper_id, membership_run_id, probe_run_id, score_version,
                  transition_state_score, queue_value_score, refill_resiliency_score,
                  auction_handoff_score, maker_retreat_score, parity_repair_score,
                  sparse_component_score, proximity_component_score, family_count, feature_json
                ) VALUES
                  ('transition-run', 'p1', 'membership-run', 'probe-run', 'v1', 0.30, 0, 0, 0, 0, 0, 0, 0, 2, '{}'),
                  ('transition-run', 'p2', 'membership-run', 'probe-run', 'v1', 0.10, 0, 0, 0, 0, 0, 0, 0, 1, '{}'),
                  ('transition-run', 'p3', 'membership-run', 'probe-run', 'v1', 0.35, 0, 0, 0, 0, 0, 0, 0, 2, '{}');
                """
            )
            conn.commit()
            conn.close()

            output_dir = tmp / "resurfacing-run"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_stranded_resurfacing_candidates.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "resurfacing-run",
                    "--membership-run-id",
                    "membership-run",
                    "--stranding-run-id",
                    "stranding-run",
                    "--transition-score-run-id",
                    "transition-run",
                    "--output-dir",
                    str(output_dir),
                    "--top-k",
                    "10",
                ],
                check=True,
                cwd=ROOT,
            )

            conn = sqlite3.connect(str(canonical_db))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT paper_id, resurfacing_rank, resurfacing_score, rationale_json
                    FROM stranded_resurfacing_candidates
                    WHERE run_id='resurfacing-run'
                    ORDER BY resurfacing_rank, paper_id
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual([row["paper_id"] for row in rows], ["p1", "p3", "p2"])
            self.assertGreater(rows[0]["resurfacing_score"], rows[1]["resurfacing_score"])
            self.assertGreater(rows[1]["resurfacing_score"], rows[2]["resurfacing_score"])

            rationale = json.loads(rows[1]["rationale_json"])
            self.assertEqual(rationale["realized_market_flag"], 1)
            self.assertEqual(rationale["primary_category"], "q-fin.PR")

            metrics = json.loads((output_dir / "stranded_resurfacing_candidate_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["candidate_count"], 3)
            self.assertEqual(metrics["top_ranked_paper_id"], "p1")


if __name__ == "__main__":
    unittest.main()
