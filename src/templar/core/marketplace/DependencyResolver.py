import sys
from functools import cmp_to_key
from typing import Callable, Dict, Optional

from templar.core.marketplace.SemVer import SemVer

sys.dont_write_bytecode = True

class DependencyResolver:
    """Resolves package dependencies with conflict detection."""

    def __init__(self, registry, ensure_available: Optional[Callable[[str], None]] = None) -> None:
        self.registry = registry
        self.ensure_available = ensure_available
        self.resolved: Dict[str, str] = {}

    def resolve(self, deps: Dict[str, str]) -> Dict[str, str]:
        if not isinstance(deps, dict) or not all(
            isinstance(name, str) and isinstance(constraint, str)
            for name, constraint in deps.items()
        ):
            raise RuntimeError("Dependencies must map package names to version constraints")

        self.resolved = {}
        constraints = {name: [constraint] for name, constraint in deps.items()}

        if not self._solve(constraints):
            details = ", ".join(
                f"{name} ({', '.join(required)})" for name, required in constraints.items()
            )

            raise RuntimeError(f"Cannot resolve compatible package versions: {details}")

        return dict(self.resolved)

    def _candidates(self, name: str, constraints: list[str]) -> list[str]:
        available = self.registry.list_versions(name)
        candidates = [
            version for version in available
            if all(SemVer.satisfies(version, constraint) for constraint in constraints)
        ]

        if not candidates and self.ensure_available:
            self.ensure_available(name)
            available = self.registry.list_versions(name)
            candidates = [
                version for version in available
                if all(SemVer.satisfies(version, constraint) for constraint in constraints)
            ]

        return sorted(candidates, key=cmp_to_key(SemVer.compare), reverse=True)

    def _dependencies_for(self, name: str, version: str) -> Dict[str, str]:
        manifest = self.registry.get_manifest(name, version)
        subdeps = manifest.get("dependencies", {})

        if not isinstance(subdeps, dict) or not all(
            isinstance(dependency, str) and isinstance(constraint, str)
            for dependency, constraint in subdeps.items()
        ):
            raise RuntimeError(f"Invalid dependencies in {name}@{version}")

        return subdeps

    def _solve(self, constraints: Dict[str, list[str]]) -> bool:
        unresolved = [name for name in constraints if name not in self.resolved]

        if not unresolved:
            return all(
                all(SemVer.satisfies(self.resolved[name], constraint) for constraint in required)
                for name, required in constraints.items()
            )

        choices = [(name, self._candidates(name, constraints[name])) for name in unresolved]
        name, candidates = min(choices, key=lambda item: len(item[1]))

        for version in candidates:
            self.resolved[name] = version
            updated = {dependency: list(required) for dependency, required in constraints.items()}

            for dependency, constraint in self._dependencies_for(name, version).items():
                updated.setdefault(dependency, []).append(constraint)

            if self._solve(updated):
                return True

            self.resolved.pop(name, None)

        return False
    
