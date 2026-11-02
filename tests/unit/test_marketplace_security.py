import pytest
import requests

from templar.core.marketplace.DependencyResolver import DependencyResolver
from templar.core.marketplace.MarketplaceManager import MarketplaceManager, DEFAULT_MAX_MANIFEST_BYTES
from templar.core.marketplace.Registry import Registry
from templar.core.marketplace.SemVer import SemVer


def manifest(name="demo", version="1.0.0"):
    return {
        "name": name,
        "version": version,
        "type": "component",
        "author": "test",
        "description": "test",
        "license": "MIT",
    }


def test_registry_rejects_path_traversal_and_manifest_mismatches(tmp_path):
    registry = Registry(tmp_path / "registry")

    with pytest.raises(ValueError):
        registry.store_package("../escape", "1.0.0", manifest(), {})

    with pytest.raises(ValueError):
        registry.store_package("demo", "1.0.0", manifest("other"), {})

    with pytest.raises(ValueError):
        registry.store_package("demo", "1.0.0", manifest(), {"../../escape": "bad"})

    with pytest.raises(ValueError, match="file name must be a string"):
        registry.store_package("demo", "1.0.0", manifest(), {1: "bad"})

    assert not (tmp_path / "registry" / "demo" / "1.0.0").exists()


def test_registry_allows_nested_files_inside_the_package(tmp_path):
    registry = Registry(tmp_path / "registry")
    registry.store_package("demo", "1.0.0", manifest(), {"templates/index.txt": "ok"})

    assert (tmp_path / "registry" / "demo" / "1.0.0" / "templates" / "index.txt").read_text() == "ok"


def test_marketplace_fetches_missing_transitive_dependencies(tmp_path, monkeypatch):
    manager = MarketplaceManager(
        tmp_path / "registry",
        assets_dir=tmp_path / "marketplace-assets",
        remote_url="https://marketplace.test",
        install_dirs={
            "component": str(tmp_path / "components"),
            "utility": str(tmp_path / "utilities"),
        },
    )
    packages = {
        "root": manifest("root", "1.0.0") | {"dependencies": {"child": "^1.0.0"}},
        "child": manifest("child", "1.2.0") | {"type": "utility"},
    }

    monkeypatch.setattr(manager, "_fetch_remote_versions", lambda name: [packages[name]["version"]])
    monkeypatch.setattr(
        manager,
        "_fetch_remote_scan",
        lambda name, version: {
            "scan_status": "clean",
            "scan_completed_at": 1_798_000_000,
            "scan_engine": "ClamAV test",
            "scan_findings": [],
        },
    )
    monkeypatch.setattr(
        manager,
        "_fetch_remote_package",
        lambda name, version: (
            packages[name],
            {"asset.txt": name},
            {
                "scan_status": "clean",
                "scan_completed_at": 1_798_000_000,
                "scan_engine": "ClamAV test",
                "scan_findings": [],
            },
        ),
    )

    installed = manager.install("root")

    assert installed["root"]["version"] == "1.0.0"
    assert installed["root"]["scan_status"] == "clean"
    assert installed["root"]["scan_completed_at"] == 1_798_000_000
    assert installed["child"]["version"] == "1.2.0"
    assert manager.registry.get_manifest("child", "1.2.0")["name"] == "child"
    assert (tmp_path / "components" / "asset.txt").read_text() == "root"
    assert (tmp_path / "utilities" / "asset.txt").read_text() == "child"
    assert installed["root"]["asset_path"] == str(tmp_path / "components")


def test_marketplace_installs_files_into_the_type_specific_project_directory(tmp_path):
    manager = MarketplaceManager(
        tmp_path / "registry",
        assets_dir=tmp_path / "assets",
        install_dirs={"component": str(tmp_path / "components")},
    )
    manager.registry.store_package("demo", "1.0.0", manifest(), {"images/logo.svg": "<svg/>"})

    installed = manager.install("demo")

    assert (tmp_path / "components" / "images" / "logo.svg").read_text() == "<svg/>"
    assert installed["demo"]["installed_path"] == str(tmp_path / "registry" / "demo" / "1.0.0")


@pytest.mark.parametrize(
    ("package_type", "directory"),
    [
        ("template", "templates"),
        ("utility", "utilities"),
        ("theme", "themes"),
        ("component", "components"),
    ],
)
def test_marketplace_install_routes_each_package_type_to_its_project_directory(
    tmp_path, package_type, directory
):
    destinations = {
        package_type: str(tmp_path / directory)
        for package_type, directory in [
            ("template", "templates"),
            ("utility", "utilities"),
            ("theme", "themes"),
            ("component", "components"),
        ]
    }
    manager = MarketplaceManager(tmp_path / "registry", install_dirs=destinations)
    pkg_manifest = manifest() | {"type": package_type}
    manager.registry.store_package("demo", "1.0.0", pkg_manifest, {"entry.py": "pass"})

    manager.install("demo")

    assert (tmp_path / directory / "entry.py").read_text() == "pass"


