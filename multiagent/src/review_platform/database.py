"""Vong doi connection database cua review platform service."""
from contextlib import contextmanager

import psycopg

import db


@contextmanager
def open_connection(dsn_str: str | None = None):
    """Mo mot connection autocommit va luon dong khi het scope."""
    conn = psycopg.connect(dsn_str or db.dsn(), autocommit=True)
    try:
        yield conn
    finally:
        conn.close()
