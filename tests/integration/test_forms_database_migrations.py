from pathlib import Path

import pytest

from templar.forms import EmailField, Form, TextField
from templar.forms.Form import LoginForm, RegistrationForm
from templar.db import create_database, db
from templar.migrations import MigrationGenerator, MigrationRunner


class AccountForm(Form):
    username = TextField(required=True, max_length=32)
    email = EmailField(required=True)


@pytest.mark.integration
def test_declared_and_builtin_forms_validate_and_render_independently():
    valid = AccountForm({"username": "ada", "email": "ada@example.com"})
    invalid = AccountForm({"username": "", "email": "not-an-email"})

    assert valid.validate() is True
    assert invalid.validate() is False
    assert "username" in invalid.errors
    assert valid.get_field("username").value == "ada"
    assert 'name="username"' in valid.render().render()

    rendered_with_csrf = valid.render(csrf_token="csrf-value").render()

    assert 'name="csrf_token"' in rendered_with_csrf
    assert 'type="hidden"' in rendered_with_csrf
    assert 'value="csrf-value"' in rendered_with_csrf

    login = LoginForm({"username": "ada", "password": "password"})

    assert list(login.fields) == ["username", "password"]
    assert login.validate() is True

    registration = RegistrationForm({
        "username": "ada",
        "email": "ada@example.com",
        "password": "password123",
        "password_confirm": "different",
    })

    assert registration.validate() is False
    assert registration.errors["password_confirm"] == ["Passwords do not match"]


@pytest.mark.integration
@pytest.mark.db
def test_configured_sqlite_database_runs_and_rolls_back_migrations(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    (migrations_dir / "001_create_accounts.py").write_text(
        "from templar.migrations import Migration\n"
        "class CreateAccounts(Migration):\n"
        "    def up(self, db):\n"
        "        db.execute('CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL)')\n"
        "    def down(self, db):\n"
        "        db.execute('DROP TABLE accounts')\n"
    )
    (migrations_dir / "002_add_email.py").write_text(
        "from templar.migrations import Migration\n"
        "class AddEmail(Migration):\n"
        "    def up(self, db):\n"
        "        db.execute('ALTER TABLE accounts ADD COLUMN email TEXT')\n"
        "    def down(self, db):\n"
        "        # SQLite does not support DROP COLUMN; recreate for this test.\n"
        "        db.execute('CREATE TABLE accounts_new (id INTEGER PRIMARY KEY, name TEXT NOT NULL)')\n"
        "        db.execute('INSERT INTO accounts_new (id, name) SELECT id, name FROM accounts')\n"
        "        db.execute('DROP TABLE accounts')\n"
        "        db.execute('ALTER TABLE accounts_new RENAME TO accounts')\n"
    )

    config = {"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'app.db'}"}

    database = create_database(config)

    try:
        runner = MigrationRunner(database, migrations_dir)

        assert runner.run_pending_migrations() == ["001_create_accounts", "002_add_email"]

        database.execute(
            "INSERT INTO accounts (name, email) VALUES (:name, :email)",
            {"name": "Ada", "email": "ada@example.com"},
        )

        assert database.query("SELECT name, email FROM accounts") == [{"name": "Ada", "email": "ada@example.com"}]
        assert runner.rollback_migrations() == ["002_add_email", "001_create_accounts"]
        assert database.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'") is None
    finally:
        database.close()


def test_runner_loads_legacy_migration_import_path_without_shadowing_base_class(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_legacy_import.py").write_text(
        "from templar.migrations.Migration import Migration\n"
        "class LegacyImport(Migration):\n"
        "    def up(self, db): db.execute('CREATE TABLE legacy_import (id INTEGER PRIMARY KEY)')\n"
        "    def down(self, db): db.execute('DROP TABLE legacy_import')\n"
    )

    database = create_database({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'app.db'}"})

    try:
        runner = MigrationRunner(database, migrations_dir)

        assert runner.run_pending_migrations() == ["001_legacy_import"]
        assert database.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='legacy_import'")
    finally:
        database.close()


@pytest.mark.integration
@pytest.mark.db
def test_database_proxy_configures_sqlite_without_optional_database_drivers(tmp_path):
    database = db.configure({"db_engine": "sqlite", "db_uri": f"sqlite:///{tmp_path / 'proxy.db'}"})

    try:
        db.execute("CREATE TABLE values_table (value TEXT)")
        db.execute("INSERT INTO values_table (value) VALUES (:value)", {"value": "ok"})

        assert database.fetchone("SELECT value FROM values_table") == {"value": "ok"}
    finally:
        db.close()


@pytest.mark.integration
def test_migration_generator_rejects_unsafe_or_invalid_names(tmp_path):
    migrations_dir = tmp_path / "migrations"

    with pytest.raises(ValueError, match="lowercase letters"):
        MigrationGenerator.generate_migration("add-users", migrations_dir)

    with pytest.raises(ValueError, match="lowercase letters"):
        MigrationGenerator.generate_migration("../escape", migrations_dir)

    generated = MigrationGenerator.generate_migration("add_users", migrations_dir)

    assert generated.parent == migrations_dir
    assert "class AddUsers(Migration):" in generated.read_text()


def test_migration_tracking_schema_does_not_require_sqlite_autoincrement(tmp_path):
    class RecordingDatabase:
        def __init__(self):
            self.statements = []

        def execute(self, sql, _params=None):
            self.statements.append(sql)

    database = RecordingDatabase()
    MigrationRunner(database, tmp_path / "migrations")

    schema = database.statements[0]

    assert "name VARCHAR(255) PRIMARY KEY" in schema
    assert "id INTEGER PRIMARY KEY" not in schema
