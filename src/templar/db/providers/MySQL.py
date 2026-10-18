import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import mysql.connector

from ..DatabaseProvider import DatabaseProvider
from ..SqlPlaceholders import named_to_pyformat

sys.dont_write_bytecode = True

class MySQLProvider(DatabaseProvider):
    """
    MySQL provider using mysql.connector.
    URI Example:
        mysql://user:password@localhost:3306/dbname
    """

    def __init__(self, db_uri: str):
        self.db_uri = db_uri
        self.conn: Optional[mysql.connector.MySQLConnection] = None
        self._in_transaction = False

    def _parse_uri(self):
        parsed = urlparse(self.db_uri)

        return {
            "database": parsed.path.lstrip("/"),
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname or "127.0.0.1",
            "port": parsed.port or 3306
        }

    def connect(self) -> None:
        cfg = self._parse_uri()
        self.conn = mysql.connector.connect(**cfg)

    @staticmethod
    def _sql(sql: str) -> str:
        """Translate Templar's provider-neutral :name placeholders for MySQL."""
        return named_to_pyformat(sql)

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> None:
        assert self.conn is not None

        cur = self.conn.cursor()
        cur.execute(self._sql(sql), params or {})

        if not self._in_transaction:
            self.conn.commit()

        cur.close()

    def executemany(self, sql: str, params_seq: List[Dict[str, Any]]) -> None:
        assert self.conn is not None
        
        cur = self.conn.cursor()
        cur.executemany(self._sql(sql), params_seq)

        if not self._in_transaction:
            self.conn.commit()

        cur.close()

    def fetchone(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        assert self.conn is not None
        
        cur = self.conn.cursor(dictionary=True)
        cur.execute(self._sql(sql), params or {})
        row = cur.fetchone()
        cur.close()
        
        return row

    def fetchall(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        assert self.conn is not None

        cur = self.conn.cursor(dictionary=True)
        cur.execute(self._sql(sql), params or {})
        rows = cur.fetchall()
        cur.close()

        return rows

    def begin(self) -> None:
        assert self.conn is not None
        
        self.conn.start_transaction()
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
        """Acquire a connection-scoped MySQL advisory lock for a migration."""
        assert self.conn is not None

        cur = self.conn.cursor()

        try:
            cur.execute("SELECT GET_LOCK(%s, %s)", (name, 60))
            row = cur.fetchone()

            if not row or row[0] != 1:
                raise RuntimeError(f"Timed out acquiring migration lock {name!r}")
        finally:
            cur.close()

    def release_migration_lock(self, name: str) -> None:
        """Release a previously acquired MySQL migration lock."""
        assert self.conn is not None

        cur = self.conn.cursor()

        try:
            cur.execute("SELECT RELEASE_LOCK(%s)", (name,))
        finally:
            cur.close()

    def insert_and_get_id(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        assert self.conn is not None

        cur = self.conn.cursor()

        try:
            cur.execute(self._sql(sql), params or {})
            generated_id = cur.lastrowid

            if not self._in_transaction:
                self.conn.commit()
        finally:
            cur.close()

        if generated_id is None:
            raise RuntimeError("MySQL insert did not return an id")

        return int(generated_id)
