"""Configured database creation with lazy optional provider imports."""

from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Optional

from templar.Config import Config
from .Database import Database


def _active_config(config: Optional[Any] = None) -> Mapping:
    if config is None:
        return Config().get_active_config()

    if isinstance(config, Mapping):
        return config

    if hasattr(config, "get_active_config"):
        return config.get_active_config()

    raise TypeError("config must be a mapping or a Templar Config instance")


def create_database(config: Optional[Any] = None) -> Database:
    """Create a connected database using the selected configuration provider."""
    active = _active_config(config)
    engine = str(active.get("db_engine", "sqlite")).lower()
    uri = active.get("db_uri", "sqlite:///db/dev.db")

    if engine in {"sqlite", "sqlite3"}:
        from .providers.SQLite import SQLiteProvider
        provider = SQLiteProvider(uri)
    elif engine == "mysql":
        from .providers.MySQL import MySQLProvider
        provider = MySQLProvider(uri)
    elif engine in {"postgres", "postgresql"}:
        from .providers.PostgreSQL import PostgreSQLProvider
        provider = PostgreSQLProvider(uri)
    elif engine in {"mongo", "mongodb", "mongo-db", "mongo_db"}:
        raise RuntimeError(
            "MongoDB is not supported by Templar's SQL ORM. "
            "Use sqlite, postgresql, or mysql."
        )
    else:
        raise RuntimeError(f"Unsupported DB engine: {engine}")

    return Database(provider)


class DatabaseProxy:
    """Resolve the database bound to the current server/request context.

    A fallback is retained for scripts and backwards compatibility, but web
    requests bind their owning ``TemplarServer.database`` for the lifetime of
    the request. This prevents one server from replacing another server's ORM
    connection in a shared Python process.
    """

    def __init__(self) -> None:
        self._default_database: Optional[Database] = None
        self._bound_database: ContextVar[Optional[Database]] = ContextVar(
            "templar_bound_database", default=None
        )

    def configure(self, config: Optional[Any] = None) -> Database:
        self.close()
        self._default_database = create_database(config)

        return self._default_database

    @contextmanager
    def use(self, database: Database):
        """Bind ``database`` only within the current request/task context."""
        if not isinstance(database, Database):
            raise TypeError("database must be a Templar Database instance")

        token = self._bound_database.set(database)

        try:
            yield database
        finally:
            self._bound_database.reset(token)

    def get(self) -> Database:
        bound = self._bound_database.get()

        if bound is not None:
            return bound

        if self._default_database is None:
            self._default_database = create_database()

        return self._default_database

    def close(self) -> None:
        if self._default_database is not None:
            self._default_database.close()
            self._default_database = None

    def __getattr__(self, name: str):
        return getattr(self.get(), name)


db = DatabaseProxy()

__all__ = ["Database", "DatabaseProxy", "create_database", "db"]
