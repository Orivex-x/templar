import sys, gnupg, tempfile
from pathlib import Path
from typing import Optional, Tuple

sys.dont_write_bytecode = True

class GPGManager:
    """Handles signing and verifying packages with GPG."""

    def __init__(self, home: Optional[str] = None) -> None:
        self.gpg = gnupg.GPG(gnupghome=home)

    def import_key(self, key_file: str) -> str:
        data = Path(key_file).read_text()
        result = self.gpg.import_keys(data)

        return result.fingerprints[0] if result.fingerprints else None

    def sign(self, package_path: str, keyid: Optional[str] = None, passphrase: Optional[str] = None) -> Path:
        pkg = Path(package_path).resolve()
        sig_path = pkg.with_suffix(pkg.suffix + ".asc")

        with pkg.open("rb") as f:
            signed = self.gpg.sign_file(f, keyid=keyid, passphrase=passphrase, detach=True, output=str(sig_path))

            if not signed:
                raise RuntimeError("Failed to sign package")

        return sig_path

    def sign_data(
        self,
        data: bytes,
        output_path: str,
        keyid: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> Path:
        """Create a detached signature for in-memory package payload data."""
        signature_path = Path(output_path).resolve()

        with tempfile.NamedTemporaryFile() as data_file:
            data_file.write(data)
            data_file.flush()
            signed = self.gpg.sign_file(
                data_file,
                keyid=keyid,
                passphrase=passphrase,
                detach=True,
                output=str(signature_path),
            )

        if not signed:
            raise RuntimeError("Failed to sign package payload")

        return signature_path

    def verify(self, package_path: str, sig_path: str) -> Tuple[bool, str]:
        package = Path(package_path).resolve()
        signature = Path(sig_path).resolve()

        with signature.open("rb") as sig:
            verified = self.gpg.verify_file(sig, str(package))

            return verified.valid, str(verified)

    def verify_data(self, data: bytes, signature: bytes) -> Tuple[bool, str, str]:
        """Verify detached signature bytes and return its signing fingerprint."""
        # python-gnupg's verify_data accepts a signature *path* plus in-memory data, so materialize only the detached
        # signature in a temporary file.
        with tempfile.NamedTemporaryFile(suffix=".asc") as signature_file:
            signature_file.write(signature)
            signature_file.flush()
            verified = self.gpg.verify_data(signature_file.name, data)

        fingerprint = str(getattr(verified, "fingerprint", "") or "")

        return bool(verified.valid), str(verified), fingerprint
