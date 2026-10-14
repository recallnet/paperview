import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sqlite_vec_adapter import (
    connect, ensure_schema, ensure_vec_table, insert_text_views, query_knn,
    upsert_embedding_space, write_embeddings, write_vectors,
)


class SQLiteVecAdapterTests(unittest.TestCase):
    def test_embeddings_survive_reopen_and_update_nearest_neighbor(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'vectors.sqlite3'
            connection = connect(path)
            ensure_schema(connection)
            insert_text_views(connection, [dict(view_id=i, paper_id=f'p{i}',
                view_type='mechanism_sections', text=f'fixture {i}',
                token_estimate=2, text_sha256=f'hash{i}') for i in (1, 2)])
            ensure_vec_table(connection, 'vec_test_2', 2)
            space = upsert_embedding_space(connection, name='test', model_name='fixture',
                dims=2, normalized=True, prompt_style='mechanism_sections')
            write_embeddings(connection, table_name='vec_test_2', space_id=space,
                view_ids=[1, 2], vectors=np.array([[1, 0], [0, 1]]), batch_id='fixture')
            connection.close()
            connection = connect(path)
            self.assertEqual(query_knn(connection, 'vec_test_2', [1, 0], 1)[0]['rowid'], 1)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM view_embedding_meta').fetchone()[0], 2)
            write_vectors(connection, 'vec_test_2', [1], [[-1, 0]])
            self.assertEqual(query_knn(connection, 'vec_test_2', [1, 0], 1)[0]['rowid'], 2)
            with self.assertRaises(ValueError):
                ensure_vec_table(connection, 'vectors; DROP TABLE papers', 2)
            with self.assertRaises(ValueError):
                write_vectors(connection, 'vec_test_2', [1, 2], [[0, 1]])
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM papers').fetchone()[0], 2)
            connection.close()


if __name__ == '__main__':
    unittest.main()
