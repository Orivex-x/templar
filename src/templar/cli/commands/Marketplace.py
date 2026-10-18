import sys
from templar.cli.BaseCommand import BaseCommand

sys.dont_write_bytecode = True

class MarketplacePackCommand(BaseCommand):
    name = "marketplace-pack"
    help = "Build a signed-marketplace package artifact"

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

        self._run("install", name=args.name, version=args.version)

class MarketplacePublishCommand(BaseCommand):
    name = "marketplace-publish"
    help = "Publish a package to the marketplace"

    @staticmethod
    def add_args(parser) -> None:
        parser.add_argument("pkg_file")
        parser.add_argument("--signature-file", help="Detached signature (defaults to <pkg_file>.asc)")
        parser.add_argument("--public-key-file", help="Optional armored public key to upload")

    def run(self, args, extra_args=None) -> None:
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Marketplace Error")
            sys.exit(1)

        self._run(
            "publish",
            pkg_file=args.pkg_file,
            signature_file=args.signature_file,
            public_key_file=args.public_key_file,
        )


class MarketplaceImportKeyCommand(BaseCommand):
    name = "marketplace-import-key"
    help = "Import a marketplace signing public key"

    @staticmethod
    def add_args(parser) -> None:
        parser.add_argument("key_file")
        parser.add_argument("--trust", action="store_true", help="Add the imported fingerprint to the active project config")

    def run(self, args, extra_args=None) -> None:
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Marketplace Error")
            sys.exit(1)

        self._run("import-key", key_file=args.key_file, trust=args.trust)

class MarketplaceSignCommand(BaseCommand):
    name = "marketplace-sign"
    help = "Sign a package"

    @staticmethod
    def add_args(parser) -> None:
        parser.add_argument("pkg_file")
        parser.add_argument("--keyid")
        parser.add_argument("--passphrase")

    def run(self, args, extra_args=None) -> None:
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Marketplace Error")
            sys.exit(1)

        self._run(
            "sign",
            pkg_file=args.pkg_file,
            keyid=args.keyid,
            passphrase=args.passphrase,
        )

class MarketplaceVerifyCommand(BaseCommand):
    name = "marketplace-verify"
    help = "Verify a package signature"

    @staticmethod
    def add_args(parser) -> None:
        parser.add_argument("pkg_file")
        parser.add_argument("sig_file")

    def run(self, args, extra_args=None) -> None:
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Marketplace Error")
            sys.exit(1)

        self._run(
            "verify",
            pkg_file=args.pkg_file,
            sig_file=args.sig_file,
        )
