import getpass
import os
import sys
from urllib.parse import urlparse

import requests
from templar.cli.BaseCommand import BaseCommand

sys.dont_write_bytecode = True

MARKETPLACE_API_URL = os.environ.get(
    "TEMPLAR_MARKETPLACE_API_URL",
    "http://127.0.0.1:8080/api",
).rstrip("/")


def _is_loopback_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def _require_secure_registry(url: str) -> None:
    if urlparse(url).scheme != "https" and not _is_loopback_url(url):
        raise ValueError("Marketplace credentials and packages require HTTPS outside localhost.")


class MarketplacePackCommand(BaseCommand):
    name = "marketplace-pack"
    help = "Build a marketplace package artifact"

    @staticmethod
    def add_args(parser) -> None:
        parser.add_argument("src_dir")
        parser.add_argument("output")

    def run(self, args, extra_args=None) -> None:
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Marketplace Error")
            sys.exit(1)

        self._run("pack", src_dir=args.src_dir, output=args.output)

class MarketplaceInstallCommand(BaseCommand):
    name = "marketplace-install"
    help = "Install a package from the marketplace"

    @staticmethod
    def add_args(parser) -> None:
        parser.add_argument("name")
        parser.add_argument("--version", default="*")

    def run(self, args, extra_args=None) -> None:
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Marketplace Error")
            sys.exit(1)

        self._run(
            "install",
            name=args.name,
            version=args.version,
            remote_url=MARKETPLACE_API_URL,
        )

class MarketplacePublishCommand(BaseCommand):
    name = "marketplace-publish"
    help = "Publish a package to the marketplace"

    @staticmethod
    def add_args(parser) -> None:
        parser.add_argument("pkg_file")
        parser.add_argument("--username", help="Marketplace account username or email")

    def run(self, args, extra_args=None) -> None:
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Marketplace Error")
            sys.exit(1)

        try:
            _require_secure_registry(MARKETPLACE_API_URL)
            username = getattr(args, "username", None) or input("Marketplace username or email: ").strip()
            if not username:
                raise ValueError("A marketplace username or email is required.")

            password = getpass.getpass("Marketplace password: ")
            if not password:
                raise ValueError("A marketplace password is required.")

            response = requests.post(
                f"{MARKETPLACE_API_URL}/login",
                json={"username_or_email": username, "password": password},
                timeout=15,
                allow_redirects=False,
            )
            response.raise_for_status()
            login = response.json()
            data = login.get("Data") if isinstance(login, dict) and login.get("Status") else None
            token = data.get("access_token") if isinstance(data, dict) else None
            if not token:
                raise RuntimeError("Marketplace login response did not contain an access token.")

            self._run(
                "publish",
                pkg_file=args.pkg_file,
                access_token=token,
                remote_url=MARKETPLACE_API_URL,
            )
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            self.output.error(str(exc), title="Marketplace Error")
            sys.exit(2)
