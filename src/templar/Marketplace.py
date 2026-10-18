import sys

from templar.core.marketplace.MarketplaceManager import MarketplaceManager

sys.dont_write_bytecode = True

def run_marketplace_command(action: str, config=None, **kwargs):
    """Run marketplace actions using the active project's configuration."""
    registry_dir = config.get("marketplace_registry_dir", "templar_packages") if config else "templar_packages"
    assets_dir = config.get("marketplace_assets_dir", "static/assets/marketplace") if config else "static/assets/marketplace"
    remote_url = config.get("marketplace_url", None) if config else None
    trusted_fingerprints = config.get("marketplace_trusted_fingerprints", []) if config else []
    mgr = MarketplaceManager(
        registry_dir=registry_dir,
        assets_dir=assets_dir,
        remote_url=remote_url or None,
        trusted_fingerprints=trusted_fingerprints,
    )

    if action == "install":
        result = mgr.install(kwargs["name"], kwargs.get("version", "*"))

        return result

    if action == "pack":
        return mgr.pack(kwargs["src_dir"], kwargs["output"])

    if action == "publish":
        msg = mgr.publish(
            kwargs["pkg_file"],
            kwargs.get("signature_file"),
            kwargs.get("public_key_file"),
        )

        return msg

    if action == "import-key":
        fingerprint = mgr.import_key(kwargs["key_file"])

        if kwargs.get("trust"):
            if config is None:
                raise ValueError("--trust requires a project configuration")

            trusted = config.get("marketplace_trusted_fingerprints", [])

            if not isinstance(trusted, list) or not all(isinstance(value, str) for value in trusted):
                raise ValueError("marketplace_trusted_fingerprints must be a list of fingerprints")

            if fingerprint not in {value.upper() for value in trusted}:
                config.set("marketplace_trusted_fingerprints", [*trusted, fingerprint])

        return fingerprint

    if action == "sign":
        sig = mgr.sign(kwargs["pkg_file"], kwargs.get("keyid"), kwargs.get("passphrase"))

        return sig

    if action == "verify":
        ok, details = mgr.verify(kwargs["pkg_file"], kwargs["sig_file"])

        return ok, details

    raise ValueError(f"Unknown marketplace action: {action}")
