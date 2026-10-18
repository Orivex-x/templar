import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from templar.Config import Config
from templar.Router import Router
from templar.cli.Cli import TemplarCLI
from templar.cli.commands.ConfigCmd import ConfigCommand
from templar.cli.commands.New import NewCommand
from templar.cli.commands.Run import RunCommand, auto_map_templates
from templar.cli.commands.Migrate import MigrateCommand


def config_set_args(*arguments):
    parser = argparse.ArgumentParser()
    ConfigCommand.add_args(parser)

    return parser.parse_args(arguments)


@pytest.mark.unit
def test_cli_discovers_the_supported_commands(monkeypatch, temp_project_dir):
    monkeypatch.chdir(temp_project_dir)
    cli = TemplarCLI()

    assert {
        "config", "create", "deploy", "help", "install-completion", "new",
        "migrate", "preview", "routes", "run", "shell", "marketplace-install",
        "marketplace-publish", "marketplace-sign", "marketplace-verify",
    }.issubset(cli.subparsers.choices)


@pytest.mark.unit
def test_config_command_sets_active_and_named_environment_values(sample_config, mock_cli_output):
    cli = SimpleNamespace(config=sample_config, output=mock_cli_output)
    command = ConfigCommand(cli)

    command.run(config_set_args("set", "port", "8123"))

    assert sample_config.get("port") == 8123

    command.run(config_set_args("set", "port", "9123", "--env", "prod"))

    assert sample_config.get_all()["prod"]["port"] == 9123


def test_config_display_redacts_sensitive_values_unless_explicitly_requested():
    assert ConfigCommand._display_value("session_secret", "top-secret", show_secrets=False) == "[redacted]"
    assert ConfigCommand._display_value("db_uri", "postgresql://user:password@host/db", show_secrets=False) == "[redacted]"
    assert ConfigCommand._display_value("session_secret", "top-secret", show_secrets=True) == "top-secret"


@pytest.mark.unit
def test_config_preserves_configured_project_paths_after_reload(sample_config, temp_project_dir):
    sample_config.set("templates_dir", "custom_templates")
    reloaded = Config(config_path=str(temp_project_dir / "templar.config.yml"))

    assert reloaded.get("templates_dir") == str((temp_project_dir / "custom_templates").resolve())


@pytest.mark.unit
def test_run_options_override_server_settings_without_rewriting_config(monkeypatch, sample_config, temp_project_dir, mock_cli_output):
    captured = {}

    class FakeServer:
        interrupted = False

        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self):
            captured["started"] = True

    monkeypatch.chdir(temp_project_dir)
    monkeypatch.setattr("templar.cli.commands.Run.TemplarServer", FakeServer)
    command = RunCommand(SimpleNamespace(config=sample_config, output=mock_cli_output))
    command.run(SimpleNamespace(prod=False, host="0.0.0.0", port=8123, theme="dark"))

    assert captured["started"] is True
    assert captured["config"].get("host") == "0.0.0.0"
    assert captured["config"].get("port") == 8123
    assert captured["config"].get("theme") == "dark"

    reloaded = Config(config_path=str(temp_project_dir / "templar.config.yml"))

    assert reloaded.get("host") == "127.0.0.1"
    assert reloaded.get("port") == 8000


@pytest.mark.unit
def test_run_honors_the_configured_active_production_environment(monkeypatch, sample_config, temp_project_dir, mock_cli_output):
    captured = {}

    class FakeServer:
        interrupted = False

        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self):
            pass

    sample_config.set_active_config("prod", persist=False)
    monkeypatch.chdir(temp_project_dir)
    monkeypatch.setattr("templar.cli.commands.Run.TemplarServer", FakeServer)
    RunCommand(SimpleNamespace(config=sample_config, output=mock_cli_output)).run(
        SimpleNamespace(prod=False, host=None, port=None, theme=None)
    )

    assert captured["config"].active_env == "prod"


@pytest.mark.unit
def test_run_merges_app_routes_without_losing_discovered_template_routes(monkeypatch, sample_config, temp_project_dir, mock_cli_output):
    captured = {}

    class FakeServer:
        interrupted = False

        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self):
            pass

    (temp_project_dir / "app.py").write_text(
        "from types import SimpleNamespace\n"
        "from templar.Router import Router\n"
        "router = Router(SimpleNamespace(default_route='index'))\n"
        "router.add('/custom', 'index')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(temp_project_dir)
    monkeypatch.setattr("templar.cli.commands.Run.TemplarServer", FakeServer)
    RunCommand(SimpleNamespace(config=sample_config, output=mock_cli_output)).run(
        SimpleNamespace(prod=False, host=None, port=None, theme=None)
    )

    assert captured["router"].match("/")[0] == "index.templar.py"
    assert captured["router"].match("/custom")[0] == "index.templar.py"


@pytest.mark.unit
def test_scaffolding_and_route_discovery_support_package_and_nested_templates(temp_project_dir):
    assert NewCommand()._resolve_skeleton_dir().is_dir()

    nested = temp_project_dir / "templates" / "auth"
    nested.mkdir()
    (nested / "login.templar.py").write_text("def render(**context): return 'ok'\n")
    router = Router(Config(config_path=str(temp_project_dir / "templar.config.yml")))
    auto_map_templates(router, temp_project_dir / "templates")
    template, _ = router.match("/auth/login")

    assert template == "auth/login.templar.py"


@pytest.mark.unit
def test_migrate_create_uses_the_active_configured_migrations_directory(sample_config, mock_cli_output):
    command = MigrateCommand(SimpleNamespace(config=sample_config, output=mock_cli_output))
    command.run(SimpleNamespace(action="create", name="add_accounts", step=1, migration_type="blank"))
    migration_files = list(Path(sample_config.get("migrations_dir")).glob("*_add_accounts.py"))

    assert len(migration_files) == 1


def test_migrate_user_schema_resolves_an_explicit_custom_user_model(tmp_path, monkeypatch):
    (tmp_path / "custom_users.py").write_text(
        "from templar.auth.User import User\n"
        "class Account(User):\n"
        "    display_name: str\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    model = MigrateCommand._resolve_user_model("custom_users:Account")

    assert model._table == "account"
    assert {"username", "email", "password_hash", "display_name"} <= set(model._fields)
