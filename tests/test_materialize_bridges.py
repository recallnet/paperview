import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sqlite_vec_adapter import connect as connect_vec_store, ensure_vec_table, write_vectors


class MaterializeBridgesTests(unittest.TestCase):
    def test_bridge_stage_writes_ranked_bridge_candidates(self):
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
                INSERT INTO papers (paper_id, source_corpus, title, abstract) VALUES
                  ('p1', 'arxiv', 'parity anchor', 'cross-market parity anchor'),
                  ('p2', 'arxiv', 'bridge paper', 'cross-market contingent bridge paper'),
                  ('p3', 'arxiv', 'auction anchor', 'auction design anchor'),
                  ('p4', 'arxiv', 'negative paper', 'dead end theorem only'),
                  ('p5', 'arxiv', 'parity local', 'mostly parity local paper');

                INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256) VALUES
                  (1, 'p1', 'title_abs', 'parity anchor', 2, 'a'),
                  (2, 'p2', 'title_abs', 'bridge paper', 2, 'b'),
                  (3, 'p3', 'title_abs', 'auction anchor', 2, 'c'),
                  (4, 'p4', 'title_abs', 'negative paper', 2, 'd'),
                  (5, 'p5', 'title_abs', 'parity local', 2, 'e');

                INSERT INTO embedding_spaces (space_id, name, model_name, dims, normalized, prompt_style) VALUES
                  (1, 's1_title_abs_main', 'local-test', 4, 1, 'title_abs');

                INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source, rationale_json) VALUES
                  ('membership-run', 'p1', 'discovery', 'test', '{}'),
                  ('membership-run', 'p2', 'discovery', 'test', '{}'),
                  ('membership-run', 'p3', 'discovery', 'test', '{}'),
                  ('membership-run', 'p4', 'discovery', 'test', '{}'),
                  ('membership-run', 'p5', 'discovery', 'test', '{}');

                INSERT INTO stranding_scores (
                  run_id, paper_id, membership_run_id, score_version, stranding_score,
                  instrument_gap_score, access_barrier_score, implementation_barrier_score,
                  result_specificity_score, resolution_mechanics_score, survey_penalty_score,
                  empirical_only_penalty_score, stranded_alpha_bonus, feature_json
                ) VALUES
                  ('stranding-run', 'p2', 'membership-run', 's08-test', 0.33, 0, 0, 0, 0, 0, 0, 0, 0, '{}');
                """
            )
            conn.commit()
            conn.close()

            vec_db = tmp / "embeddings.sqlite3"
            vec_conn = connect_vec_store(vec_db)
            ensure_vec_table(vec_conn, "vec_s1_title_abs_main_4", 4)
            write_vectors(
                vec_conn,
                "vec_s1_title_abs_main_4",
                [1, 2, 3, 4, 5],
                np.array(
                    [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.72, 0.68, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.95, 0.05, 0.0, 0.0],
                    ],
                    dtype=np.float32,
                ),
            )
            vec_conn.close()

            embedding_metrics = tmp / "embedding_metrics.json"
            embedding_metrics.write_text(
                json.dumps(
                    {
                        "run_id": "embed-run",
                        "vec_db_path": str(vec_db),
                        "spaces": [
                            {
                                "name": "s1_title_abs_main",
                                "view_type": "title_abs",
                                "dims": 4,
                                "table_name": "vec_s1_title_abs_main_4",
                                "view_count": 5,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            anchors = tmp / "anchors.yaml"
            anchors.write_text(
                """
anchors:
  - anchor_id: parity_propagation
    label: parity
    anchor_type: positive
    paper_ids: ["p1"]
    tags: [parity]
  - anchor_id: auction_parimutuel_design
    label: auction
    anchor_type: positive
    paper_ids: ["p3"]
    tags: [auction]
  - anchor_id: negative_anchor
    label: negative
    anchor_type: negative
    paper_ids: ["p4"]
    tags: [negative]
""".strip(),
                encoding="utf-8",
            )

            output_dir = tmp / "bridge-run"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_bridges.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "bridge-run",
                    "--embedding-run-id",
                    "embed-run",
                    "--embedding-metrics-path",
                    str(embedding_metrics),
                    "--vec-db-path",
                    str(vec_db),
                    "--anchors-path",
                    str(anchors),
                    "--membership-run-id",
                    "membership-run",
                    "--stranding-run-id",
                    "stranding-run",
                    "--output-dir",
                    str(output_dir),
                    "--top-k",
                    "2",
                ],
                check=True,
                cwd=ROOT,
            )

            conn = sqlite3.connect(str(canonical_db))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT source_anchor_id, target_anchor_id, paper_id, bridge_rank, bridge_score, rationale_json
                    FROM bridge_candidates
                    WHERE run_id='bridge-run'
                    ORDER BY bridge_rank, paper_id
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["source_anchor_id"], "auction_parimutuel_design")
            self.assertEqual(rows[0]["target_anchor_id"], "parity_propagation")
            self.assertEqual(rows[0]["paper_id"], "p2")
            self.assertEqual(rows[0]["bridge_rank"], 1)
            self.assertGreater(rows[0]["bridge_score"], rows[1]["bridge_score"])

            rationale = json.loads(rows[0]["rationale_json"])
            self.assertEqual(rationale["stranding_score"], 0.33)
            self.assertIn("s1_title_abs_main", rationale["space_components"])

            metrics = json.loads((output_dir / "bridge_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["anchor_pair_count"], 1)
            self.assertEqual(metrics["bridge_candidate_count"], 2)
            self.assertEqual(metrics["pairs_with_candidates"], 1)


if __name__ == "__main__":
    unittest.main()
