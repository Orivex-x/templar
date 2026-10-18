import sys, json, re, shutil, tempfile
from pathlib import Path
from typing import Dict, List

sys.dont_write_bytecode = True

class Registry:
    """Local registry interface (can be extended to remote)."""

    def __init__(self, base_dir: str = "templar_packages") -> None:
        self.base = Path(base_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _component(value: str, label: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
            raise ValueError(f"Invalid package {label}")

        return value

    def list_versions(self, name: str) -> List[str]:
        name = self._component(name, "name")
        pkg_dir = self.base / name

        if not pkg_dir.exists():
            return []
        
        return [pkg.name for pkg in pkg_dir.iterdir() if pkg.is_dir()]

    def get_manifest(self, name: str, version: str) -> Dict:
        name = self._component(name, "name")
        version = self._component(version, "version")
        manifest_file = self.base / name / version / "manifest.json"

        if not manifest_file.exists():
            return {}

        return json.loads(manifest_file.read_text())

    def store_package(self, name: str, version: str, manifest: Dict, files: Dict[str, str]) -> None:
        name = self._component(name, "name")
        version = self._component(version, "version")

        if not isinstance(manifest, dict) or manifest.get("name") != name or str(manifest.get("version")) != version:
            raise ValueError("Package manifest name and version must match the requested package")

        pkg_dir = (self.base / name / version).resolve()

        if self.base not in pkg_dir.parents:
            raise ValueError("Package path must stay inside the registry")

        if pkg_dir.exists():
            raise FileExistsError(f"Package {name}@{version} already exists in the registry")

        if not isinstance(files, dict):
            raise ValueError("Package files must be a mapping of file names to text content")

        manifest_content = json.dumps(manifest, indent=2)
        validated_files = []

        for fname, content in files.items():
            if not isinstance(fname, str):
                raise ValueError(f"Package file name must be a string: {fname!r}")

            if not isinstance(content, str):
                raise ValueError(f"Package file content must be text: {fname!r}")

            target = (pkg_dir / fname).resolve()

            if target == pkg_dir or pkg_dir not in target.parents:
                raise ValueError(f"Package file path escapes its package directory: {fname!r}")

            validated_files.append((target.relative_to(pkg_dir), content))

        pkg_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix=f".{version}.", dir=pkg_dir.parent))

        try:
            (temp_dir / "manifest.json").write_text(manifest_content, encoding="utf-8")

            for relative_path, content in validated_files:
                target = temp_dir / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            temp_dir.replace(pkg_dir)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
