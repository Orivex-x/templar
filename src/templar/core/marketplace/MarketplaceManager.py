import sys, json, requests, base64, logging, shutil
from pathlib import Path
from typing import Dict, Tuple, Optional
from urllib.parse import quote, urlparse

from templar.core.marketplace.Registry import PACKAGE_TYPES, Registry
from templar.core.marketplace.DependencyResolver import DependencyResolver
from templar.core.marketplace.SemVer import SemVer

sys.dont_write_bytecode = True
logger = logging.getLogger("templar.marketplace")

DEFAULT_MAX_PACKAGE_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_FILE_COUNT = 1_000
DEFAULT_MAX_MANIFEST_BYTES = 256 * 1024


class MarketplaceManager:
    """Unified manager for packaging, publishing, and installing packages."""

    def __init__(
        self,
        registry_dir: str = "templar_packages",
        assets_dir: str = "static/assets/marketplace",
        remote_url: Optional[str] = None,
        max_package_bytes: int = DEFAULT_MAX_PACKAGE_BYTES,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_file_count: int = DEFAULT_MAX_FILE_COUNT,
        install_dirs: Optional[Dict[str, str | Path]] = None,
    ) -> None:
        self.registry = Registry(registry_dir)
        self.assets_dir = Path(assets_dir).resolve()
        self.install_dirs = {
            package_type: Path(path).resolve()
            for package_type, path in (install_dirs or {}).items()
        }
        self.install_dirs.setdefault("template", Path("templates").resolve())
        self.install_dirs.setdefault("utility", Path("utilities").resolve())
        self.install_dirs.setdefault("theme", Path("themes").resolve())
        self.install_dirs.setdefault("component", Path("components").resolve())
        self.remote_url = remote_url  # optional remote API base
        if self.remote_url:
            parsed_remote = urlparse(self.remote_url)
            is_loopback = parsed_remote.scheme == "http" and parsed_remote.hostname in {
                "localhost", "127.0.0.1", "::1",
            }
            if parsed_remote.scheme != "https" and not is_loopback:
                raise ValueError("Marketplace package transfers require HTTPS outside localhost.")

        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (max_package_bytes, max_file_bytes, max_file_count)):
            raise ValueError("Marketplace package limits must be positive integers")

        if max_file_bytes > max_package_bytes:
            raise ValueError("max_file_bytes cannot exceed max_package_bytes")

        self.max_package_bytes = max_package_bytes
        self.max_file_bytes = max_file_bytes
        self.max_file_count = max_file_count

    # -------------------------
    # Packaging
    # -------------------------
    @staticmethod
    def _package_artifact(manifest: Dict, encoded_files: Dict[str, str]) -> Dict[str, Dict]:
        if not isinstance(manifest, dict):
            raise ValueError("Package manifest must be an object")

        if not isinstance(encoded_files, dict) or not all(
            isinstance(filename, str) and isinstance(content, str)
            for filename, content in encoded_files.items()
        ):
            raise ValueError("Package files must map string names to base64 strings")

        return {"manifest": manifest, "files": encoded_files}

    @classmethod
    def _read_package_artifact(cls, package_path: str) -> Tuple[Dict, Dict[str, str]]:
        try:
            artifact = json.loads(Path(package_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid package artifact: {exc}") from exc

        if not isinstance(artifact, dict) or set(artifact) != {"manifest", "files"}:
            raise ValueError("Package artifact must contain exactly 'manifest' and 'files'")

        artifact = cls._package_artifact(artifact["manifest"], artifact["files"])

        return artifact["manifest"], artifact["files"]

    def pack(self, src_dir: str, output: str) -> Path:
        """Create a portable manifest-and-files package artifact."""
        src = Path(src_dir).resolve()
        manifest_path = src / "manifest.json"

        if not src.is_dir() or not manifest_path.is_file():
            raise ValueError("manifest.json is required in the package source directory")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        required = ["name", "version", "type", "author", "description", "license"]

        for req in required:
            if req not in manifest:
                raise ValueError(f"Manifest missing required field: {req}")

        if not isinstance(manifest["type"], str) or manifest["type"] not in PACKAGE_TYPES:
            raise ValueError(f"Manifest type must be one of: {', '.join(sorted(PACKAGE_TYPES))}")

        if not isinstance(manifest.get("name"), str) or not SemVer.is_valid(manifest.get("version")):
            raise ValueError("Package manifest must contain a string name and a valid semantic version")

        encoded_files = {}

        for source_file in src.rglob("*"):
            if source_file == manifest_path or not source_file.is_file():
                continue

            if source_file.is_symlink() or src not in source_file.resolve().parents:
                raise ValueError(f"Package files must not escape the source directory: {source_file}")

            relative_name = source_file.relative_to(src).as_posix()

            try:
                content = source_file.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"Package files must be UTF-8 text: {relative_name}") from exc

            encoded_files[relative_name] = base64.b64encode(content.encode("utf-8")).decode("ascii")

        out_file = Path(output)
        artifact = self._package_artifact(manifest, encoded_files)
        out_file.write_text(json.dumps(artifact, sort_keys=True, indent=2), encoding="utf-8")

        return out_file

    def publish(
        self,
        pkg_file: str,
        access_token: Optional[str] = None,
    ) -> str:
        """Publish a package artifact locally or to the remote registry.

        Remote registries receive ``PUT /packages/{name}/{version}`` with a JSON
        body containing the package ``manifest`` and ``files``.
        """
        manifest, encoded_files = self._read_package_artifact(pkg_file)
        name, version = manifest["name"], manifest["version"]

        if not SemVer.is_valid(version):
            raise ValueError("Package manifest version must be a valid semantic version")

        if self.remote_url:
            if not access_token:
                raise ValueError("Marketplace publishing requires a logged-in publisher account.")
            endpoint = f"{self.remote_url}/packages/{quote(name, safe='')}/{quote(version, safe='')}"

            try:
                response = requests.put(
                    endpoint,
                    json={"manifest": manifest, "files": encoded_files},
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=15,
                    allow_redirects=False,
                )
                response.raise_for_status()
                status_code = getattr(response, "status_code", None)
                if isinstance(status_code, int) and not 200 <= status_code < 300:
                    raise requests.HTTPError("Marketplace returned a non-success status", response=response)
            except requests.HTTPError as exc:
                details = ""
                if exc.response is not None:
                    try:
                        body = exc.response.json()
                        if isinstance(body, dict) and isinstance(body.get("error"), str):
                            details = body["error"]
                    except ValueError:
                        pass
                if details:
                    raise RuntimeError(details) from exc
                raise RuntimeError(
                    f"Marketplace rejected {name}@{version} with HTTP "
                    f"{getattr(exc.response, 'status_code', 'error')}."
                ) from exc
            except requests.RequestException as exc:
                raise RuntimeError(
                    f"Could not reach the marketplace to publish {name}@{version}. Please try again later."
                ) from exc

            return f"Published {name}@{version} to remote marketplace"

        try:
            files = {
                filename: base64.b64decode(content, validate=True).decode("utf-8")
                for filename, content in encoded_files.items()
            }
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError(f"Package artifact contains invalid file data: {exc}") from exc

        self.registry.store_package(name, version, manifest, files)

        return f"Published {name}@{version}"

    # -------------------------
    # Installation
    # -------------------------
    def install(self, name: str, constraint: str = "*") -> Dict[str, Dict[str, str]]:
        """
        Resolve and install dependencies, fetching missing packages from remote if needed.

        Returns:
            Dict[str, Dict[str, str]]: Mapping of package name -> {'version': str,
            'installed_path': str, 'asset_path': str}. ``installed_path`` is
            the local registry cache; ``asset_path`` is the project-local
            directory applications should reference.
        """
        resolver = DependencyResolver(self.registry, ensure_available=self._ensure_available)
        deps = {name: constraint}

        # Resolve versions
        try:
            resolved_versions = resolver.resolve(deps)
        except RuntimeError as e:
            raise RuntimeError(f"Dependency resolution failed: {e}")

        installed_packages: Dict[str, Dict[str, object]] = {}

        for pkg_name, version in resolved_versions.items():
            pkg_manifest = self.registry.get_manifest(pkg_name, version)
            scan_info = None

            # If not present locally, fetch from remote
            if not pkg_manifest:
                if not self.remote_url:
                    raise RuntimeError(f"Package {pkg_name}@{version} not found locally and no remote configured")
                
                self._log(f"Fetching {pkg_name}@{version} from remote...")
                pkg_manifest, pkg_files, scan_info = self._fetch_remote_package(pkg_name, version)
                self.registry.store_package(pkg_name, version, pkg_manifest, pkg_files)
            elif self.remote_url:
                scan_info = self._fetch_remote_scan(name=pkg_name, version=version)

            pkg_path = self.registry.base / pkg_name / version
            asset_path = self._materialize_assets(pkg_path, pkg_manifest)
            installed_packages[pkg_name] = {
                "version": version,
                "installed_path": str(pkg_path),
                "asset_path": str(asset_path),
            }
            if scan_info is not None:
                installed_packages[pkg_name].update(scan_info)

        return installed_packages

    def _materialize_assets(
        self,
        package_path: Path,
        manifest: Dict,
    ) -> Path:
        """Install package files into the project directory for their declared type."""
        package_type = manifest.get("type")

        if not isinstance(package_type, str) or package_type not in PACKAGE_TYPES:
            raise ValueError(f"Package manifest type must be one of: {', '.join(sorted(PACKAGE_TYPES))}")

        package_path = package_path.resolve()

        if self.registry.base not in package_path.parents:
            raise ValueError("Marketplace package path must stay inside the registry")

        target = self.install_dirs[package_type].resolve()
        pending_files = []

        for source in package_path.rglob("*"):
            if source.name == "manifest.json" or not source.is_file():
                continue

            resolved_source = source.resolve()

            if source.is_symlink() or package_path not in resolved_source.parents:
                raise ValueError(f"Marketplace package contains an unsafe file: {source.name}")

            relative = source.relative_to(package_path)
            destination = (target / relative).resolve()

            if target not in destination.parents:
                raise ValueError(f"Marketplace asset path escapes its install directory: {relative}")

            if destination.exists():
                if not destination.is_file() or destination.read_bytes() != resolved_source.read_bytes():
                    raise FileExistsError(
                        f"Package file already exists with different contents: {destination}"
                    )
                continue

            pending_files.append((resolved_source, destination))

        for source, destination in pending_files:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

        return target

    def _ensure_available(self, name: str) -> None:
        """Populate locally missing package versions from the configured remote."""
        if not self.remote_url:
            return

        for version in self._fetch_remote_versions(name):
            if self.registry.get_manifest(name, version):
                continue

            manifest, files, _scan_info = self._fetch_remote_package(name, version)
            self.registry.store_package(name, version, manifest, files)

    # -------------------------
    # Remote fetching
    # -------------------------
    @staticmethod
    def _limited_response(url: str, max_bytes: int) -> bytes:
        """Download an HTTP response with a hard in-memory size limit."""
        response = requests.get(url, timeout=10, stream=True, allow_redirects=False)

        try:
            status_code = getattr(response, "status_code", None)
            if isinstance(status_code, int) and 300 <= status_code < 400:
                raise RuntimeError("Remote marketplace redirects are not allowed")

            response.raise_for_status()
            raw_length = response.headers.get("Content-Length")

            if raw_length is not None and int(raw_length) > max_bytes:
                raise RuntimeError(f"Remote response exceeds the {max_bytes}-byte limit")

            chunks, received = [], 0

            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue

                received += len(chunk)

                if received > max_bytes:
                    raise RuntimeError(f"Remote response exceeds the {max_bytes}-byte limit")

                chunks.append(chunk)

            return b"".join(chunks)
        except ValueError as exc:
            raise RuntimeError("Remote response has an invalid Content-Length") from exc
        finally:
            response.close()

    @staticmethod
    def _decode_json_response(payload: bytes, label: str):
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Remote {label} response is not valid JSON") from exc

    def _fetch_remote_package(
        self,
        name: str,
        version: str,
    ) -> Tuple[Dict, Dict[str, str], Dict[str, object]]:
        """
        Fetch manifest and package files from a remote registry.

        Returns:
            A validated manifest, decoded files, and the registry's clean scan report.
        """
        scan_info = self._fetch_remote_scan(name, version)
        manifest_url = f"{self.remote_url}/packages/{quote(name, safe='')}/{quote(version, safe='')}/manifest"
        files_url = f"{self.remote_url}/packages/{quote(name, safe='')}/{quote(version, safe='')}/files"

        try:
            # Fetch manifest
            manifest = self._decode_json_response(
                self._limited_response(manifest_url, DEFAULT_MAX_MANIFEST_BYTES), "manifest"
            )

            if (
                not isinstance(manifest, dict)
                or manifest.get("name") != name
                or str(manifest.get("version")) != version
                or not SemVer.is_valid(version)
            ):
                raise RuntimeError("Remote manifest name/version does not match the requested package")

            if not isinstance(manifest.get("type"), str) or manifest["type"] not in PACKAGE_TYPES:
                raise RuntimeError(
                    f"Remote package type must be one of: {', '.join(sorted(PACKAGE_TYPES))}"
                )

            # Fetch files
            # Base64 adds at most roughly one third overhead. The response allowance also leaves room for JSON names
            # and punctuation.
            files_data = self._decode_json_response(
                self._limited_response(files_url, self.max_package_bytes * 2), "files"
            )

            # Decode base64 content
            if not isinstance(files_data, dict):
                raise RuntimeError("Remote package files must be an object")

            if not all(isinstance(filename, str) and isinstance(content, str) for filename, content in files_data.items()):
                raise RuntimeError("Remote package files must map string names to base64 strings")

            if len(files_data) > self.max_file_count:
                raise RuntimeError(f"Remote package exceeds the {self.max_file_count}-file limit")

            files, decoded_total = {}, 0

            for fname, content in files_data.items():
                decoded = base64.b64decode(content, validate=True)

                if len(decoded) > self.max_file_bytes:
                    raise RuntimeError(f"Remote package file exceeds the {self.max_file_bytes}-byte limit: {fname}")

                decoded_total += len(decoded)

                if decoded_total > self.max_package_bytes:
                    raise RuntimeError(f"Remote package exceeds the {self.max_package_bytes}-byte decoded-size limit")

                files[fname] = decoded.decode("utf-8")

            return manifest, files, scan_info
        except (requests.RequestException, ValueError, UnicodeDecodeError) as e:
            raise RuntimeError(f"Failed to fetch remote package {name}@{version}: {e}")

    def _fetch_remote_scan(self, name: str, version: str) -> Dict[str, object]:
        scan_url = f"{self.remote_url}/packages/{quote(name, safe='')}/{quote(version, safe='')}/scan"
        try:
            scan_info = self._decode_json_response(
                self._limited_response(scan_url, DEFAULT_MAX_MANIFEST_BYTES),
                "package scan status",
            )
        except (requests.RequestException, ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError(f"Failed to verify the security scan for {name}@{version}: {exc}") from exc

        if (
            not isinstance(scan_info, dict)
            or scan_info.get("scan_status") != "clean"
            or isinstance(scan_info.get("scan_completed_at"), bool)
            or not isinstance(scan_info.get("scan_completed_at"), int)
            or scan_info["scan_completed_at"] <= 0
            or not isinstance(scan_info.get("scan_engine"), str)
            or not isinstance(scan_info.get("scan_findings"), list)
        ):
            raise RuntimeError(f"Package {name}@{version} does not have a valid clean security scan.")

        return scan_info

    def _fetch_remote_versions(self, name: str) -> list[str]:
        try:
            payload = self._decode_json_response(
                self._limited_response(f"{self.remote_url}/packages/{quote(name, safe='')}/versions", DEFAULT_MAX_MANIFEST_BYTES),
                "versions",
            )
            versions = payload.get("versions", []) if isinstance(payload, dict) else payload

            if not isinstance(versions, list) or not all(isinstance(version, str) for version in versions):
                raise RuntimeError("Remote package versions must be a list of strings")

            if not all(SemVer.is_valid(version) for version in versions):
                raise RuntimeError("Remote package versions must be valid semantic versions")

            return versions
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch versions for {name}: {e}")

    # -------------------------
    # Logging helper
    # -------------------------
    def _log(self, msg: str):
        """Optional logging helper for installation steps."""
        logger.info(msg)
