import os
import shutil
import subprocess
import sys
import tempfile
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any

from templar.core.deployment.Errors import DeployError
from templar.core.deployment.SshProvider import SSHProvider
from templar.core.deployment.DockerProvider import DockerProvider
from templar.core.deployment.Provider import Provider

sys.dont_write_bytecode = True

logger = logging.getLogger("templar.deployment.manager")

DEFAULT_DEPLOY_IGNORES = [
    ".git", "__pycache__", "*.py[cod]", "node_modules", ".venv", "venv",
    ".env", ".env.*", ".gnupg", "*.pem", "*.key", "*.p12", "*.pfx",
    "*.db", "*.sqlite", "*.sqlite3", "db", "logs", "templar_packages",
    # Common private-key and credential stores whose names do not necessarily
    # have a filename extension.
    ".ssh", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".aws", ".azure",
    ".gcloud", ".kube", ".docker", ".npmrc", ".pypirc", ".netrc", "credentials",
]

def run_or_fail(command: list[str], *, cwd: str | None = None) -> None:
    """Run a command without relying on a platform-specific shell."""
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise DeployError(f"Command failed: {' '.join(command)}")

@dataclass
class DeploymentManager:
    project_root: str = field(default_factory=os.getcwd)
    providers: Dict[str, Provider] = field(default_factory=dict)

    def __post_init__(self):
        self.providers.setdefault("ssh", SSHProvider())
        self.providers.setdefault("docker", DockerProvider())

    def prepare_source(self, ignore=None) -> str:
        project_root = Path(self.project_root).resolve()

        if not project_root.is_dir():
            raise DeployError(f"Deployment project root does not exist: {project_root}")

        # copytree follows symlinks by default. Validate targets first so an innocuous project filename cannot materialize
        # a file from ~/.ssh or another external location in a Docker context/deployment upload.
        for source in project_root.rglob("*"):
            if not source.is_symlink():
                continue

            target = source.resolve()

            if target != project_root and project_root not in target.parents:
                raise DeployError(f"Deployment source contains an external symlink: {source}")

        project_ignore = Path(self.project_root) / ".templarignore"
        project_patterns = []

        if project_ignore.is_file():
            project_patterns = [
                line.strip() for line in project_ignore.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]

        ignore = [*DEFAULT_DEPLOY_IGNORES, *project_patterns, *(ignore or [])]
        tmpdir = tempfile.mkdtemp(prefix="templar-deploy-")
        dest = os.path.join(tmpdir, "deploy")
        shutil.copytree(
            project_root, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*ignore)
        )

        return dest

    def run_tests(self):
        logger.info("Running project tests with pytest")

        if shutil.which("pytest"):
            run_or_fail(["pytest", "-q"], cwd=self.project_root)
        else:
            run_or_fail([sys.executable, "-m", "pytest", "-q"], cwd=self.project_root)

    def build(self):
        logger.info("Building project when an npm build script is available")

        if (Path(self.project_root) / "package.json").is_file() and shutil.which("npm"):
            run_or_fail(["npm", "run", "build"], cwd=self.project_root)
        else:
            logger.info("No build step detected")

    def deploy(self, provider_name: str, opts: Dict[str, Any], dry_run: bool = False):
        provider = self.providers.get(provider_name)

        if not provider:
            raise DeployError(f"Unknown provider: {provider_name}")

        src = self.prepare_source()

        try:
            if dry_run:
                logger.info("Dry run: would deploy using %s with opts %s", provider_name, opts)

                return {"status": "dry-run"}

            return provider.deploy(src, opts)
        finally:
            try:
                shutil.rmtree(Path(src).parent)
            except Exception:
                pass
