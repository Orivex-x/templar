"""Backward-compatible deployment imports.

The supported command-line implementation lives in ``templar.cli.commands.Deploy``.
This module keeps the original deployment imports stable without registering a
second, incompatible CLI implementation.
"""

from templar.core.deployment.DockerProvider import DockerProvider
from templar.core.deployment.Errors import DeployError
from templar.core.deployment.Manager import DeploymentManager, run_or_fail
from templar.core.deployment.Provider import Provider
from templar.core.deployment.SshProvider import SSHProvider

__all__ = [
    "DeploymentManager",
    "DockerProvider",
    "DeployError",
    "Provider",
    "SSHProvider",
    "run_or_fail",
]
