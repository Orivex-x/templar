import hashlib
import sqlite3
from types import SimpleNamespace

import pytest

from templar.auth import PasswordManager
from templar.auth import Auth
from templar.auth.Permission import require_auth, require_permission, require_role
from templar.auth.User import User
from templar.core.Exceptions import PermissionDeniedError, UnauthorizedError
from templar.db import create_database, db
from templar.middleware.AuthMiddleware import install as install_auth_middleware
from templar.middleware.MiddlewareManager import MiddlewareManager
from templar.Session import MemorySessionStore


def test_password_hashes_remain_verifiable_across_iteration_policy_changes():
    salt = "legacy-salt"
    legacy_digest = hashlib.pbkdf2_hmac("sha256", b"correct horse", salt.encode("utf-8"), 1_000).hex()
    legacy_hash = f"pbkdf2_sha256$1000${salt}${legacy_digest}"

    assert PasswordManager.verify_password("correct horse", legacy_hash)
    assert not PasswordManager.verify_password("wrong", legacy_hash)


def test_password_verification_rejects_invalid_iteration_counts():
    invalid_hash = "pbkdf2_sha256$0$salt$deadbeef"

    assert not PasswordManager.verify_password("password", invalid_hash)


def test_password_hashing_rejects_boolean_work_factors():
    import pytest

    with pytest.raises(ValueError, match="iterations"):
        PasswordManager.hash_password("password", iterations=True)


def test_password_hashing_rejects_work_factors_below_the_current_minimum():
    import pytest

    with pytest.raises(ValueError, match="iterations"):
        PasswordManager.hash_password("password", iterations=1)


def test_all_session_backends_require_json_compatible_values():
    store = MemorySessionStore()

    with pytest.raises(TypeError, match="JSON serializable"):
        store.create({"unserializable": object()})


