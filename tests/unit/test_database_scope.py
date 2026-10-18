"""Database scoping tests for concurrent/multi-server use."""

import threading

import pytest

from templar.db import create_database, db
from templar.db.Models import Model
from templar.db.Database import Database
from templar.db.DatabaseProvider import DatabaseProvider


def test_models_use_the_database_bound_to_the_current_scope():
    # Model declaration may create its fallback schema, but every operational
    # path must ensure that schema on the database selected for this scope.
    fallback = db.configure({"db_engine": "sqlite", "db_uri": "sqlite:///:memory:"})

    class ScopedRecord(Model):
        value: str

    first = create_database({"db_engine": "sqlite", "db_uri": "sqlite:///:memory:"})
    second = create_database({"db_engine": "sqlite", "db_uri": "sqlite:///:memory:"})

    try:
        with db.use(first):
            ScopedRecord(value="first").save()

            assert [record.value for record in ScopedRecord.objects().all()] == ["first"]

        with db.use(second):
            assert ScopedRecord.objects().all() == []

            ScopedRecord(value="second").save()

            assert [record.value for record in ScopedRecord.objects().all()] == ["second"]

        with db.use(first):
            assert [record.value for record in ScopedRecord.objects().all()] == ["first"]
    finally:
        first.close()
        second.close()
        fallback.close()
        db.close()


def test_database_transaction_holds_the_connection_lock_until_completion():
    database = create_database({"db_engine": "sqlite", "db_uri": "sqlite:///:memory:"})
    entered = threading.Event()
    release = threading.Event()
    second_finished = threading.Event()

    try:
        database.execute("CREATE TABLE transaction_lock (value TEXT)")

        def first_request():
            with database.transaction():
                database.execute("INSERT INTO transaction_lock (value) VALUES ('first')")
                entered.set()
                release.wait(timeout=2)

        def second_request():
            entered.wait(timeout=2)
            database.execute("INSERT INTO transaction_lock (value) VALUES ('second')")
            second_finished.set()

        first = threading.Thread(target=first_request)
        second = threading.Thread(target=second_request)
        first.start()
        second.start()

        assert entered.wait(timeout=1)
        assert not second_finished.wait(timeout=0.05)

        release.set()
        first.join(timeout=2)
        second.join(timeout=2)

        assert second_finished.is_set()
        assert database.fetchone("SELECT COUNT(1) AS count FROM transaction_lock")["count"] == 2
    finally:
        database.close()


def test_immediate_migration_transaction_preserves_commit_error_and_releases_lock():
    class FailingCommitProvider(DatabaseProvider):
        def connect(self):
            pass

        def close(self):
            pass

        def begin_immediate(self):
            pass

        def commit(self):
            raise RuntimeError("commit failed")

        def rollback(self):
            pass

    database = Database(FailingCommitProvider())
    try:
        with pytest.raises(RuntimeError, match="commit failed"):
            with database.migration_transaction():
                pass

        acquired = threading.Event()
        thread = threading.Thread(target=lambda: (database._lock.acquire(), acquired.set(), database._lock.release()))
        thread.start()
        thread.join(timeout=1)

        assert acquired.is_set(), "migration transaction leaked the database lock"
    finally:
        database.close()


def test_migration_lock_cleanup_does_not_mask_a_failed_commit():
    class FailingProvider(DatabaseProvider):
        def connect(self):
            pass

        def close(self):
            pass

        def begin_immediate(self):
            pass

        def commit(self):
            raise ValueError("commit failed")

        def rollback(self):
            pass

        def acquire_migration_lock(self, _name):
            pass

        def release_migration_lock(self, _name):
            raise RuntimeError("unlock failed")

    database = Database(FailingProvider())

    try:
        with pytest.raises(ValueError, match="commit failed"):
            with database.migration_lock("test"):
                with database.migration_transaction():
                    pass
    finally:
        database.close()
