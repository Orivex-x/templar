import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

from ..DatabaseProvider import DatabaseProvider
from ..SqlPlaceholders import named_to_pyformat

sys.dont_write_bytecode = True

class PostgreSQLProvider(DatabaseProvider):
    """
    PostgreSQL database provider using psycopg2.
    URI Example:
        postgres://user:password@localhost:5432/dbname
    """

    def __init__(self, db_uri: str):
        self.db_uri = db_uri
        self.conn: Optional[psycopg2.extensions.connection] = None
        self._in_transaction = False

    def _parse_uri(self) -> Dict[str, Any]:
        parsed = urlparse(self.db_uri)

        return {
            "dbname": parsed.path.lstrip("/"),
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": parsed.port or 5432,
        }

    def connect(self) -> None:
        cfg = self._parse_uri()
        self.conn = psycopg2.connect(**cfg)
        self.conn.autocommit = False

    @staticmethod
    def _sql(sql: str) -> str:
        """Translate Templar's provider-neutral :name placeholders for psycopg."""
        return named_to_pyformat(sql)

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> None:
        assert self.conn is not None

        with self.conn.cursor() as cur:
            cur.execute(self._sql(sql), params or {})

        if not self._in_transaction:
            self.conn.commit()

    def executemany(self, sql: str, params_seq: List[Dict[str, Any]]) -> None:
        assert self.conn is not None

        with self.conn.cursor() as cur:
            cur.executemany(self._sql(sql), params_seq)

        if not self._in_transaction:
            self.conn.commit()

    def fetchone(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        assert self.conn is not None

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(self._sql(sql), params or {})
            row = cur.fetchone()

            return dict(row) if row else None

    def fetchall(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        assert self.conn is not None

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(self._sql(sql), params or {})
            rows = cur.fetchall()

            return [dict(r) for r in rows]

    def begin(self) -> None:
        assert self.conn is not None

        with self.conn.cursor() as cur:
            cur.execute("BEGIN;")

        self._in_transaction = True

    def commit(self) -> None:
        assert self.conn is not None

        self.conn.commit()
        self._in_transaction = False

    def rollback(self) -> None:
        assert self.conn is not None

        self.conn.rollback()
        self._in_transaction = False

    def acquire_migration_lock(self, name: str) -> None:
        """Acquire a session-scoped PostgreSQL advisory lock for a migration."""
        assert self.conn is not None

        with self.conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(hashtext(%s))", (name,))

        # The provider uses autocommit=False. Finish the implicit transaction opened by SELECT before
        # Database.migration_transaction() begins its own transaction; session advisory locks survive a commit.
        self.conn.commit()

    def release_migration_lock(self, name: str) -> None:
        """Release a previously acquired PostgreSQL migration lock."""
        assert self.conn is not None

        with self.conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(hashtext(%s))", (name,))

        self.conn.commit()
        self.conn.commit()

    def insert_and_get_id(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        assert self.conn is not None

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"{self._sql(sql)} RETURNING id", params or {})
            row = cur.fetchone()

        if not self._in_transaction:
            self.conn.commit()

        if not row or row.get("id") is None:
            raise RuntimeError("PostgreSQL insert did not return an id")

        return int(row["id"])
