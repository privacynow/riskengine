from contextlib import contextmanager
from typing import Iterator, Tuple

import psycopg2
from psycopg2.extensions import connection, cursor

from . import config


def get_db_connection() -> connection:
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


@contextmanager
def db_cursor() -> Iterator[Tuple[connection, cursor]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        yield conn, cur
    finally:
        cur.close()
        conn.close()