def test_user_model_preserves_declared_schema_and_private_persistence_data(tmp_path):
    database = create_database({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'users.db'}"})

    try:
        with db.use(database):
            assert User._table == "users"
            assert {"username", "email", "password_hash", "roles", "permissions"} <= set(User._fields)

            password_hash = PasswordManager.hash_password("correct horse")
            user = User(
                username="ada",
                email="ada@example.com",
                password_hash=password_hash,
                roles=["admin"],
                permissions=["users:read"],
            )
            original_created_at = user.created_at
            user.save()

            stored = database.fetchone(
                "SELECT password_hash, roles, permissions, created_at FROM users WHERE id=:id",
                {"id": user.id},
            )

            assert stored == {
                "password_hash": password_hash,
                "roles": '["admin"]',
                "permissions": '["users:read"]',
                "created_at": original_created_at,
            }

            loaded = User.get_by_username("ada")

            assert loaded is not None
            assert loaded.created_at == original_created_at
            assert loaded.roles == ["admin"]
            assert loaded.permissions == ["users:read"]
            assert loaded.to_dict()["username"] == "ada"
            assert "password_hash" not in loaded.to_dict()
            assert loaded.to_record()["password_hash"] == password_hash

            with pytest.raises(sqlite3.IntegrityError):
                User(
                    username="ada",
                    email="other@example.com",
                    password_hash=password_hash,
                ).save()
            with pytest.raises(sqlite3.IntegrityError):
                User(
                    username="other",
                    email="ada@example.com",
                    password_hash=password_hash,
                ).save()
    finally:
        database.close()


def test_user_extensions_inherit_the_full_authentication_schema_without_import_side_effects():
    # Model declaration must remain side-effect free: importing a model should
    # not create a fallback database before an application/server chooses one.
    db.close()

    class ExtendedUser(User):
        display_name: str

    assert db._default_database is None
    assert ExtendedUser._table == "extended_user"
    assert {"username", "email", "password_hash", "is_active", "roles", "permissions", "display_name"} <= set(ExtendedUser._fields)
    assert ExtendedUser._unique_fields == ("username", "email")
    assert {"username", "email", "password_hash"} <= set(ExtendedUser._required_fields)


def test_user_activity_flags_are_strict_and_inactive_string_loader_results_fail_closed():
    password_hash = PasswordManager.hash_password("correct horse")

    assert User("disabled", "disabled@example.com", password_hash, is_active="false").is_active is False
    assert User("enabled", "enabled@example.com", password_hash, is_active="1").is_active is True

    with pytest.raises(ValueError, match="is_active"):
        User("unknown", "unknown@example.com", password_hash, is_active="certainly")

    auth = Auth("test-secret")

    assert not auth._user_is_active({"is_active": "false"})
    assert not auth._user_is_active({"is_active": "0"})

    manager = MiddlewareManager()
    install_auth_middleware(manager)
    context = SimpleNamespace(
        session={"user_id": 8},
        server=SimpleNamespace(user_loader=lambda _user_id: {"id": 8, "is_active": "false"}),
        user=None,
    )
    manager.run_before(context)

    assert context.session == {}
    assert context.user is None


def test_user_identity_fields_are_required_in_python_and_new_database_schema(tmp_path):
    password_hash = PasswordManager.hash_password("correct horse")

    for field_values in ((None, "ada@example.com", password_hash), ("ada", None, password_hash), ("ada", "ada@example.com", None)):
        with pytest.raises(ValueError, match="non-empty"):
            User(*field_values)

    database = create_database({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'required-users.db'}"})

    try:
        with db.use(database):
            User.objects()
            columns = {row["name"]: row for row in database.fetchall("PRAGMA table_info(users)")}

            assert columns["username"]["notnull"] == 1
            assert columns["email"]["notnull"] == 1
            assert columns["password_hash"]["notnull"] == 1
    finally:
        database.close()


def test_user_schema_adds_named_unique_indexes_to_existing_sqlite_tables(tmp_path):
    database = create_database({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'legacy-users.db'}"})

    try:
        database.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, email TEXT, "
            "password_hash TEXT, is_active INTEGER, roles TEXT, permissions TEXT, created_at TEXT, "
            "updated_at TEXT, last_login TEXT)"
        )
        with db.use(database):
            with pytest.raises(RuntimeError, match="templar migrate user-schema"):
                User.objects()

            User.migrate_schema(database)
            indexes = {row["name"]: row for row in database.fetchall("PRAGMA index_list(users)")}

            assert indexes["users_username_uniq"]["unique"] == 1
            assert indexes["users_email_uniq"]["unique"] == 1

            columns = {row["name"]: row for row in database.fetchall("PRAGMA table_info(users)")}

            assert columns["username"]["notnull"] == 1
            assert columns["email"]["notnull"] == 1
            assert columns["password_hash"]["notnull"] == 1
    finally:
        database.close()


def test_user_schema_requires_migration_when_legacy_identity_columns_are_not_unique(tmp_path):
    database = create_database({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'nonunique-users.db'}"})

    try:
        database.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, email TEXT NOT NULL, "
            "password_hash TEXT NOT NULL, is_active INTEGER NOT NULL, roles TEXT NOT NULL, permissions TEXT NOT NULL, "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_login TEXT)"
        )

        with db.use(database):
            with pytest.raises(RuntimeError, match="missing unique constraints.*templar migrate user-schema"):
                User.objects()

            User.migrate_schema(database)
            indexes = {row["name"]: row for row in database.fetchall("PRAGMA index_list(users)")}

            assert indexes["users_username_uniq"]["unique"] == 1
            assert indexes["users_email_uniq"]["unique"] == 1
    finally:
        database.close()


def test_user_schema_rejects_conflicting_legacy_framework_index_names(tmp_path):
    database = create_database({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'conflicting-index.db'}"})

    try:
        database.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, email TEXT NOT NULL, "
            "password_hash TEXT NOT NULL, is_active INTEGER NOT NULL, roles TEXT NOT NULL, permissions TEXT NOT NULL, "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_login TEXT)"
        )

        database.execute("CREATE INDEX users_username_uniq ON users(username)")

        with db.use(database):
            with pytest.raises(RuntimeError, match="users_username_uniq conflicts"):
                User.migrate_schema(database)

            indexes = {row["name"]: row for row in database.fetchall("PRAGMA index_list(users)")}

            assert indexes["users_username_uniq"]["unique"] == 0
    finally:
        database.close()


