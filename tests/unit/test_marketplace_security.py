import pytest

from templar.core.marketplace.DependencyResolver import DependencyResolver
from templar.core.marketplace.GPGManager import GPGManager
from templar.core.marketplace.MarketplaceManager import MarketplaceManager, DEFAULT_MAX_MANIFEST_BYTES
from templar.core.marketplace.Registry import Registry
from templar.core.marketplace.SemVer import SemVer


def manifest(name="demo", version="1.0.0"):
    return {"name": name, "version": version, "author": "test", "description": "test", "license": "MIT"}


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
    )
    packages = {
        "root": manifest("root", "1.0.0") | {"dependencies": {"child": "^1.0.0"}},
        "child": manifest("child", "1.2.0"),
    }

    monkeypatch.setattr(manager, "_fetch_remote_versions", lambda name: [packages[name]["version"]])
    monkeypatch.setattr(
        manager,
        "_fetch_remote_package",
        lambda name, version: (packages[name], {"asset.txt": name}),
    )

    installed = manager.install("root")

    assert installed["root"]["version"] == "1.0.0"
    assert installed["child"]["version"] == "1.2.0"
    assert manager.registry.get_manifest("child", "1.2.0")["name"] == "child"
    assert (tmp_path / "marketplace-assets" / "root" / "1.0.0" / "asset.txt").read_text() == "root"
    assert (tmp_path / "marketplace-assets" / "child" / "1.2.0" / "asset.txt").read_text() == "child"
    assert installed["root"]["asset_path"] == str(tmp_path / "marketplace-assets" / "root" / "1.0.0")


def test_marketplace_assets_are_versioned_and_stay_within_the_configured_root(tmp_path):
    manager = MarketplaceManager(tmp_path / "registry", assets_dir=tmp_path / "assets")
    manager.registry.store_package("demo", "1.0.0", manifest(), {"images/logo.svg": "<svg/>"})

    installed = manager.install("demo")

    assert (tmp_path / "assets" / "demo" / "1.0.0" / "images" / "logo.svg").read_text() == "<svg/>"
    assert installed["demo"]["installed_path"] == str(tmp_path / "registry" / "demo" / "1.0.0")


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


class _SignatureVerifier:
    def __init__(self, fingerprint):
        self.fingerprint = fingerprint
        self.payload = None
        self.signature = None

    def verify_data(self, payload, signature):
        self.payload = payload
        self.signature = signature
        return True, "valid", self.fingerprint


def test_remote_package_requires_a_signature_from_a_trusted_key(tmp_path, monkeypatch):
    fingerprint = "A" * 40
    manager = MarketplaceManager(
        tmp_path / "registry",
        remote_url="https://marketplace.test",
        trusted_fingerprints=[fingerprint],
    )
    verifier = _SignatureVerifier(fingerprint)
    manager.gpg = verifier
    remote_manifest = manifest()
    remote_files = {"asset.txt": "aGVsbG8="}

    def get(url, timeout, stream=False):
        if url.endswith("/manifest"):
            return _RemoteResponse(remote_manifest)

        if url.endswith("/files"):
            return _RemoteResponse(remote_files)

        if url.endswith("/signature"):
            return _RemoteResponse(content=b"detached-signature")

        raise AssertionError(url)

    monkeypatch.setattr("templar.core.marketplace.MarketplaceManager.requests.get", get)
    package_manifest, files = manager._fetch_remote_package("demo", "1.0.0")

    assert package_manifest == remote_manifest
    assert files == {"asset.txt": "hello"}
    assert verifier.signature == b"detached-signature"
    assert verifier.payload == manager.remote_signature_payload(remote_manifest, remote_files)


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


def test_remote_package_rejects_untrusted_or_missing_signatures(tmp_path):
    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")

    with pytest.raises(RuntimeError, match="trusted marketplace signing fingerprint"):
        manager._verify_remote_package(manifest(), {}, b"signature")

    manager = MarketplaceManager(
        tmp_path / "other-registry",
        remote_url="https://marketplace.test",
        trusted_fingerprints=["B" * 40],
    )

    manager.gpg = _SignatureVerifier("A" * 40)

    with pytest.raises(RuntimeError, match="untrusted key"):
        manager._verify_remote_package(manifest(), {}, b"signature")

    with pytest.raises(ValueError, match="complete 40- or 64-character"):
        MarketplaceManager(tmp_path / "short-fingerprint", trusted_fingerprints=["A" * 16])


def test_gpg_verification_uses_the_resolved_package_path(tmp_path):
    class FakeGpg:
        def __init__(self):
            self.data_path = None

        def verify_file(self, signature, data_path):
            self.data_path = data_path
            return type("Result", (), {"valid": True, "__str__": lambda self: "valid"})()

    package = tmp_path / "nested" / "demo.pkg"
    package.parent.mkdir()
    package.write_bytes(b"package")
    signature = tmp_path / "nested" / "demo.pkg.asc"
    signature.write_bytes(b"signature")
    verifier = GPGManager.__new__(GPGManager)
    verifier.gpg = FakeGpg()

    valid, _ = verifier.verify(package, signature)

    assert valid
    assert verifier.gpg.data_path == str(package.resolve())


