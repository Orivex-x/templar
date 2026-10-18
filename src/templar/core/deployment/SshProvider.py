import logging
import shutil
import subprocess
from typing import Dict, Any
from templar.core.deployment.Errors import DeployError
from templar.core.deployment.Provider import Provider

logger = logging.getLogger("templar.deployment.ssh")

class SSHProvider(Provider):
    def _run(self, command: list[str]):
        logger.debug("SSH -> %s", command)
        completed = subprocess.run(command, check=False)

        if completed.returncode != 0:
            raise DeployError(f"SSH command failed: {' '.join(command)}")

    def deploy(self, source_dir: str, opts: Dict[str, Any]):
        host = opts.get("host") or self.cfg.get("host")
        user = opts.get("user") or self.cfg.get("user")
        dest = opts.get("dest") or self.cfg.get("dest")
        ssh_key = opts.get("ssh_key") or self.cfg.get("ssh_key")

        if not host or not user or not dest:
            raise DeployError("ssh provider requires host, user and dest")

        if not shutil.which("ssh") or not shutil.which("scp"):
            raise DeployError(
                "SSH deployment requires the OpenSSH client (ssh and scp) on this platform."
            )

        ssh_options = ["-i", str(ssh_key)] if ssh_key else []
        destination = f"{user}@{host}:{dest}"
        logger.info("Syncing to %s@%s:%s", user, host, dest)
        source_contents = str(source_dir).rstrip("/\\") + "/."
        self._run(["scp", *ssh_options, "-r", source_contents, destination])

        remote_commands = opts.get("remote_commands") or self.cfg.get("remote_commands") or []

        for rc in remote_commands:
            logger.info("Running remote command: %s", rc)
            self._run(["ssh", *ssh_options, f"{user}@{host}", str(rc)])

        return {"status": "ok", "meta": {"host": host, "dest": dest}}
