"""Install shell completion files for the Templar CLI."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from templar.cli.BaseCommand import BaseCommand


class CompletionCommand(BaseCommand):
    """Generate and install Argcomplete integration for the current user."""

    name = "install-completion"
    help = "Install shell completion for templar"

    @staticmethod
    def add_args(parser):
        parser.add_argument(
            "--shell",
            choices=("auto", "bash", "zsh", "fish", "powershell"),
            default="auto",
            help="Shell to configure (default: detect the current platform/shell)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show the completion file path without writing it",
        )

    @staticmethod
    def _detect_shell() -> str:
        if os.name == "nt":
            return "powershell"

        shell = Path(os.environ.get("SHELL", "bash")).name.lower()

        return shell if shell in {"bash", "zsh", "fish"} else "bash"

    @staticmethod
    def _completion_path(shell: str) -> Path:
        home = Path.home()

        if shell == "bash":
            data_home = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))

            return data_home / "bash-completion" / "completions" / "templar"

        if shell == "zsh":
            return home / ".zsh" / "completions" / "_templar"

        if shell == "fish":
            return Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "fish" / "completions" / "templar.fish"

        if os.name == "nt":
            app_data = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))

            return app_data / "Templar" / "completions" / "templar.ps1"

        config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))

        return config_home / "templar" / "completions" / "templar.ps1"

    @staticmethod
    def _generator() -> str | None:
        local_generator = Path(sys.executable).with_name("register-python-argcomplete")

        if local_generator.is_file():
            return str(local_generator)

        return shutil.which("register-python-argcomplete")

    def _generate_script(self, shell: str) -> str:
        generator = self._generator()

        if not generator:
            raise RuntimeError(
                "Argcomplete's completion generator was not found. "
                "Reinstall Templar with `python -m pip install -e \".[dev]\"`."
            )

        completed = subprocess.run(
            [generator, "--shell", shell, "templar"],
            check=True,
            capture_output=True,
            text=True,
        )

        if not completed.stdout.strip():
            raise RuntimeError("Argcomplete did not generate a completion script.")

        return completed.stdout

    @staticmethod
    def _configure_zsh() -> None:
        """Ensure zsh searches the user-owned completion directory, once."""
        zshrc = Path.home() / ".zshrc"
        begin = "# >>> templar completion >>>"
        end = "# <<< templar completion <<<"

        if zshrc.exists() and begin in zshrc.read_text(encoding="utf-8"):
            return

        block = (
            f"\n{begin}\n"
            "fpath=(\"$HOME/.zsh/completions\" $fpath)\n"
            "autoload -Uz compinit && compinit\n"
            f"{end}\n"
        )

        with zshrc.open("a", encoding="utf-8") as file:
            file.write(block)

    @staticmethod
    def _powershell_executables() -> list[str]:
        """Return each installed PowerShell implementation without duplicates."""
        executables = []

        for name in ("pwsh", "powershell"):
            executable = shutil.which(name)

            if executable and executable not in executables:
                executables.append(executable)

        return executables

    def _configure_powershell(self, completion_file: Path) -> None:
        """Source the generated completion file from the current-user profile."""
        executables = self._powershell_executables()

        if not executables:
            raise RuntimeError(
                "PowerShell was not found. Install PowerShell and rerun "
                "`templar install-completion --shell powershell`."
            )

        begin = "# >>> templar completion >>>"
        end = "# <<< templar completion <<<"
        completion_path = str(completion_file).replace("'", "''")

        for powershell in executables:
            profile_result = subprocess.run(
                [powershell, "-NoProfile", "-Command", "$PROFILE.CurrentUserAllHosts"],
                check=True,
                capture_output=True,
                text=True,
            )

            profile = Path(profile_result.stdout.strip())

            if not profile.name:
                raise RuntimeError("Could not determine the current-user PowerShell profile.")

            existing = profile.read_text(encoding="utf-8") if profile.exists() else ""

            if begin in existing:
                continue

            profile.parent.mkdir(parents=True, exist_ok=True)

            with profile.open("a", encoding="utf-8") as file:
                file.write(f"\n{begin}\n& '{completion_path}'\n{end}\n")

    def run(self, args, extra_args=None):
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Completion Error")
            sys.exit(1)

        shell = self._detect_shell() if args.shell == "auto" else args.shell
        destination = self._completion_path(shell)

        if args.dry_run:
            self.output.info(
                f"Would install {shell} completion at:\n{destination}",
                title="Templar Completion",
            )

            return

        try:
            completion = self._generate_script(shell)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(completion, encoding="utf-8")

            if shell == "zsh":
                self._configure_zsh()
            elif shell == "powershell":
                self._configure_powershell(destination)
        except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
            self.output.error(str(error), title="Completion Error")
            sys.exit(2)

        reload_note = "Open a new terminal to enable completion."
        self.output.success(
            f"Installed {shell} completion at:\n{destination}\n\n{reload_note}",
            title="Templar Completion Installed",
        )
