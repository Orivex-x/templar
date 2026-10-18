import sys
import yaml
from rich.text import Text
from rich.columns import Columns
from templar.cli.BaseCommand import BaseCommand

sys.dont_write_bytecode = True

class ConfigCommand(BaseCommand):
    name = "config"
    help = "Show or modify configuration"
    _SENSITIVE_CONFIG_TERMS = ("secret", "password", "token", "credential", "api_key", "private_key", "db_uri", "redis_url")

    # -----------------------------
    # Arg parsing (intentionally loose)
    # -----------------------------
    @staticmethod
    def add_args(parser):
        parser.add_argument(
            "action",
            nargs="?",
            default="show",
            help="Action: show | activate | set"
        )
        parser.add_argument("env", nargs="?")
        parser.add_argument("key", nargs="?")
        parser.add_argument("value", nargs="?")
        parser.add_argument("--env", dest="target_env", choices=("dev", "prod", "active"), help="Target environment for 'set'")
        parser.add_argument("--show-secrets", action="store_true", help="Show resolved sensitive values when displaying configuration")

    # -----------------------------
    # Helpers
    # -----------------------------
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
        env = args.target_env or args.env
        key = args.key
        value = args.value

        if args.target_env and value is None and args.env and args.key:
            env, key, value = args.target_env, args.env, args.key

        # Natural active-environment form: `templar config set theme dark`.
        if args.target_env is None and value is None and env and key and ":" not in env:
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

    # -----------------------------
    # Run
    # -----------------------------
    def run(self, args, extra_args=None):
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}")
            sys.exit(1)

        action = (args.action or "show").lower()

        if action == "show":
            if args.env == "active":
                self._show_active_config(show_secrets=getattr(args, "show_secrets", False))
            else:
                self._show_config(show_secrets=getattr(args, "show_secrets", False))

            return

        if action == "activate":
            self._activate_config(args.env)

            return

        if action == "set":
            env, key, value = self._parse_set_args(args)
            self._set_config(env, key, value)

            return

        self.output.error(f"Unknown action '{action}'")

    # -----------------------------
    # Display
    # -----------------------------
    @classmethod
    def _display_value(cls, key: str, value, *, show_secrets: bool):
        normalized = key.lower()

        if not show_secrets and any(term in normalized for term in cls._SENSITIVE_CONFIG_TERMS):
            return "[redacted]"

        return value

    def _show_config(self, *, show_secrets: bool = False):
        config = self.cli.config.get_all()

        def render_section(title: str, section: dict) -> Text:
            text = Text()
            text.append(f"{title}\n", style="bold cyan underline")

            for k, v in section.items():
                v = self._display_value(k, v, show_secrets=show_secrets)
                key_text = Text(k, style="magenta")

                if isinstance(v, bool):
                    v_text = Text("yes" if v else "no", style="bold green" if v else "bold red")
                else:
                    v_text = Text(str(v), style="green")

                text.append_text(key_text)
                text.append(": ")
                text.append_text(v_text)
                text.append("\n")

            return text

        self.output.panel(
            Columns(
                [
                    render_section("Dev Configuration", config.get("dev", {})),
                    render_section("Prod Configuration", config.get("prod", {})),
                ],
                expand=True,
                equal=True,
                padding=(0, 3),
            ),
            title="Templar Configuration Overview",
        )

    def _show_active_config(self, *, show_secrets: bool = False):
        active = self.cli.config.get_active_config()
        text = Text("Active Configuration\n", style="bold cyan underline")

        for k, v in active.items():
            v = self._display_value(k, v, show_secrets=show_secrets)
            key_text = Text(k, style="magenta")

            if isinstance(v, bool):
                v_text = Text("yes" if v else "no", style="bold green" if v else "bold red")
            else:
                v_text = Text(str(v), style="green")

            text.append_text(key_text)
            text.append(": ")
            text.append_text(v_text)
            text.append("\n")

        self.output.panel(text, title="Active Templar Configuration")

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
            self.output.error(
                "'mode' is read-only. Use `templar config activate dev|prod`."
            )

            return

        env_cfg = self._get_env_config(env)

        if key not in env_cfg:
            self.output.error(
                f"Unknown config key '{key}'.\n"
                f"Run `templar config show` to view valid keys."
            )

            return

        current_value = env_cfg[key]

        # Type casting is driven by the existing schema value.
        if isinstance(current_value, bool):
            if value.lower() not in ("1", "0", "true", "false", "yes", "no", "on", "off"):
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

        self.cli.config.set(
            key,
            value,
            None if env == "active" else env
        )

        self.output.success(f"Set '{key}' = '{value}' in '{env}' environment")