def test_marketplace_command_uses_configured_type_directories(tmp_path, monkeypatch):
    from templar.Marketplace import run_marketplace_command

    project_paths = {
        "project_root": tmp_path,
        "templates_dir": tmp_path / "custom-templates",
        "themes_dir": tmp_path / "custom-themes",
        "components_dir": tmp_path / "custom-components",
        "utilities_dir": tmp_path / "custom-utilities",
    }

    class Config:
        def get(self, key, default=None):
            return project_paths.get(key, default)

    captured = {}

    class FakeManager:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def install(self, name, version):
            return name, version

    monkeypatch.setattr("templar.Marketplace.MarketplaceManager", FakeManager)
    result = run_marketplace_command("install", config=Config(), name="demo", version="1.0.0")

    assert result == ("demo", "1.0.0")
    assert captured["install_dirs"] == {
        "template": project_paths["templates_dir"],
        "theme": project_paths["themes_dir"],
        "component": project_paths["components_dir"],
        "utility": project_paths["utilities_dir"],
    }


def test_package_manifest_requires_a_supported_type(tmp_path):
    source = tmp_path / "package"
    source.mkdir()
    (source / "manifest.json").write_text(
        __import__("json").dumps(manifest() | {"type": "unknown"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Manifest type"):
        MarketplaceManager(tmp_path / "registry").pack(source, tmp_path / "package.json")


class _RemoteResponse:
    def __init__(self, payload=None, content=b""):
        self._payload = payload
        self.content = content or __import__("json").dumps(payload).encode("utf-8")
        self.headers = {"Content-Length": str(len(self.content))}

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield from (self.content[index:index + chunk_size] for index in range(0, len(self.content), chunk_size))

    def close(self):
        return None


def test_remote_package_installs_without_signing_or_key_setup(tmp_path, monkeypatch):
    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")
    remote_manifest = manifest()
    remote_files = {"asset.txt": "aGVsbG8="}
    requested_urls = []
    redirect_settings = []

    def get(url, timeout, stream=False, allow_redirects=True):
        requested_urls.append(url)
        redirect_settings.append(allow_redirects)
        if url.endswith("/scan"):
            return _RemoteResponse({
                "scan_status": "clean",
                "scan_completed_at": 1_798_000_000,
                "scan_engine": "ClamAV 1.4.2/28057",
                "scan_findings": [],
            })

        if url.endswith("/manifest"):
            return _RemoteResponse(remote_manifest)

        if url.endswith("/files"):
            return _RemoteResponse(remote_files)

        raise AssertionError(url)

    monkeypatch.setattr("templar.core.marketplace.MarketplaceManager.requests.get", get)
    package_manifest, files, scan_info = manager._fetch_remote_package("demo", "1.0.0")

    assert package_manifest == remote_manifest
    assert files == {"asset.txt": "hello"}
    assert scan_info["scan_status"] == "clean"
    assert requested_urls == [
        "https://marketplace.test/packages/demo/1.0.0/scan",
        "https://marketplace.test/packages/demo/1.0.0/manifest",
        "https://marketplace.test/packages/demo/1.0.0/files",
    ]
    assert redirect_settings == [False, False, False]


def test_remote_package_rejects_redirect_responses(tmp_path, monkeypatch):
    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")

    class RedirectResponse:
        status_code = 302
        headers = {}

        def raise_for_status(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        "templar.core.marketplace.MarketplaceManager.requests.get",
        lambda *args, **kwargs: RedirectResponse(),
    )

    with pytest.raises(RuntimeError, match="redirects are not allowed"):
        manager._fetch_remote_package("demo", "1.0.0")


def test_remote_package_rejects_missing_or_non_clean_scan_status(tmp_path, monkeypatch):
    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")
    monkeypatch.setattr(
        "templar.core.marketplace.MarketplaceManager.requests.get",
        lambda *args, **kwargs: _RemoteResponse({"scan_status": "pending"}),
    )

    with pytest.raises(RuntimeError, match="does not have a valid clean security scan"):
        manager._fetch_remote_package("demo", "1.0.0")


def test_remote_package_rejects_oversized_responses_before_json_parsing(tmp_path, monkeypatch):
    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")

    class OversizedResponse:
        headers = {"Content-Length": str(DEFAULT_MAX_MANIFEST_BYTES + 1)}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            raise AssertionError("body must not be read after oversized Content-Length")

        def close(self):
            return None

    monkeypatch.setattr("templar.core.marketplace.MarketplaceManager.requests.get", lambda *args, **kwargs: OversizedResponse())

    with pytest.raises(RuntimeError, match="exceeds"):
        manager._fetch_remote_package("demo", "1.0.0")


def test_package_artifact_pack_and_publish_needs_no_signing_key(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "manifest.json").write_text(__import__("json").dumps(manifest()))
    (source / "templates").mkdir()
    (source / "templates" / "index.txt").write_text("hello")
    manager = MarketplaceManager(tmp_path / "registry")
    artifact_path = manager.pack(source, tmp_path / "demo-package.json")
    message = manager.publish(artifact_path)

    assert message == "Published demo@1.0.0"
    assert (tmp_path / "registry" / "demo" / "1.0.0" / "templates" / "index.txt").read_text() == "hello"


def test_remote_publish_uploads_authenticated_manifest_and_files(tmp_path, monkeypatch):
    artifact = tmp_path / "demo.json"
    artifact.write_text(__import__("json").dumps({"manifest": manifest(), "files": {"asset.txt": "aGVsbG8="}}))
    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")
    received = {}

    def put(url, json, headers, timeout, allow_redirects):
        received.update(url=url, json=json, headers=headers, timeout=timeout, allow_redirects=allow_redirects)

        return _RemoteResponse()

    monkeypatch.setattr("templar.core.marketplace.MarketplaceManager.requests.put", put)
    result = manager.publish(artifact, "temporary-token")

    assert result == "Published demo@1.0.0 to remote marketplace"
    assert received["url"] == "https://marketplace.test/packages/demo/1.0.0"
    assert received["headers"] == {"Authorization": "Bearer temporary-token"}
    assert received["json"]["manifest"] == manifest()
    assert received["json"]["files"] == {"asset.txt": "aGVsbG8="}
    assert set(received["json"]) == {"manifest", "files"}
    assert received["allow_redirects"] is False


def test_remote_marketplace_rejects_plain_http_outside_loopback(tmp_path):
    with pytest.raises(ValueError, match="require HTTPS"):
        MarketplaceManager(tmp_path / "registry", remote_url="http://marketplace.example/api")


def test_remote_publish_requires_a_publisher_access_token(tmp_path):
    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")
    artifact = tmp_path / "demo.json"
    artifact.write_text(__import__("json").dumps({"manifest": manifest(), "files": {"asset.txt": "aGVsbG8="}}))

    with pytest.raises(ValueError, match="logged-in publisher"):
        manager.publish(artifact)


def test_remote_publish_surfaces_retryable_scanner_errors(tmp_path, monkeypatch):
    artifact = tmp_path / "demo.json"
    artifact.write_text(__import__("json").dumps({"manifest": manifest(), "files": {"asset.txt": "aGVsbG8="}}))
    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")

    class ScannerUnavailableResponse:
        status_code = 503

        def raise_for_status(self):
            raise requests.HTTPError("503 Service Unavailable", response=self)

        def json(self):
            return {
                "error": "Package scanning is temporarily unavailable. Please try publishing again later."
            }

    monkeypatch.setattr(
        "templar.core.marketplace.MarketplaceManager.requests.put",
        lambda *args, **kwargs: ScannerUnavailableResponse(),
    )

    with pytest.raises(RuntimeError, match="Please try publishing again later"):
        manager.publish(artifact, "test-access-token")


def test_dependency_resolver_backtracks_to_a_compatible_version(tmp_path):
    registry = Registry(tmp_path / "registry")
    registry.store_package("root", "1.0.0", manifest("root") | {"dependencies": {"library": ">=1.0.0", "plugin": "*"}}, {})
    registry.store_package("library", "1.0.0", manifest("library"), {})
    registry.store_package("library", "2.0.0", manifest("library", "2.0.0"), {})
    registry.store_package("plugin", "1.0.0", manifest("plugin") | {"dependencies": {"library": "<2.0.0"}}, {})

    resolved = DependencyResolver(registry).resolve({"root": "*"})

    assert resolved == {"root": "1.0.0", "plugin": "1.0.0", "library": "1.0.0"}


def test_semver_and_remote_version_validation_are_controlled(tmp_path, monkeypatch):
    assert not SemVer.is_valid("1")
    assert not SemVer.is_valid("1.0")
    assert not SemVer.is_valid("1.bad")
    assert not SemVer.is_valid("1.0.0-01")

    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")

    monkeypatch.setattr(
        "templar.core.marketplace.MarketplaceManager.requests.get",
        lambda url, timeout, stream=False, allow_redirects=True: _RemoteResponse({"versions": ["1.bad"]}),
    )

    with pytest.raises(RuntimeError, match="valid semantic versions"):
        manager._fetch_remote_versions("demo")
