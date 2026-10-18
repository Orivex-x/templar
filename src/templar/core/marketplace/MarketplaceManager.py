import sys, json, requests, base64, logging, re, shutil, tempfile
from pathlib import Path
from typing import Dict, Iterable, Tuple, Optional
from urllib.parse import quote

from templar.core.marketplace.Registry import Registry
from templar.core.marketplace.DependencyResolver import DependencyResolver
from templar.core.marketplace.SemVer import SemVer

sys.dont_write_bytecode = True
logger = logging.getLogger("templar.marketplace")

DEFAULT_MAX_PACKAGE_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_FILE_COUNT = 1_000
DEFAULT_MAX_MANIFEST_BYTES = 256 * 1024
DEFAULT_MAX_SIGNATURE_BYTES = 1024 * 1024

class MarketplaceManager:
    """Unified manager for packaging, publishing, installing, and verifying assets."""

    def __init__(
        self,
        registry_dir: str = "templar_packages",
        assets_dir: str = "static/assets/marketplace",
        remote_url: Optional[str] = None,
        trusted_fingerprints: Optional[Iterable[str]] = None,
        max_package_bytes: int = DEFAULT_MAX_PACKAGE_BYTES,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_file_count: int = DEFAULT_MAX_FILE_COUNT,
    ) -> None:
        self.registry = Registry(registry_dir)
        self.assets_dir = Path(assets_dir).resolve()
        self.gpg = None
        self.remote_url = remote_url  # optional remote API base
        self.trusted_fingerprints = self._normalize_fingerprints(trusted_fingerprints or [])

        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (max_package_bytes, max_file_bytes, max_file_count)):
            raise ValueError("Marketplace package limits must be positive integers")

        if max_file_bytes > max_package_bytes:
            raise ValueError("max_file_bytes cannot exceed max_package_bytes")

        self.max_package_bytes = max_package_bytes
        self.max_file_bytes = max_file_bytes
        self.max_file_count = max_file_count

    @staticmethod
    def _normalize_fingerprints(fingerprints: Iterable[str]) -> set[str]:
        normalized = set()

        for fingerprint in fingerprints:
            if not isinstance(fingerprint, str) or not re.fullmatch(r"(?:[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})", fingerprint):
                raise ValueError("Marketplace trusted fingerprints must be complete 40- or 64-character hexadecimal fingerprints")

            normalized.add(fingerprint.upper())

        return normalized

    def _get_gpg(self):
        if self.gpg is None:
            from templar.core.marketplace.GPGManager import GPGManager
            self.gpg = GPGManager()

        return self.gpg

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
        required = ["name", "version", "author", "description", "license"]

        for req in required:
            if req not in manifest:
                raise ValueError(f"Manifest missing required field: {req}")

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
        signature_file: Optional[str] = None,
        public_key_file: Optional[str] = None,
    ) -> str:
        """Publish locally or upload a signed package artefact to the remote registry.

        Remote registries receive ``PUT /packages/{name}/{version}`` with a JSON
        body containing ``manifest``, ``files``, a base64 detached ``signature``,
        and optional armoured ``public_key``. The signature covers :meth:`remote_signature_payload`.
        """
        manifest, encoded_files = self._read_package_artifact(pkg_file)
        name, version = manifest["name"], manifest["version"]

        if not SemVer.is_valid(version):
            raise ValueError("Package manifest version must be a valid semantic version")

        if self.remote_url:
            signature_path = Path(signature_file) if signature_file else Path(pkg_file).with_suffix(Path(pkg_file).suffix + ".asc")

            try:
                signature = signature_path.read_bytes()
            except OSError as exc:
                raise ValueError(f"A detached package signature is required for remote publishing: {exc}") from exc

            if not signature:
                raise ValueError("A detached package signature is required for remote publishing")

            public_key = None

            if public_key_file:
                try:
                    public_key = Path(public_key_file).read_text(encoding="utf-8")
                except OSError as exc:
                    raise ValueError(f"Could not read public key file: {exc}") from exc

            payload = {
                "manifest": manifest,
                "files": encoded_files,
                "signature": base64.b64encode(signature).decode("ascii"),
            }

            if public_key:
                payload["public_key"] = public_key

            endpoint = f"{self.remote_url}/packages/{quote(name, safe='')}/{quote(version, safe='')}"

            try:
                response = requests.put(endpoint, json=payload, timeout=15)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise RuntimeError(f"Failed to publish {name}@{version} to remote marketplace: {exc}") from exc

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

    def import_key(self, key_file: str) -> str:
        """Import a marketplace signing key and return its full fingerprint."""
        fingerprint = self._get_gpg().import_key(key_file)

        if not fingerprint:
            raise RuntimeError("No public key was imported")

        return fingerprint.upper()

    # -------------------------
    # Installation
    # -------------------------
    def install(self, name: str, constraint: str = "*") -> Dict[str, Dict[str, str]]:
        """
        Resolve and install dependencies, fetching missing packages from remote if needed.

        Returns:
            Dict[str, Dict[str, str]]: Mapping of package name -> {'version': str,
            'installed_path': str, 'asset_path': str}. ``installed_path`` is
            the verified registry cache; ``asset_path`` is the project-local
            directory applications should reference.
        """
        resolver = DependencyResolver(self.registry, ensure_available=self._ensure_available)
        deps = {name: constraint}

        # Resolve versions
        try:
            resolved_versions = resolver.resolve(deps)
        except RuntimeError as e:
            raise RuntimeError(f"Dependency resolution failed: {e}")

        installed_packages: Dict[str, Dict[str, str]] = {}

        for pkg_name, version in resolved_versions.items():
            pkg_manifest = self.registry.get_manifest(pkg_name, version)

            # If not present locally, fetch from remote
            if not pkg_manifest:
                if not self.remote_url:
                    raise RuntimeError(f"Package {pkg_name}@{version} not found locally and no remote configured")
                
                self._log(f"Fetching {pkg_name}@{version} from remote...")
                pkg_manifest, pkg_files = self._fetch_remote_package(pkg_name, version)
                self.registry.store_package(pkg_name, version, pkg_manifest, pkg_files)

            pkg_path = self.registry.base / pkg_name / version
            asset_path = self._materialize_assets(pkg_name, version, pkg_path)
            installed_packages[pkg_name] = {
                "version": version,
                "installed_path": str(pkg_path),
                "asset_path": str(asset_path),
            }

        return installed_packages

    def _materialize_assets(self, name: str, version: str, package_path: Path) -> Path:
        """Atomically expose a verified package below the project's asset root.

        Registry storage remains a private verified cache.  Keeping materialised
        files in ``marketplace_assets_dir/<name>/<version>`` gives templates and
        themes a stable location under the normal static directory without
        granting package file names any path traversal capability.
        """
        name = Registry._component(name, "name")
        version = Registry._component(version, "version")
        package_path = package_path.resolve()

        if self.registry.base not in package_path.parents:
            raise ValueError("Marketplace package path must stay inside the registry")

        target = (self.assets_dir / name / version).resolve()

        if self.assets_dir != target.parent.parent:
            raise ValueError("Marketplace asset path must stay inside the asset directory")

        if target.exists():
            return target

        target.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix=f".{version}.", dir=target.parent))

        try:
            for source in package_path.rglob("*"):
                if source.name == "manifest.json" or not source.is_file():
                    continue

                resolved_source = source.resolve()

                if source.is_symlink() or package_path not in resolved_source.parents:
                    raise ValueError(f"Marketplace package contains an unsafe file: {source.name}")

                relative = source.relative_to(package_path)
                destination = (temp_dir / relative).resolve()

                if temp_dir not in destination.parents:
                    raise ValueError(f"Marketplace asset path escapes its package directory: {relative}")

                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(resolved_source, destination)

            temp_dir.replace(target)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        return target

    def _ensure_available(self, name: str) -> None:
        """Populate locally missing package versions from the configured remote."""
        if not self.remote_url:
            return

        for version in self._fetch_remote_versions(name):
            if self.registry.get_manifest(name, version):
                continue

            manifest, files = self._fetch_remote_package(name, version)
            self.registry.store_package(name, version, manifest, files)

    # -------------------------
    # Remote fetching
    # -------------------------
    @staticmethod
    def remote_signature_payload(manifest: Dict, encoded_files: Dict[str, str]) -> bytes:
        """Return the canonical payload remote registries must sign.

        The detached signature is served from the package's ``/signature``
        endpoint and covers both the manifest and the base64-encoded file map.
        """
        return json.dumps(
            {"files": encoded_files, "manifest": manifest},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def _verify_remote_package(self, manifest: Dict, encoded_files: Dict[str, str], signature: bytes) -> None:
        if not self.trusted_fingerprints:
            raise RuntimeError("Remote installation requires at least one trusted marketplace signing fingerprint")

        valid, details, fingerprint = self._get_gpg().verify_data(
            self.remote_signature_payload(manifest, encoded_files), signature
        )

        if not valid:
            raise RuntimeError(f"Remote package signature is invalid: {details}")

        if fingerprint.upper() not in self.trusted_fingerprints:
            raise RuntimeError(f"Remote package was signed by an untrusted key: {fingerprint or 'unknown'}")

    @staticmethod
    def _limited_response(url: str, max_bytes: int) -> bytes:
        """Download an HTTP response with a hard in-memory size limit."""
        response = requests.get(url, timeout=10, stream=True)

        try:
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

    def _fetch_remote_package(self, name: str, version: str) -> Tuple[Dict, Dict[str, str]]:
        """
        Fetch manifest and package files from a remote registry.

        Returns:
            Tuple[manifest, files]: manifest is dict, files is Dict[filename, content]
        """
        manifest_url = f"{self.remote_url}/packages/{quote(name, safe='')}/{quote(version, safe='')}/manifest"
        files_url = f"{self.remote_url}/packages/{quote(name, safe='')}/{quote(version, safe='')}/files"
        signature_url = f"{self.remote_url}/packages/{quote(name, safe='')}/{quote(version, safe='')}/signature"

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

            signature = self._limited_response(signature_url, DEFAULT_MAX_SIGNATURE_BYTES)

            if not signature:
                raise RuntimeError("Remote package signature is empty")

            self._verify_remote_package(manifest, files_data, signature)
            files, decoded_total = {}, 0

            for fname, content in files_data.items():
                decoded = base64.b64decode(content, validate=True)

                if len(decoded) > self.max_file_bytes:
                    raise RuntimeError(f"Remote package file exceeds the {self.max_file_bytes}-byte limit: {fname}")

                decoded_total += len(decoded)

                if decoded_total > self.max_package_bytes:
                    raise RuntimeError(f"Remote package exceeds the {self.max_package_bytes}-byte decoded-size limit")

                files[fname] = decoded.decode("utf-8")

            return manifest, files
        except (requests.RequestException, ValueError, UnicodeDecodeError) as e:
            raise RuntimeError(f"Failed to fetch remote package {name}@{version}: {e}")

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
    # Signing / Verification
    # -------------------------
    def sign(self, pkg_file: str, keyid: str = None, passphrase: str = None) -> Path:
        manifest, encoded_files = self._read_package_artifact(pkg_file)
        signature_path = Path(pkg_file).with_suffix(Path(pkg_file).suffix + ".asc")

        return self._get_gpg().sign_data(
            self.remote_signature_payload(manifest, encoded_files),
            str(signature_path),
            keyid,
            passphrase,
        )

    def verify(self, pkg_file: str, sig_file: str) -> Tuple[bool, str]:
        manifest, encoded_files = self._read_package_artifact(pkg_file)

        try:
            signature = Path(sig_file).read_bytes()
        except OSError as exc:
            raise ValueError(f"Could not read package signature: {exc}") from exc

        valid, details, _ = self._get_gpg().verify_data(
            self.remote_signature_payload(manifest, encoded_files), signature
        )

        return valid, details

    # -------------------------
    # Logging helper
    # -------------------------
    def _log(self, msg: str):
        """Optional logging helper for installation steps."""
        logger.info(msg)
