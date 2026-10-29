import sys
from typing import Any

import yaml
from rich.text import Text
from rich.columns import Columns

from templar.cli.BaseCommand import BaseCommand

sys.dont_write_bytecode = True


class ConfigCommand(BaseCommand):
    name = "config"
    help = "Show or modify configuration"

    _SENSITIVE_CONFIG_TERMS = (
        "secret",
        "password",
        "token",
        "credential",
        "api_key",
        "private_key",
        "db_uri",
        "redis_url",
    )

    @staticmethod
    def add_args(parser):
        parser.add_argument(
            "action",
            nargs="?",
            default="show",
            help="Action: show | activate | set",
        )
        parser.add_argument("env", nargs="?")
        parser.add_argument("key", nargs="?")
        parser.add_argument("value", nargs="?")
        parser.add_argument(
            "--env",
            dest="target_env",
            choices=("dev", "prod", "active"),
            help="Target environment for 'set'",
        )
        parser.add_argument(
            "--show-secrets",
            action="store_true",
            help="Show resolved sensitive values when displaying configuration",
        )

    # -----------------------------
    # Helpers
    # -----------------------------
    @staticmethod
    def _get_arg(args, name: str, default=None):
        if args is None or isinstance(args, (list, tuple)):
            return default

        return getattr(args, name, default)

    def _get_env_config(self, env: str) -> dict:
        if env == "active":
            return self.cli.config.get_active_config()

        return self.cli.config.get_all().get(env, {})

    def _parse_set_args(self, args):
        """
        Supported forms:
          templar config set dev theme dark
          templar config set dev:theme dark
          templar config set theme:dark
        """
        env = self._get_arg(args, "target_env") or self._get_arg(args, "env")
        key = self._get_arg(args, "key")
        value = self._get_arg(args, "value")

        target_env = self._get_arg(args, "target_env")
        positional_env = self._get_arg(args, "env")

        if target_env and value is None and positional_env and key:
            env, key, value = target_env, positional_env, key

        # Natural active-environment form: templar config set theme dark
        if target_env is None and value is None and env and key and ":" not in env:
            env, key, value = "active", env, key

        # env may be "dev:key" or "key:value"
        if env and ":" in env:
            left, right = env.split(":", 1)

            if left in ("dev", "prod"):
                env = left
                key = right
            else:
                env = "active"
                key = left
                value = right

        # key may be "key:value"
        if key and ":" in key:
            key, value = key.split(":", 1)

        if not env:
            env = "active"

        if not key or value is None:
            self.output.error("You must specify both a key and a value for 'set'")
            sys.exit(1)

        return env, key.strip(), value.strip()

    @classmethod
    def _display_value(
        cls,
        key: str,
        value: Any,
        *,
        show_secrets: bool,
    ) -> Any:
        normalized = key.lower()

        if not show_secrets and any(term in normalized for term in cls._SENSITIVE_CONFIG_TERMS):
            return "[redacted]"

        return value

    def _get_config_rows(
        self,
        *,
        active_only: bool = False,
        show_secrets: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return configuration as plain Python data.

        Each row contains:
          environment: configuration environment
          key: configuration key
          value: resolved value, with sensitive values redacted by default
        """
        if active_only:
            configurations = {
                "active": self.cli.config.get_active_config()
            }
        else:
            configurations = self.cli.config.get_all()

        rows: list[dict[str, Any]] = []

        for environment, section in configurations.items():
            if not isinstance(section, dict):
                continue

            for key, value in section.items():
                rows.append({
                    "environment": environment,
                    "key": key,
                    "value": self._display_value(key, value, show_secrets=show_secrets),
                })

        return rows

    @staticmethod
    def _format_cli_rows(rows: list[dict[str, Any]]) -> list[tuple[str, Text]]:
        formatted_rows = []

        for row in rows:
            value = row["value"]

            if isinstance(value, bool):
                value_text = Text(
                    "yes" if value else "no",
                    style="bold green" if value else "bold red",
                )
            else:
                value_text = Text(str(value), style="green")

            key_text = Text(str(row["key"]), style="magenta")

            formatted_rows.append((key_text, value_text))

        return formatted_rows

    def _render_config_section(
        self,
        title: str,
        rows: list[dict[str, Any]],
    ) -> Text:
        text = Text()
        text.append(f"{title}\n", style="bold cyan underline")

        for key_text, value_text in self._format_cli_rows(rows):
            text.append_text(key_text)
            text.append(": ")
            text.append_text(value_text)
            text.append("\n")

        return text

    def run(
        self,
        args,
        extra_args=None,
        *,
        return_rows: bool = False,
    ) -> list[dict[str, Any]] | None:
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}")
            sys.exit(1)

        action = (self._get_arg(args, "action", "show") or "show").lower()

        if action == "show":
            show_secrets = self._get_arg(args,name="show_secrets", default=False)

            active_only = self._get_arg(args, "env") == "active"

            rows = self._get_config_rows(active_only=active_only, show_secrets=show_secrets)

            if return_rows:
                return rows

            if active_only:
                self.output.panel(
                    self._render_config_section("Active Configuration", rows),
                    title="Active Templar Configuration",
                )
            else:
                dev_rows = [row for row in rows if row["environment"] == "dev"]
                prod_rows = [row for row in rows if row["environment"] == "prod"]

                self.output.panel(
                    Columns(
                        [
                            self._render_config_section("Dev Configuration", dev_rows),
                            self._render_config_section("Prod Configuration", prod_rows),
                        ],
                        expand=True,
                        equal=True,
                        padding=(0, 3),
                    ),
                    title="Templar Configuration Overview",
                )

            return None

        if action == "activate":
            self._activate_config(self._get_arg(args, "env"))

            return None

        if action == "set":
            env, key, value = self._parse_set_args(args)
            self._set_config(env, key, value)

            return None

        self.output.error(f"Unknown action '{action}'")

        return None

    # -----------------------------
    # Actions
    # -----------------------------
    def _activate_config(self, env: str):
        if env not in ("dev", "prod"):
            self.output.error("You must specify 'dev' or 'prod'")

            return

        self.cli.config.set_active_config(env)
        self.output.success(f"Activated '{env}' configuration")

    def _set_config(self, env: str, key: str, value: str):
        if env not in ("dev", "prod", "active"):
            self.output.error("Environment must be dev, prod, or active")

            return

        if key.lower() == "mode":
            self.output.error("'mode' is read-only. Use `templar config activate dev|prod`.")

            return

        env_cfg = self._get_env_config(env)

        if key not in env_cfg:
            self.output.error(f"Unknown config key '{key}'.\nRun `templar config show` to view valid keys.")

            return

        current_value = env_cfg[key]

        # Type casting is driven by the existing schema value.
        if isinstance(current_value, bool):
            if value.lower() not in ("1", "0", "true", "false", "yes", "no", "on", "off",):
                self.output.error(f"'{key}' must be a boolean")

                return

            value = value.lower() in ("1", "true", "yes", "on")

        elif isinstance(current_value, int):
            try:
                value = int(value)
            except ValueError:
                self.output.error(f"'{key}' must be an integer")

                return

        elif isinstance(current_value, (list, dict)):
            try:
                value = yaml.safe_load(value)
            except yaml.YAMLError:
                self.output.error(f"'{key}' must be valid YAML")

                return

            if not isinstance(value, type(current_value)):
                self.output.error(f"'{key}' must be a {type(current_value).__name__}")

                return

        self.cli.config.set(key, value, None if env == "active" else env)

        self.output.success(f"Set '{key}' = '{value}' in '{env}' environment")