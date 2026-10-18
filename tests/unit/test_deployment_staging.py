import shutil
from pathlib import Path

import pytest

from templar.core.deployment.Manager import DeploymentManager
from templar.core.deployment.Errors import DeployError


def test_deployment_staging_excludes_secrets_runtime_data_and_templarignore(tmp_path):
    (tmp_path / ".env").write_text("SECRET=value", encoding="utf-8")
    (tmp_path / "private.key").write_text("private", encoding="utf-8")
    (tmp_path / "id_rsa").write_text("private", encoding="utf-8")
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "config").write_text("private", encoding="utf-8")
    (tmp_path / ".aws").mkdir()
    (tmp_path / ".aws" / "credentials").write_text("private", encoding="utf-8")
    (tmp_path / "app.db").write_text("database", encoding="utf-8")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "app.log").write_text("log", encoding="utf-8")
    (tmp_path / "only-local.txt").write_text("local", encoding="utf-8")
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")
    (tmp_path / ".templarignore").write_text("only-local.txt\n", encoding="utf-8")

    prepared = Path(DeploymentManager(project_root=str(tmp_path)).prepare_source())

    try:
        assert (prepared / "keep.txt").is_file()

        for excluded in (".env", "private.key", "id_rsa", ".ssh", ".aws", "app.db", "logs", "only-local.txt"):
            assert not (prepared / excluded).exists()
    finally:
        shutil.rmtree(prepared.parent)


def test_deployment_staging_rejects_symlinks_to_external_files(tmp_path):
    external_secret = tmp_path.parent / "external-deployment-secret"
    external_secret.write_text("private", encoding="utf-8")
    (tmp_path / "innocent-name.txt").symlink_to(external_secret)

    with pytest.raises(DeployError, match="external symlink"):
        DeploymentManager(project_root=str(tmp_path)).prepare_source()
