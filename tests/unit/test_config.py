"""Unit tests for Config module."""

import pytest
import yaml
from pathlib import Path
from templar.core.Exceptions import ConfigMissingError, ConfigInvalidError
from templar.Config import Config


@pytest.mark.unit
class TestConfig:
    """Tests for Config class."""
    
    def test_config_load_from_file(self, sample_config):
        """Test loading configuration from file."""
        assert sample_config is not None
        assert sample_config.active_env == "dev"
    
    def test_config_get_active_config(self, sample_config):
        """Test getting active environment config."""
        active = sample_config.get_active_config()

        assert active["mode"] == "dev"
        assert active["host"] == "127.0.0.1"
        assert active["port"] == 8000
    
    def test_config_get_dev_settings(self, sample_config):
        """Test accessing dev environment settings."""
        dev_config = sample_config._config.get("dev", {})

        assert dev_config["mode"] == "dev"
        assert dev_config["debug"] is True
        assert dev_config["cache_backend"] == "memory"
    
    def test_config_get_prod_settings(self, sample_config):
        """Test accessing prod environment settings."""
        prod_config = sample_config._config.get("prod", {})

        assert prod_config["mode"] == "prod"
        assert prod_config["debug"] is False
        assert prod_config["cache_backend"] == "redis"
    
    def test_config_property_access(self, sample_config):
        """Test accessing config properties."""
        assert sample_config.active_env == "dev"
        assert sample_config._active_config["port"] == 8000
    
    def test_config_theme_setting(self, sample_config):
        """Test theme configuration."""
        active = sample_config.get_active_config()

        assert active["theme"] == "light"
    
    def test_config_database_settings(self, sample_config):
        """Test database configuration."""
        active = sample_config.get_active_config()

        assert active["db_engine"] == "sqlite"
        assert "sqlite" in active["db_uri"]

    def test_missing_config_in_current_directory_is_bootstrapped(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        config = Config("templar.config.yml")

        assert (tmp_path / "templar.config.yml").is_file()
        assert config.active_env == "dev"

    def test_mutating_package_defaults_materializes_a_project_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        package_config_before = Path(Config.PACKAGE_CONFIG_PATH).read_text(encoding="utf-8")

        config = Config()
        config.set("theme", "dark")

        project_config = tmp_path / "templar.config.yml"

        assert project_config.is_file()
        assert config._config_path == str(project_config)
        assert yaml.safe_load(project_config.read_text(encoding="utf-8"))["dev"]["theme"] == "dark"
        assert Path(Config.PACKAGE_CONFIG_PATH).read_text(encoding="utf-8") == package_config_before

    def test_environment_references_dotenv_and_runtime_overrides(self, tmp_path, monkeypatch):
        (tmp_path / ".env").write_text("APP_SECRET=dotenv-secret\n", encoding="utf-8")
        config_path = tmp_path / "templar.config.yml"
        config_path.write_text(
            "active: prod\n"
            "dev: {mode: dev, session_secret: dev, log_file: logs/dev.log}\n"
            "prod:\n"
            "  mode: prod\n  session_secret: ${APP_SECRET}\n  log_file: logs/prod.log\n"
            "  deployment_domain: example.com\n  host: 127.0.0.1\n  ssl_cert_path: ''\n  ssl_key_path: ''\n  tls_terminated_by_proxy: true\n"
            "  db_engine: sqlite\n  db_uri: sqlite:///prod.db\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("TEMPLAR_HOST", "127.0.0.2")
        monkeypatch.setenv("TEMPLAR_PORT", "9010")

        config = Config(config_path=str(config_path))

        assert config.get("session_secret") == "dotenv-secret"
        assert config.get("host") == "127.0.0.2"
        assert config.get("port") == 9010

    def test_unset_environment_reference_is_rejected(self, tmp_path):
        config_path = tmp_path / "templar.config.yml"
        config_path.write_text("dev: {session_secret: '${MISSING_TEMPLAR_VALUE}'}\nprod: {}\n", encoding="utf-8")

        with pytest.raises(ValueError, match="unset environment variable"):
            Config(config_path=str(config_path))

    def test_production_only_reference_is_lazy_and_not_persisted(self, tmp_path):
        config_path = tmp_path / "templar.config.yml"
        original = (
            "active: dev\n"
            "dev: {mode: dev, session_secret: dev-secret, log_file: logs/dev.log}\n"
            "prod: {mode: prod, session_secret: '${TEMPLAR_SECRET_KEY}', log_file: logs/prod.log, "
            "deployment_domain: example.com, ssl_cert_path: '', ssl_key_path: '', tls_terminated_by_proxy: true, host: 127.0.0.1, db_engine: sqlite, db_uri: sqlite:///prod.db}\n"
        )
        config_path.write_text(original, encoding="utf-8")

        config = Config(config_path=str(config_path))
        config.set("theme", "dark")

        saved = config_path.read_text(encoding="utf-8")

        assert "${TEMPLAR_SECRET_KEY}" in saved

    def test_templar_env_selects_production_and_requires_resolved_secret(self, tmp_path, monkeypatch):
        config_path = tmp_path / "templar.config.yml"
        config_path.write_text(
            "active: dev\n"
            "dev: {mode: dev, session_secret: dev-secret, log_file: logs/dev.log}\n"
            "prod: {mode: prod, session_secret: '${TEMPLAR_SECRET_KEY}', log_file: logs/prod.log, "
            "deployment_domain: example.com, ssl_cert_path: '', ssl_key_path: '', tls_terminated_by_proxy: true, host: 127.0.0.1, db_engine: sqlite, db_uri: sqlite:///prod.db}\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("TEMPLAR_ENV", "prod")

        with pytest.raises(ValueError, match="unset environment variable"):
            Config(config_path=str(config_path))

        monkeypatch.setenv("TEMPLAR_SECRET_KEY", "production-secret")
        config = Config(config_path=str(config_path))

        assert config.active_env == "prod"
        assert config.get("session_secret") == "production-secret"

    def test_production_requires_explicit_tls_or_a_loopback_proxy_mode(self, tmp_path):
        config_path = tmp_path / "templar.config.yml"
        config_path.write_text(
            "active: prod\n"
            "dev: {mode: dev, session_secret: dev-secret, log_file: logs/dev.log}\n"
            "prod: {mode: prod, host: 0.0.0.0, session_secret: production-secret, log_file: logs/prod.log, "
            "deployment_domain: example.com, ssl_cert_path: '', ssl_key_path: '', db_engine: sqlite, db_uri: sqlite:///prod.db}\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="TLS certificates or explicit"):
            Config(config_path=str(config_path))

        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace("db_uri: sqlite:///prod.db}", "db_uri: sqlite:///prod.db, tls_terminated_by_proxy: true}"),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="loopback"):
            Config(config_path=str(config_path))

    def test_production_rejects_insecure_session_cookies(self, tmp_path):
        config_path = tmp_path / "templar.config.yml"
        config_path.write_text(
            "active: prod\n"
            "dev: {mode: dev, session_secret: dev-secret, log_file: logs/dev.log}\n"
            "prod: {mode: prod, host: 127.0.0.1, session_secret: production-secret, log_file: logs/prod.log, "
            "deployment_domain: example.com, ssl_cert_path: '', ssl_key_path: '', tls_terminated_by_proxy: true, "
            "session_cookie_secure: false, db_engine: sqlite, db_uri: sqlite:///prod.db}\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="session_cookie_secure"):
            Config(config_path=str(config_path))

    def test_production_runtime_host_override_cannot_bypass_proxy_loopback_rule(self, tmp_path):
        config_path = tmp_path / "templar.config.yml"
        config_path.write_text(
            "active: prod\n"
            "dev: {mode: dev, session_secret: dev-secret, log_file: logs/dev.log}\n"
            "prod: {mode: prod, host: 127.0.0.1, session_secret: production-secret, log_file: logs/prod.log, "
            "deployment_domain: example.com, ssl_cert_path: '', ssl_key_path: '', tls_terminated_by_proxy: true, "
            "session_cookie_secure: true, db_engine: sqlite, db_uri: sqlite:///prod.db}\n",
            encoding="utf-8",
        )
        config = Config(config_path=str(config_path))

        with pytest.raises(ValueError, match="loopback"):
            config.override("host", "0.0.0.0")

        assert config.get("host") == "127.0.0.1"

    def test_active_production_config_set_is_validated_before_persistence(self, tmp_path):
        config_path = tmp_path / "templar.config.yml"
        config_path.write_text(
            "active: prod\n"
            "dev: {mode: dev, session_secret: dev-secret, log_file: logs/dev.log}\n"
            "prod: {mode: prod, host: 127.0.0.1, session_secret: production-secret, log_file: logs/prod.log, "
            "deployment_domain: example.com, ssl_cert_path: '', ssl_key_path: '', tls_terminated_by_proxy: true, "
            "session_cookie_secure: true, db_engine: sqlite, db_uri: sqlite:///prod.db}\n",
            encoding="utf-8",
        )
        config = Config(config_path=str(config_path))

        with pytest.raises(ValueError, match="session_cookie_secure"):
            config.set("session_cookie_secure", False)

        assert config.get("session_cookie_secure") is True
        assert yaml.safe_load(config_path.read_text(encoding="utf-8"))["prod"]["session_cookie_secure"] is True

    def test_dotenv_values_are_instance_local_and_os_values_win(self, tmp_path, monkeypatch):
        monkeypatch.delenv("APP_SECRET", raising=False)

        def write_project(name, secret):
            project = tmp_path / name
            project.mkdir()
            (project / ".env").write_text(f"APP_SECRET={secret}\n", encoding="utf-8")
            config_path = project / "templar.config.yml"
            config_path.write_text(
                "active: dev\n"
                "dev: {mode: dev, session_secret: '${APP_SECRET}', log_file: logs/dev.log}\n"
                "prod: {}\n",
                encoding="utf-8",
            )

            return config_path

        first_path = write_project("first", "first-secret")
        second_path = write_project("second", "second-secret")

        assert Config(config_path=str(first_path)).get("session_secret") == "first-secret"
        assert Config(config_path=str(second_path)).get("session_secret") == "second-secret"
        assert "APP_SECRET" not in __import__("os").environ

        monkeypatch.setenv("APP_SECRET", "process-secret")

        assert Config(config_path=str(first_path)).get("session_secret") == "process-secret"