def test_gpg_data_verification_materializes_only_the_detached_signature():
    class FakeGpg:
        def __init__(self):
            self.signature = None
            self.data = None

        def verify_data(self, signature_path, data):
            from pathlib import Path

            self.signature = Path(signature_path).read_bytes()
            self.data = data

            return type(
                "Result",
                (),
                {"valid": True, "fingerprint": "A" * 40, "__str__": lambda self: "valid"},
            )()

    verifier = GPGManager.__new__(GPGManager)
    verifier.gpg = FakeGpg()

    valid, _, fingerprint = verifier.verify_data(b"signed data", b"signature")

    assert valid
    assert fingerprint == "A" * 40
    assert verifier.gpg.signature == b"signature"
    assert verifier.gpg.data == b"signed data"


def test_package_artifact_pack_publish_and_sign_share_the_remote_payload(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "manifest.json").write_text(__import__("json").dumps(manifest()))
    (source / "templates").mkdir()
    (source / "templates" / "index.txt").write_text("hello")
    manager = MarketplaceManager(tmp_path / "registry")
    artifact_path = manager.pack(source, tmp_path / "demo-package.json")
    artifact_manifest, encoded_files = manager._read_package_artifact(artifact_path)

    class FakeGpg:
        def __init__(self):
            self.data = None

        def sign_data(self, data, output_path, keyid, passphrase):
            self.data = data
            return __import__("pathlib").Path(output_path)

    manager.gpg = FakeGpg()
    signature_path = manager.sign(artifact_path)
    message = manager.publish(artifact_path)

    assert artifact_manifest == manifest()
    assert encoded_files["templates/index.txt"] == "aGVsbG8="
    assert manager.gpg.data == manager.remote_signature_payload(artifact_manifest, encoded_files)
    assert signature_path.name == "demo-package.json.asc"
    assert message == "Published demo@1.0.0"
    assert (tmp_path / "registry" / "demo" / "1.0.0" / "templates" / "index.txt").read_text() == "hello"


def test_remote_publish_uploads_artifact_signature_and_optional_public_key(tmp_path, monkeypatch):
    artifact = tmp_path / "demo.json"
    artifact.write_text(__import__("json").dumps({"manifest": manifest(), "files": {"asset.txt": "aGVsbG8="}}))
    signature = tmp_path / "demo.json.asc"
    signature.write_bytes(b"signature")
    public_key = tmp_path / "publisher.asc"
    public_key.write_text("armored key")
    manager = MarketplaceManager(tmp_path / "registry", remote_url="https://marketplace.test")
    received = {}

    def put(url, json, timeout):
        received.update(url=url, json=json, timeout=timeout)

        return _RemoteResponse()

    monkeypatch.setattr("templar.core.marketplace.MarketplaceManager.requests.put", put)
    result = manager.publish(artifact, signature, public_key)

    assert result == "Published demo@1.0.0 to remote marketplace"
    assert received["url"] == "https://marketplace.test/packages/demo/1.0.0"
    assert received["json"]["manifest"] == manifest()
    assert received["json"]["files"] == {"asset.txt": "aGVsbG8="}
    assert received["json"]["signature"] == "c2lnbmF0dXJl"
    assert received["json"]["public_key"] == "armored key"


def test_marketplace_key_import_returns_a_full_fingerprint(tmp_path):
    class FakeGpg:
        def import_key(self, key_file):
            assert key_file == "marketplace.asc"
            return "a" * 40

    manager = MarketplaceManager(tmp_path / "registry")
    manager.gpg = FakeGpg()

    assert manager.import_key("marketplace.asc") == "A" * 40


def test_marketplace_key_import_can_persist_trust(tmp_path):
    from types import SimpleNamespace
    from templar.Marketplace import run_marketplace_command

    class Config:
        def __init__(self):
            self.values = {"marketplace_registry_dir": str(tmp_path / "registry"), "marketplace_trusted_fingerprints": []}

        def get(self, key, default=None):
            return self.values.get(key, default)

        def set(self, key, value):
            self.values[key] = value

    config = Config()

    # Exercise config persistence without invoking a real GPG binary.
    from unittest.mock import patch

    with patch("templar.Marketplace.MarketplaceManager.import_key", return_value="A" * 40):
        fingerprint = run_marketplace_command("import-key", config=config, key_file="marketplace.asc", trust=True)

    assert fingerprint == "A" * 40
    assert config.values["marketplace_trusted_fingerprints"] == ["A" * 40]


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
        lambda url, timeout, stream=False: _RemoteResponse({"versions": ["1.bad"]}),
    )

    with pytest.raises(RuntimeError, match="valid semantic versions"):
        manager._fetch_remote_versions("demo")
