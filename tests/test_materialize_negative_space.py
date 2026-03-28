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


class MaterializeNegativeSpaceTests(unittest.TestCase):
    def test_negative_space_stage_writes_ranked_candidates(self):
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
                  ('p1', 'arxiv', 'negative anchor', 'dead end theorem only'),
                  ('p2', 'arxiv', 'dead region candidate', 'dead end theorem only nearby'),
                  ('p3', 'arxiv', 'strong stranded candidate', 'dead region but with stronger stranded cue'),
                  ('p4', 'arxiv', 'far positive paper', 'cross-market parity anchor');

                INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256) VALUES
                  (1, 'p1', 'title_abs', 'negative anchor', 2, 'a'),
                  (2, 'p2', 'title_abs', 'dead region candidate', 2, 'b'),
                  (3, 'p3', 'title_abs', 'strong stranded candidate', 2, 'c'),
                  (4, 'p4', 'title_abs', 'far positive paper', 2, 'd');

                INSERT INTO embedding_spaces (space_id, name, model_name, dims, normalized, prompt_style) VALUES
                  (1, 's1_title_abs_main', 'local-test', 4, 1, 'title_abs');

                INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source, rationale_json) VALUES
                  ('membership-run', 'p1', 'discovery', 'test', '{}'),
                  ('membership-run', 'p2', 'discovery', 'test', '{}'),
                  ('membership-run', 'p3', 'discovery', 'test', '{}'),
                  ('membership-run', 'p4', 'discovery', 'test', '{}');

                INSERT INTO stranding_scores (
                  run_id, paper_id, membership_run_id, score_version, stranding_score,
                  instrument_gap_score, access_barrier_score, implementation_barrier_score,
                  result_specificity_score, resolution_mechanics_score, survey_penalty_score,
                  empirical_only_penalty_score, stranded_alpha_bonus, feature_json
                ) VALUES
                  ('stranding-run', 'p2', 'membership-run', 's08-test', 0.05, 0, 0, 0, 0, 0, 0, 0, 0, '{}'),
                  ('stranding-run', 'p3', 'membership-run', 's08-test', 0.60, 0, 0, 0, 0, 0, 0, 0, 0, '{}');
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
                [1, 2, 3, 4],
                np.array(
                    [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.97, 0.03, 0.0, 0.0],
                        [0.96, 0.04, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0],
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
                                "view_count": 4,
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
  - anchor_id: negative_anchor
    label: negative
    anchor_type: negative
    paper_ids: ["p1"]
    tags: [negative]
""".strip(),
                encoding="utf-8",
            )

            output_dir = tmp / "negative-run"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_negative_space.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "negative-run",
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
                    SELECT anchor_id, paper_id, negative_rank, negative_space_score, rationale_json
                    FROM negative_space_candidates
                    WHERE run_id='negative-run'
                    ORDER BY negative_rank
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["anchor_id"], "negative_anchor")
            self.assertEqual(rows[0]["paper_id"], "p2")
            self.assertEqual(rows[0]["negative_rank"], 1)
            self.assertGreater(rows[0]["negative_space_score"], rows[1]["negative_space_score"])

            rationale = json.loads(rows[0]["rationale_json"])
            self.assertEqual(rationale["stranding_score"], 0.05)
            self.assertIn("s1_title_abs_main", rationale["space_components"])

            metrics = json.loads((output_dir / "negative_space_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["negative_anchor_count"], 1)
            self.assertEqual(metrics["negative_space_candidate_count"], 2)
            self.assertEqual(metrics["anchors_with_candidates"], 1)


if __name__ == "__main__":
    unittest.main()
