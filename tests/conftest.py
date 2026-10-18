"""Pytest configuration and shared fixtures."""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

# Add the src-layout package to path when tests run without an editable installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from templar.Config import Config
from templar.Router import Router
from templar.Renderer import Renderer
from templar.cli.CliOutput import CliOutput

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Create project structure
        (project_path / "templates").mkdir()
        (project_path / "themes").mkdir()
        (project_path / "static").mkdir()
        (project_path / "logs").mkdir()
        
        # Create a basic template
        (project_path / "templates" / "index.templar.py").write_text(
            "def render(**context):\n"
            "    from templar.core.elements.Div import Div\n"
            "    return Div('Hello')\n"
        )
        
        yield project_path


@pytest.fixture
def sample_config(temp_project_dir):
    """Create a sample configuration."""
    config_path = temp_project_dir / "templar.config.yml"
    config_path.write_text(
        """
dev:
  mode: dev
  host: 127.0.0.1
  port: 8000
  debug: true
  theme: light
  templates_dir: templates
  themes_dir: themes
  static_dir: static
  session_secret: test-secret
  log_file: logs/dev.log
  cache_backend: memory
  db_engine: sqlite
  db_uri: sqlite:///:memory:

prod:
  mode: prod
  host: 0.0.0.0
  port: 8000
  debug: false
  deployment_domain: example.com
  ssl_cert_path: /etc/ssl/certs/cert.pem
  ssl_key_path: /etc/ssl/private/key.pem
  session_secret: prod-secret
  log_file: logs/prod.log
  cache_backend: redis
  db_engine: postgresql
  db_uri: postgresql://user:pass@localhost/dbname

active: dev
"""
    )
    
    config = Config(config_path=str(config_path))
    yield config

@pytest.fixture
def router(sample_config):
    """Create a router with sample routes."""
    router = Router(sample_config)
    router.add("/", "index")
    router.add("/about", "about")
    router.add("/user/<id>", "user")
    router.add("/product/<category>/<pid>", "product")
    yield router

@pytest.fixture
def mock_cli_output():
    """Create a mock CliOutput."""
    output = Mock(spec=CliOutput)
    output.panel = Mock()
    output.table = Mock()
    output.print = Mock()
    yield output

@pytest.fixture
def renderer(sample_config, temp_project_dir):
    """Create a renderer instance."""
    renderer = Renderer(
        sample_config,
        temp_project_dir / "templates",
        temp_project_dir / "themes",
        temp_project_dir / "static"
    )
    yield renderer
