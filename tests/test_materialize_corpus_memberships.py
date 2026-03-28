import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MaterializeCorpusMembershipsTests(unittest.TestCase):
    def test_materializes_discovery_realized_stranded_and_holdout_memberships(self):
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
                INSERT INTO papers (
                  paper_id, source_corpus, title, abstract, categories_json, primary_category, published_at
                ) VALUES
                  ('p1', 'arxiv', 'Cross-market trading parity', 'arbitrage and trading across venues', '["q-fin.TR"]', 'q-fin.TR', '2020-02-01'),
                  ('p2', 'arxiv', 'General optimization', 'queueing and control only', '["math.OC"]', 'math.OC', '2022-05-01'),
                  ('p3', 'arxiv', 'Prediction market design', 'prediction market and hedging mechanics', '["cs.GT"]', 'cs.GT', '2024-04-02'),
                  ('p4', 'arxiv', 'Old q-fin idea', 'pricing under affine models', '["q-fin.PR"]', 'q-fin.PR', '2016-07-03');
                """
            )
            conn.commit()
            conn.close()

            output_dir = tmp / "membership-run"
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--with",
                    "pyyaml",
                    "python3",
                    str(ROOT / "scripts" / "materialize_corpus_memberships.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "membership-run",
                    "--corpus-config-path",
                    str(ROOT / "configs" / "corpus.yaml"),
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                cwd=ROOT,
            )

            conn = sqlite3.connect(str(canonical_db))
            try:
                counts = dict(
                    conn.execute(
                        """
                        SELECT corpus_id, count(*)
                        FROM corpus_memberships
                        WHERE run_id = 'membership-run'
                        GROUP BY corpus_id
                        """
                    ).fetchall()
                )
            finally:
                conn.close()
            self.assertEqual(counts["discovery"], 3)
            self.assertEqual(counts["realized_market"], 2)
            self.assertEqual(counts["stranded_alpha"], 2)
            self.assertEqual(counts["holdout"], 1)


if __name__ == "__main__":
    unittest.main()
