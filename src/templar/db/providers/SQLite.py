import sys, sqlite3, os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from ..DatabaseProvider import DatabaseProvider

sys.dont_write_bytecode = True

class SQLiteProvider(DatabaseProvider):
    """
    Simple SQLite provider. Uses sqlite3.Row to return dict-like rows.
    db_uri example: sqlite:///relative/path/to.db  or sqlite:////absolute/path/to.db
    """

    def __init__(self, db_uri: str):
        # parse sqlite URI
        self.db_path = self._parse_uri(db_uri)
        self.conn: Optional[sqlite3.Connection] = None
        self._in_transaction = False

    def _parse_uri(self, uri: str) -> str:
        if uri in {":memory:", "sqlite:///:memory:"}:
            return ":memory:"

        if uri.startswith("sqlite:///"):
            # relative path (three slashes)
            p = uri[len("sqlite:///") :]

            return os.path.abspath(p)
        
        if uri.startswith("sqlite:////"):
            # absolute path (rare but support & handle gracefully)
            p = uri[len("sqlite:") :]

            return os.path.abspath(p)
        
        if uri.startswith("sqlite://"):
            # fallback
            p = uri[len("sqlite://") :]

            return os.path.abspath(p)
        
        # plain path
        return os.path.abspath(uri)

    def connect(self) -> None:
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, sql: str, params: Optional[Union[Dict[str, Any], Sequence[Any]]] = None) -> None:
        assert self.conn is not None

        cur = self.conn.cursor()
        cur.execute(sql, params or {})

        if not self._in_transaction:
            self.conn.commit()

        cur.close()

    def insert_and_get_id(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        assert self.conn is not None

        cur = self.conn.cursor()

        try:
            cur.execute(sql, params or {})

            if not self._in_transaction:
                self.conn.commit()

            return int(cur.lastrowid)
        finally:
            cur.close()

    def executemany(self, sql: str, params_seq: List[Dict[str, Any]]) -> None:
        assert self.conn is not None

        cur = self.conn.cursor()
        cur.executemany(sql, params_seq)

        if not self._in_transaction:
            self.conn.commit()

        cur.close()

    def fetchone(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        assert self.conn is not None

        cur = self.conn.cursor()
        cur.execute(sql, params or {})
        row = cur.fetchone()
        cur.close()

        return dict(row) if row else None

    def fetchall(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        assert self.conn is not None

        cur = self.conn.cursor()
        cur.execute(sql, params or {})
        rows = cur.fetchall()
        cur.close()

        return [dict(r) for r in rows]

    def begin(self) -> None:
        assert self.conn is not None

        self.conn.execute("BEGIN;")
        self._in_transaction = True

    def begin_immediate(self) -> None:
        """Acquire SQLite's write reservation before a schema migration."""
        assert self.conn is not None

        self.conn.execute("BEGIN IMMEDIATE;")
        self._in_transaction = True

    def commit(self) -> None:
        assert self.conn is not None

        self.conn.commit()
        self._in_transaction = False

    def rollback(self) -> None:
        assert self.conn is not None

        self.conn.rollback()
        self._in_transaction = False
