"""SQLite-vec storage shared by corpus materializers.

Vector sidecars store genuine float32 embeddings; source metadata follows the
same schema as the canonical corpus database.
"""
import hashlib
import re
import sqlite3
from pathlib import Path

import numpy as np
import sqlite_vec


def connect(path):
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    try:
        connection.enable_load_extension(True)
        try:
            sqlite_vec.load(connection)
        finally:
            connection.enable_load_extension(False)
    except Exception:
        connection.close()
        raise
    return connection


def ensure_schema(connection):
    schema = Path(__file__).resolve().parent.parent / 'sql/paperview_schema.sql'
    connection.executescript(schema.read_text())


def stable_short_id(value):
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def _table_name(name):
    # @context invariant: SQLite parameters cannot bind identifiers. Validate
    # configured table names before interpolating them into any statement.
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
        raise ValueError('invalid vector table identifier')
    return '"' + name + '"'


def ensure_vec_table(connection, table_name, dims):
    table = _table_name(table_name)
    if not isinstance(dims, int) or dims <= 0:
        raise ValueError('vector dimensions must be a positive integer')
    connection.execute(f'CREATE VIRTUAL TABLE IF NOT EXISTS {table} USING vec0(embedding float[{dims}])')
    connection.commit()


def _write_vectors(connection, table_name, view_ids, vectors):
    table = _table_name(table_name)
    if len(view_ids) != len(vectors):
        raise ValueError('view IDs and vectors must have equal lengths')
    for view_id, vector in zip(view_ids, vectors):
        connection.execute(f'DELETE FROM {table} WHERE rowid = ?', (int(view_id),))
        connection.execute(f'INSERT INTO {table}(rowid, embedding) VALUES (?, ?)',
                           (int(view_id), np.asarray(vector, dtype=np.float32).tobytes()))


def write_vectors(connection, table_name, view_ids, vectors):
    with connection:
        _write_vectors(connection, table_name, view_ids, vectors)


def query_knn(connection, table_name, vector, k):
    table = _table_name(table_name)
    return connection.execute(
        f'SELECT rowid, distance FROM {table} WHERE embedding MATCH ? AND k = ? ORDER BY distance',
        (np.asarray(vector, dtype=np.float32).tobytes(), int(k)),
    ).fetchall()


def insert_text_views(connection, rows):
    with connection:
        # The standalone discovery sidecar has no papers table populated; the
        # canonical corpus materializer inserts its own paper rows separately.
        for row in rows:
            connection.execute('INSERT OR IGNORE INTO papers(paper_id, source_corpus) VALUES (?, ?)',
                               (row['paper_id'], 'discovery'))
            connection.execute('''INSERT INTO text_views
                (view_id, paper_id, view_type, text, token_estimate, text_sha256)
                VALUES (:view_id, :paper_id, :view_type, :text, :token_estimate, :text_sha256)''', row)


def upsert_embedding_space(connection, *, name, model_name, dims, normalized, prompt_style):
    connection.execute('''INSERT INTO embedding_spaces(name, model_name, dims, normalized, prompt_style)
        VALUES (?, ?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET
        model_name=excluded.model_name, dims=excluded.dims,
        normalized=excluded.normalized, prompt_style=excluded.prompt_style''',
        (name, model_name, dims, int(normalized), prompt_style))
    return connection.execute('SELECT space_id FROM embedding_spaces WHERE name = ?', (name,)).fetchone()[0]


def upsert_view_embedding_meta(connection, *, space_id, view_ids, batch_id, embed_ms=0):
    connection.executemany('''INSERT INTO view_embedding_meta
        (view_id, space_id, embed_status, embed_ms, batch_id) VALUES (?, ?, 'embedded', ?, ?)
        ON CONFLICT(view_id, space_id) DO UPDATE SET
        embed_status=excluded.embed_status, embed_ms=excluded.embed_ms, batch_id=excluded.batch_id''',
        [(int(view_id), space_id, embed_ms, batch_id) for view_id in view_ids])


def write_embeddings(connection, *, table_name, space_id, view_ids, vectors, batch_id):
    # @context invariant: vectors and their provenance must commit together.
    # Calling write_vectors here would commit before a metadata error can roll back.
    with connection:
        _write_vectors(connection, table_name, view_ids, vectors)
        upsert_view_embedding_meta(connection, space_id=space_id, view_ids=view_ids, batch_id=batch_id)
