import sys, subprocess, logging

from templar.core.deployment.Errors import DeployError
from templar.core.deployment.Provider import Provider

sys.dont_write_bytecode = True

logger = logging.getLogger("templar.deployment.docker")

class DockerProvider(Provider):
    def deploy(self, source_dir: str, opts: dict):
        image = opts.get("image") or self.cfg.get("image")
        tag = opts.get("tag") or self.cfg.get("tag") or "latest"
        push = opts.get("push") or self.cfg.get("push") or False

        if not image:
            raise DeployError("docker provider requires image name")

        full = f"{image}:{tag}"
        logger.info("Building docker image %s", full)
        completed = subprocess.run(["docker", "build", "-t", full, source_dir])

        if completed.returncode != 0:
            raise DeployError("docker build failed")

        if push:
            logger.info("Pushing docker image %s", full)
            completed = subprocess.run(["docker", "push", full])
            
            if completed.returncode != 0:
                raise DeployError("docker push failed")

        return {"status": "ok", "meta": {"image": full, "pushed": push}}
