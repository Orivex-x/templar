from pathlib import Path
import sys

from templar.core.marketplace.MarketplaceManager import MarketplaceManager

sys.dont_write_bytecode = True

def run_marketplace_command(action: str, config=None, **kwargs):
    """Run marketplace actions using the active project's configuration."""
    registry_dir = config.get("marketplace_registry_dir", "templar_packages") if config else "templar_packages"
    remote_url = kwargs.get("remote_url")
    project_root = Path(config.get("project_root", Path.cwd())) if config else Path.cwd()
    install_dirs = {
        "template": config.get("templates_dir", project_root / "templates") if config else project_root / "templates",
        "theme": config.get("themes_dir", project_root / "themes") if config else project_root / "themes",
        "component": config.get("components_dir", project_root / "components") if config else project_root / "components",
        "utility": config.get("utilities_dir", project_root / "utilities") if config else project_root / "utilities",
    }
    mgr = MarketplaceManager(
        registry_dir=registry_dir,
        remote_url=remote_url or None,
        install_dirs=install_dirs,
    )

    if action == "install":
        result = mgr.install(kwargs["name"], kwargs.get("version", "*"))

        return result

    if action == "pack":
        return mgr.pack(kwargs["src_dir"], kwargs["output"])

    if action == "publish":
        msg = mgr.publish(kwargs["pkg_file"], kwargs.get("access_token"))

        return msg

    raise ValueError(f"Unknown marketplace action: {action}")
