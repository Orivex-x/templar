import sys
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Sequence, Union
from .DatabaseProvider import DatabaseProvider

sys.dont_write_bytecode = True

class Database:
    """
    Lightweight facade around a DatabaseProvider instance.
    Exposes execute/fetchone/fetchall for the rest of the code.
    """
    def __init__(self, provider: DatabaseProvider) -> None:
        self._provider = provider
        self._connected = False
        # Providers hold one connection and transaction state. Serializing access prevents ThreadingHTTPServer requests
        # from joining, committing or rolling back one another's transactions.
        self._lock = threading.RLock()
        self._transaction_state = threading.local()
        self.connect()

    def connect(self) -> None:
        with self._lock:
            if not self._connected:
                self._provider.connect()
                self._connected = True

    def close(self) -> None:
        with self._lock:
            if self._connected:
                self._provider.close()
                self._connected = False

    def execute(self, sql: str, params: Optional[Union[Dict[str, Any], Sequence[Any]]] = None) -> None:
        with self._lock:
            self._provider.execute(sql, params or {})

    def insert_and_get_id(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        with self._lock:
            return self._provider.insert_and_get_id(sql, params or {})

    def executemany(self, sql: str, params_seq: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._provider.executemany(sql, params_seq)

    def fetchone(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._provider.fetchone(sql, params or {})

    def fetchall(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self._lock:
            return self._provider.fetchall(sql, params or {})

    def query(self, sql: str, params: Optional[Union[Dict[str, Any], Sequence[Any]]] = None) -> List[Dict[str, Any]]:
        """Compatibility alias for fetching all rows."""
        return self.fetchall(sql, params)

    def begin(self) -> None:
        self._lock.acquire()
        try:
            if getattr(self._transaction_state, "active", False):
                raise RuntimeError("Nested database transactions are not supported")

            self._provider.begin()
            self._transaction_state.active = True
        except Exception:
            self._lock.release()
            raise

    def commit(self) -> None:
        if not getattr(self._transaction_state, "active", False):
            with self._lock:
                self._provider.commit()

            return

        try:
            self._provider.commit()
        finally:
            self._transaction_state.active = False
            self._lock.release()

    def rollback(self) -> None:
        if not getattr(self._transaction_state, "active", False):
            with self._lock:
                self._provider.rollback()

            return

        try:
            self._provider.rollback()
        finally:
            self._transaction_state.active = False
            self._lock.release()

    @contextmanager
    def transaction(self):
        self.begin()

        try:
            yield self
        except Exception:
            self.rollback()
            raise
        else:
            self.commit()

    @contextmanager
    def migration_transaction(self):
        """Run one migration under the strongest lock the provider exposes.

        SQLite's ordinary deferred ``BEGIN`` lets multiple workers all decide
        a migration is pending before the first writes. ``BEGIN IMMEDIATE``
        reserves the database for the whole migration and its tracking record.
        Other providers retain their transactional DDL/locking behavior.
        """
        begin_immediate = getattr(self._provider, "begin_immediate", None)
        if not callable(begin_immediate):
            with self.transaction():
                yield self

            return

        self._lock.acquire()
        transaction_started = False

        try:
            if getattr(self._transaction_state, "active", False):
                raise RuntimeError("Nested database transactions are not supported")

            begin_immediate()
            self._transaction_state.active = True
            transaction_started = True

            try:
                yield self
            except Exception:
                # Preserve the migration failure if a best-effort rollback also fails.  This method owns the lock for
                # the immediate transaction, so it must release it exactly once below.
                try:
                    self._provider.rollback()
                except Exception:
                    pass

                raise
            else:
                try:
                    self._provider.commit()
                except Exception:
                    # A failed commit can leave PostgreSQL in an aborted transaction. Roll it back before advisory-lock
                    # clean-up has to issue another statement on this connection.
                    try:
                        self._provider.rollback()
                    except Exception:
                        pass

                    raise
        finally:
            if transaction_started:
                self._transaction_state.active = False

            self._lock.release()

    @contextmanager
    def migration_lock(self, name: str):
        """Serialize a named migration across processes when supported.

        PostgreSQL and MySQL expose connection-scoped advisory locks. SQLite
        obtains its equivalent write reservation through ``BEGIN IMMEDIATE``
        in :meth:`migration_transaction`; holding the local lock here still
        makes the two contexts compose safely for one Database instance.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Migration lock name must be a non-empty string")

        acquire = getattr(self._provider, "acquire_migration_lock", None)
        release = getattr(self._provider, "release_migration_lock", None)
        self._lock.acquire()
        acquired = False

        try:
            if callable(acquire):
                acquire(name)
                acquired = True

            yield self
        except BaseException:
            # Clean-up must never replace the migration/commit failure that caused this context to unwind. Connection
            # close remains the provider-level fallback for a failed advisory unlocking.
            if acquired and callable(release):
                try:
                    release(name)
                except Exception:
                    pass
                finally:
                    acquired = False

            raise
        finally:
            try:
                if acquired and callable(release):
                    release(name)
            finally:
                self._lock.release()