def test_custom_user_models_receive_their_own_schema_migration_hint_and_upgrade(tmp_path):
    class Account(User):
        display_name: str

    database = create_database({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'legacy-account.db'}"})

    try:
        database.execute(
            "CREATE TABLE account (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, email TEXT, password_hash TEXT, "
            "is_active INTEGER, roles TEXT, permissions TEXT, created_at TEXT, updated_at TEXT, last_login TEXT, display_name TEXT)"
        )

        with db.use(database):
            with pytest.raises(RuntimeError, match=r"user-schema --model"):
                Account.objects()

            Account.migrate_schema(database)
            indexes = {row["name"]: row for row in database.fetchall("PRAGMA index_list(account)")}

            assert indexes["account_username_uniq"]["unique"] == 1
            assert indexes["account_email_uniq"]["unique"] == 1
    finally:
        database.close()


def test_explicit_sqlite_user_migration_preserves_indexes_and_triggers(tmp_path):
    database = create_database({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'legacy-objects.db'}"})

    try:
        database.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, email TEXT, "
            "password_hash TEXT, is_active INTEGER, roles TEXT, permissions TEXT, created_at TEXT, "
            "updated_at TEXT, last_login TEXT)"
        )
        database.execute("CREATE TABLE audit (event TEXT)")
        database.execute("CREATE INDEX legacy_users_last_login ON users(last_login)")
        database.execute(
            "CREATE TRIGGER legacy_users_audit AFTER INSERT ON users "
            "BEGIN INSERT INTO audit(event) VALUES ('insert'); END"
        )

        User.migrate_schema(database)

        objects = {
            row["name"]: row["type"]
            for row in database.fetchall("SELECT type, name FROM sqlite_master WHERE tbl_name='users'")
        }

        assert objects["legacy_users_last_login"] == "index"
        assert objects["legacy_users_audit"] == "trigger"
    finally:
        database.close()


def test_authenticate_accepts_active_user_objects_and_rejects_inactive_ones():
    auth = Auth("test-secret")
    password_hash = PasswordManager.hash_password("correct horse")
    active = User("ada", "ada@example.com", password_hash, id=7)
    inactive = User("disabled", "disabled@example.com", password_hash, is_active=False, id=8)

    session = {}

    assert auth.authenticate("ada", "correct horse", lambda _username: active, session)
    assert session["user_id"] == 7
    assert auth.has_role(SimpleNamespace(user=active), "") is False

    active.roles.append("admin")
    active.permissions.append("users:read")

    assert auth.has_role(SimpleNamespace(user=active), "admin")
    assert auth.has_permission(SimpleNamespace(user=active), "users:read")
    assert not auth.authenticate("disabled", "correct horse", lambda _username: inactive, {})


def test_auth_middleware_revokes_sessions_for_inactive_user_objects():
    manager = MiddlewareManager()
    install_auth_middleware(manager)
    inactive = User("disabled", "disabled@example.com", "not-used", is_active=False, id=8)
    context = SimpleNamespace(
        session={"user_id": 8},
        server=SimpleNamespace(user_loader=lambda _user_id: inactive),
        user=None,
    )

    manager.run_before(context)

    assert context.session == {}
    assert context.user is None


def test_mapping_user_loaders_normalize_claims_and_require_the_session_identity():
    manager = MiddlewareManager()
    install_auth_middleware(manager)
    context = SimpleNamespace(
        session={"user_id": 8},
        server=SimpleNamespace(
            user_loader=lambda _user_id: {
                "id": 8,
                "is_active": True,
                "roles": '["admin"]',
                "permissions": '["users:read"]',
            }
        ),
        user=None,
    )
    manager.run_before(context)

    assert context.user["roles"] == ["admin"]
    assert context.user["permissions"] == ["users:read"]

    mismatched = SimpleNamespace(
        session={"user_id": 8},
        server=SimpleNamespace(user_loader=lambda _user_id: {"id": 9, "is_active": True}),
        user=None,
    )

    manager.run_before(mismatched)

    assert mismatched.session == {}
    assert mismatched.user is None


def test_permission_decorators_use_request_scoped_user():
    request = SimpleNamespace(user={"roles": ["admin"], "permissions": ["users:read"]})

    @require_auth
    def authenticated(ctx):
        return ctx.user

    @require_permission("users:read")
    def can_read(_ctx):
        return "allowed"

    @require_role("admin")
    def is_admin(_ctx):
        return "allowed"

    assert authenticated(request) is request.user
    assert can_read(request) == "allowed"
    assert is_admin(request) == "allowed"

    with pytest.raises(UnauthorizedError):
        authenticated(SimpleNamespace(user=None))


def test_malformed_string_claims_never_grant_permissions_or_roles():
    request = SimpleNamespace(user={"id": 1, "roles": "not-admin", "permissions": "not-admin"})

    @require_permission("admin")
    def protected(_request):
        return "granted"

    @require_role("admin")
    def role_protected(_request):
        return "granted"

    with pytest.raises(PermissionDeniedError):
        protected(request)

    with pytest.raises(PermissionDeniedError):
        role_protected(request)

    assert not Auth("test-secret").has_permission(request, "admin")
    assert not Auth("test-secret").has_role(request, "admin")


def test_user_save_refreshes_updated_at_for_normal_updates(tmp_path):
    database = create_database({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'timestamps.db'}"})

    try:
        with db.use(database):
            user = User("ada", "ada@example.com", PasswordManager.hash_password("correct horse"))
            user.save()
            initial_timestamp = user.updated_at
            user.email = "ada.lovelace@example.com"
            user.save()

            assert user.updated_at > initial_timestamp
            assert User.get_by_username("ada").updated_at == user.updated_at
    finally:
        database.close()
