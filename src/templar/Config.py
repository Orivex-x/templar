import sys, os, re, yaml, warnings, shutil, tempfile, stat, ipaddress
from copy import deepcopy
from typing import Any, Dict, Optional
import importlib.resources as pkg_resources

sys.dont_write_bytecode = True

class Config:
    _ENV_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
    # Bundled defaults travel inside the installed package.
    PACKAGE_ROOT = os.path.abspath(os.path.dirname(__file__))
    PACKAGE_CONFIG_PATH = os.path.join(PACKAGE_ROOT, "templar.config.yml")

    _REQUIRED_DEV_KEYS = [
        "mode", "host", "port", "debug", "log_file", "session_secret"
    ]
    
    _REQUIRED_PROD_KEYS = [
        "mode", "host", "port", "debug", "deployment_domain",
        "ssl_cert_path", "ssl_key_path", "log_file", "session_secret",
        "db_engine", "db_uri"
    ]

    def __init__(self, config_path: Optional[str] = None, environment: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Optional path to YAML config (user project preferred).
            environment: 'dev' or 'prod'. Defaults to the config's ``active``
                setting, or ``dev`` when it is absent.
        """
        # Determine the config path: project first, fallback to package. The bundled config is read-only defaults,
        # never a mutation target.
        self._using_package_defaults = False

        if config_path is None:
            project_config = os.path.join(os.getcwd(), "templar.config.yml")

            if os.path.exists(project_config):
                self._config_path = project_config
            else:
                self._config_path = self.PACKAGE_CONFIG_PATH
                self._using_package_defaults = True
        else:
            self._config_path = config_path

        self._config: Dict[str, Any] = {}

        # Project dotenv values are intentionally instance-local. Mutating os.environ here makes a previously loaded
        # project influence the next Config instance in the same process.
        self._dotenv_values: Dict[str, str] = {}

        # Keep substitutions separate from the resolved runtime configuration. A later `templar config set` must never
        # turn `${SECRET}` into a plaintext secret in the project's YAML file.
        self._environment_references: Dict[tuple, str] = {}

        # Load YAML config
        self._load_dotenv()
        self._load()
        self._normalize_schema()
        self._validate_keys()

        # Determine active environment
        env = environment or self._environment_value("TEMPLAR_ENV") or self._config.get("active", "dev")

        if env not in self._config:
            fallback = "dev" if "dev" in self._config else "prod"
            warnings.warn(f"Environment '{env}' not found in config. Using fallback '{fallback}'.")
            env = fallback

        self._active_key = env
        self._activate_environment(env)
        self._apply_runtime_environment()
        self._validate_active_security()

    # ---------------------
    # Internal Loading
    # ---------------------
    def _load(self):
        """Load YAML config from file, or copy skeleton if missing."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config = self._safe_load_yaml(f.read()) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in {self._config_path}: {e}")
        else:
            self._write_from_skeleton()

    def _load_dotenv(self) -> None:
        """Read simple project-local ``.env`` values without changing the OS."""
        if self._using_package_defaults:
            dotenv = os.path.join(os.getcwd(), ".env")
        else:
            dotenv = os.path.join(os.path.dirname(os.path.abspath(self._config_path)), ".env")

        if not os.path.isfile(dotenv):
            return

        with open(dotenv, encoding="utf-8") as dotenv_file:
            for raw_line in dotenv_file:
                line = raw_line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()

                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                    continue

                value = value.strip()

                if len(value) >= 2 and value[:1] == value[-1:] and value[:1] in {"'", '"'}:
                    value = value[1:-1]

                self._dotenv_values[key] = value

    def _environment_value(self, name: str) -> Optional[str]:
        """Return an OS value first, then this config's local dotenv value."""
        return os.environ.get(name, self._dotenv_values.get(name))

    def _expand_environment(self, value):
        if isinstance(value, dict):
            return {key: self._expand_environment(item) for key, item in value.items()}

        if isinstance(value, list):
            return [self._expand_environment(item) for item in value]

        if not isinstance(value, str):
            return value

        def replace(match):
            variable = match.group(1)
            resolved = self._environment_value(variable)

            if resolved is None:
                raise ValueError(f"Configuration references unset environment variable: {variable}")

            return resolved

        return self._ENV_REFERENCE.sub(replace, value)

    def _activate_environment(self, environment: str) -> None:
        """Resolve only the selected environment into a runtime-only mapping.

        Projects commonly keep production-only references in their config while
        developing locally. Resolving every environment would make a missing
        production secret prevent a development server from starting.
        """
        source = self._config.get(environment, {})
        self._record_environment_references(source, (environment,))
        self._active_config = self._expand_environment(deepcopy(source))
        self._inject_paths(self._active_config)

    def _record_environment_references(self, value: Any, path: tuple = ()) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                self._record_environment_references(item, path + (key,))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                self._record_environment_references(item, path + (index,))
        elif isinstance(value, str) and self._ENV_REFERENCE.search(value):
            self._environment_references[path] = value

    def _apply_runtime_environment(self) -> None:
        """Honor documented process-level deployment overrides."""
        mappings = {"TEMPLAR_HOST": "host", "TEMPLAR_PORT": "port", "TEMPLAR_DEBUG": "debug"}

        for variable, key in mappings.items():
            value = self._environment_value(variable)

            if value is None:
                continue

            if key == "port":
                try:
                    value = int(value)
                except ValueError as exc:
                    raise ValueError("TEMPLAR_PORT must be an integer") from exc
            elif key == "debug":
                if value.lower() not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
                    raise ValueError("TEMPLAR_DEBUG must be a boolean")

                value = value.lower() in {"true", "1", "yes", "on"}

            self._active_config[key] = value

        secret = self._environment_value("TEMPLAR_SESSION_SECRET") or self._environment_value("TEMPLAR_SECRET_KEY")

        if secret:
            self._active_config["session_secret"] = secret

    def _safe_load_yaml(self, content: str) -> Dict[str, Any]:
        try:
            return yaml.safe_load(content) or {}
        except yaml.YAMLError:
            repaired = self._quote_unquoted_uri_scalars(content)

            if repaired == content:
                raise

            return yaml.safe_load(repaired) or {}

    def _quote_unquoted_uri_scalars(self, content: str) -> str:
        repaired_lines = []
        pattern = re.compile(r"^(\s*[\w-]+:\s*)([^#\n]*://[^#\n]*)(\s*(?:#.*)?)$")

        for line in content.splitlines():
            match = pattern.match(line)

            if not match:
                repaired_lines.append(line)
                continue

            prefix, value, suffix = match.groups()
            stripped = value.strip()

            if stripped.startswith(("'", '"')):
                repaired_lines.append(line)
                continue

            repaired_lines.append(f"{prefix}{stripped!r}{suffix}")

        return "\n".join(repaired_lines)

    def _load_package_defaults(self) -> Dict[str, Any]:
        if os.path.exists(self.PACKAGE_CONFIG_PATH) and self.PACKAGE_CONFIG_PATH != self._config_path:
            try:
                with open(self.PACKAGE_CONFIG_PATH, "r", encoding="utf-8") as f:
                    defaults = yaml.safe_load(f) or {}

                    if "dev" in defaults and "prod" in defaults:
                        return defaults
            except yaml.YAMLError:
                pass

        try:
            with pkg_resources.path("templar.skeleton", "templar.config.yml") as skeleton_file:
                with open(skeleton_file, "r", encoding="utf-8") as f:
                    defaults = yaml.safe_load(f) or {}

                    if "dev" in defaults and "prod" in defaults:
                        return defaults
        except FileNotFoundError:
            pass

        return {
            "active": "dev",
            "dev": {
                "mode": "dev", "host": "127.0.0.1", "port": 8000,
                "debug": True, "theme": "light", "default_route": "index",
                "log_file": "logs/dev.log", "session_secret": "changeme",
                "session_cookie_name": "templar_session", "session_cookie_secure": False,
                "session_cookie_samesite": "Lax", "session_ttl_seconds": 86400, "max_body_size": 1048576,
                "deployment_domain": "", "ssl_cert_path": "", "ssl_key_path": "",
                "db_engine": "sqlite", "db_uri": "sqlite:///db/dev.db",
                "migrations_dir": "migrations",
            },
            "prod": {
                "mode": "prod", "host": "0.0.0.0", "port": 8000,
                "debug": False, "theme": "light", "default_route": "index",
                "log_file": "logs/prod.log", "session_secret": "changeme",
                "session_cookie_name": "templar_session", "session_cookie_secure": True,
                "session_cookie_samesite": "Lax", "session_ttl_seconds": 86400, "max_body_size": 1048576,
                "deployment_domain": "example.com", "ssl_cert_path": "",
                "ssl_key_path": "", "db_engine": "sqlite",
                "db_uri": "sqlite:///db/prod.db", "migrations_dir": "migrations",
            },
        }

    def _normalize_schema(self) -> None:
        defaults = self._load_package_defaults()
        base_root = os.path.dirname(os.path.abspath(self._config_path))

        if "dev" not in self._config and "prod" not in self._config:
            self._config = self._from_legacy_schema(self._config, defaults, base_root)

            return

        for env_name in ("dev", "prod"):
            env_defaults = dict(defaults.get(env_name, {}))
            env_config = self._config.get(env_name, {})
            self._config[env_name] = {
                **env_defaults,
                **(env_config if isinstance(env_config, dict) else {}),
            }

        self._config.setdefault("active", defaults.get("active", "dev"))

    def _from_legacy_schema(self, config: Dict[str, Any], defaults: Dict[str, Any], base_root: str) -> Dict[str, Any]:
        app = config.get("app", {}) if isinstance(config.get("app"), dict) else {}
        server = config.get("server", {}) if isinstance(config.get("server"), dict) else {}
        project = config.get("project", {}) if isinstance(config.get("project"), dict) else {}
        database = config.get("database", {}) if isinstance(config.get("database"), dict) else {}
        logging_cfg = config.get("logging", {}) if isinstance(config.get("logging"), dict) else {}
        session = config.get("session", {}) if isinstance(config.get("session"), dict) else {}

        mode = str(server.get("mode", "dev")).lower()
        active = "prod" if mode in ("prod", "production") else "dev"
        host = server.get("host", defaults.get(active, {}).get("host", "127.0.0.1"))
        port = server.get("port", defaults.get(active, {}).get("port", 8000))
        debug = app.get("debug", defaults.get(active, {}).get("debug", active == "dev"))
        session_secret = server.get("secret_key") or session.get("secret") or defaults.get(active, {}).get("session_secret", "changeme")
        log_file = logging_cfg.get("file", defaults.get(active, {}).get("log_file", "logs/dev.log"))

        db_engine = database.get("driver", defaults.get(active, {}).get("db_engine", "sqlite"))
        db_uri = database.get("uri")

        if not db_uri:
            if db_engine == "sqlite":
                db_uri = f"sqlite:///{database.get('path', './data/app.db')}"
            else:
                db_uri = defaults.get(active, {}).get("db_uri", "")

        normalized = {"active": active}

        for env_name in ("dev", "prod"):
            env = dict(defaults.get(env_name, {}))
            env.update({
                "mode": env_name,
                "host": host,
                "port": port,
                "debug": bool(debug) if env_name == "dev" else False,
                "theme": env.get("theme", "light"),
                "default_route": env.get("default_route", "index"),
                "log_level": logging_cfg.get("level", env.get("log_level", "DEBUG" if env_name == "dev" else "INFO")),
                "log_file": log_file if env_name == "dev" else env.get("log_file", "logs/prod.log"),
                "logs_dir": project.get("logs_dir", "./logs"),
                "session_secret": session_secret,
                "db_engine": db_engine,
                "db_uri": db_uri,
                "migrations_dir": project.get("migrations_dir", "migrations"),
                "deployment_domain": env.get("deployment_domain", ""),
                "ssl_cert_path": env.get("ssl_cert_path", ""),
                "ssl_key_path": env.get("ssl_key_path", ""),
            })
            normalized[env_name] = env

        return normalized

    def _write_from_skeleton(self):
        """Copy default skeleton config from package if missing."""
        os.makedirs(os.path.dirname(self._config_path) or ".", exist_ok=True)

        try:
            with pkg_resources.path("templar.skeleton", "templar.config.yml") as skeleton_file:
                shutil.copyfile(skeleton_file, self._config_path)

            with open(self._config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise FileNotFoundError(f"No config found at {self._config_path} and skeleton missing.")

    def _materialize_project_config(self) -> None:
        """Turn an implicit package-default configuration into a local project file."""
        if not self._using_package_defaults:
            return

        self._config_path = os.path.join(os.getcwd(), "templar.config.yml")
        self._config = {}
        self._write_from_skeleton()
        self._normalize_schema()
        self._validate_keys()
        self._using_package_defaults = False

        active = self._config.get("active", "dev")

        if active not in self._config:
            active = "dev" if "dev" in self._config else "prod"

        self._active_key = active
        self._active_key = active
        self._activate_environment(active)
        self._validate_active_security()

    # ---------------------
    # Path Injection
    # ---------------------
    def _inject_paths(self, cfg: Dict[str, Any]) -> None:
        """Convert active-environment path keys to project-relative absolutes."""
        PATH_KEYS = [
            "ssl_cert_path", "ssl_key_path", "log_file", "migrations_dir",
            "logs_dir", "templates_dir", "themes_dir", "static_dir",
            "marketplace_registry_dir", "marketplace_assets_dir",
        ]

        # Base project root for this config
        base_root = os.path.dirname(os.path.abspath(self._config_path))

        for k in PATH_KEYS:
            if k in cfg and isinstance(cfg[k], str) and cfg[k]:
                cfg[k] = os.path.abspath(
                    os.path.join(base_root, cfg[k]) if not os.path.isabs(cfg[k]) else cfg[k]
                )

        # Always include project_root
        cfg["project_root"] = base_root

        cfg.setdefault("templates_dir", os.path.join(base_root, "templates"))
        cfg.setdefault("themes_dir", os.path.join(base_root, "themes"))
        cfg.setdefault("static_dir", os.path.join(base_root, "static"))
        # The registry is Templar's verified package cache. Marketplace
        # downloads are materialised separately beneath static assets so an
        # application has one predictable, publicly servable install root.
        cfg.setdefault("marketplace_assets_dir", os.path.join(base_root, "static", "assets", "marketplace"))

    # ---------------------
    # Key Validation
    # ---------------------
    def _validate_keys(self):
        """Warn about missing required keys in dev/prod config."""
        for env_name, required_keys in (("dev", self._REQUIRED_DEV_KEYS), ("prod", self._REQUIRED_PROD_KEYS)):
            cfg = self._config.get(env_name, {})
            missing = [k for k in required_keys if k not in cfg]

            if missing:
                warnings.warn(f"Missing keys in {env_name} config: {missing}", UserWarning)

    def _validate_active_security(self) -> None:
        insecure_secrets = {"", "changeme", "supersecret", "your-secret-key-change-this"}
        secret = str(self._active_config.get("session_secret", ""))

        if self._active_key == "prod" and secret.lower() in insecure_secrets:
            raise ValueError("Production requires a non-default session_secret")

        if self._active_key == "prod":
            if self._active_config.get("session_cookie_secure") is not True:
                raise ValueError("Production requires session_cookie_secure: true")

            cert_path = self._active_config.get("ssl_cert_path", "")
            key_path = self._active_config.get("ssl_key_path", "")

            if not isinstance(cert_path, str) or not isinstance(key_path, str):
                raise ValueError("Production TLS paths must be strings")

            cert_path = cert_path.strip()
            key_path = key_path.strip()

            if bool(cert_path) != bool(key_path):
                raise ValueError("Production TLS requires both ssl_cert_path and ssl_key_path")

            if not cert_path:
                if self._active_config.get("tls_terminated_by_proxy") is not True:
                    raise ValueError(
                        "Production requires TLS certificates or explicit tls_terminated_by_proxy: true"
                    )

                host = str(self._active_config.get("host", "")).strip().lower()

                try:
                    is_loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
                except ValueError:
                    is_loopback = False

                if not is_loopback:
                    raise ValueError(
                        "TLS-terminated production deployments must bind to localhost or a loopback IP"
                    )
        if self._active_config.get("use_async_db", False):
            raise ValueError("use_async_db is not supported by Templar's synchronous database API")

    # ---------------------
    # Accessors
    # ---------------------
    def set_active_config(self, key: str, persist: bool = True):
        if persist:
            self._materialize_project_config()

        if key not in self._config:
            raise ValueError(f"No such environment '{key}' in config")
        
        previous_key = self._active_key
        previous_config = self._active_config
        self._active_key = key

        try:
            self._activate_environment(key)
            self._apply_runtime_environment()
            self._validate_active_security()
        except Exception:
            self._active_key = previous_key
            self._active_config = previous_config
            raise

        if persist:
            self._config["active"] = key
            self._write_config_file()

    def override(self, key: str, value: Any) -> None:
        """Apply a runtime-only active-environment override without writing YAML."""
        missing = object()
        previous = self._active_config.get(key, missing)
        self._active_config[key] = value

        try:
            self._validate_active_security()
        except Exception:
            if previous is missing:
                self._active_config.pop(key, None)
            else:
                self._active_config[key] = previous
            raise

    def validate_active_security(self) -> None:
        """Validate the effective runtime configuration before server startup."""
        self._validate_active_security()

    def set(self, key: str, value: Any, env: Optional[str] = None):
        self._materialize_project_config()
        target_env = env or self._active_key

        if target_env not in self._config:
            raise ValueError(f"No such environment '{target_env}' in config")
        
        missing = object()
        previous_raw = self._config[target_env].get(key, missing)
        previous_active = self._active_config
        self._config[target_env][key] = value

        if target_env == self._active_key:
            try:
                self._activate_environment(self._active_key)
                self._apply_runtime_environment()
                self._validate_active_security()
            except Exception:
                if previous_raw is missing:
                    self._config[target_env].pop(key, None)
                else:
                    self._config[target_env][key] = previous_raw

                self._active_config = previous_active

                raise

        self._environment_references.pop((target_env, key), None)
        
        self._write_config_file()
        
    def get_active_config(self) -> Dict[str, Any]:
        return dict(self._active_config)

    def get(self, key: str, default: Any = None) -> Any:
        return self._active_config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """
        Return the full configuration dictionary,
        including dev, prod, and active.
        """
        return dict(self._config)

    def _write_config_file(self):
        config_to_write = deepcopy(self._config)
        for path, raw_value in self._environment_references.items():
            target = config_to_write

            try:
                for component in path[:-1]:
                    target = target[component]

                target[path[-1]] = raw_value
            except (KeyError, IndexError, TypeError):
                # A user intentionally replaced or removed this setting.
                continue
        config_path = os.path.abspath(self._config_path)
        directory = os.path.dirname(config_path) or "."
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(config_path)}.",
            suffix=".tmp",
            dir=directory,
        )
        try:
            if os.path.exists(config_path):
                # ``os.fchmod`` is unavailable on Windows. Applying the mode
                # by path is supported on every Templar platform (Windows may
                # honor only its writable bit, which is still preferable to
                # failing a configuration update).
                try:
                    os.chmod(temporary_path, stat.S_IMODE(os.stat(config_path).st_mode))
                except OSError:
                    pass
            with os.fdopen(descriptor, "w", encoding="utf-8") as config_file:
                yaml.safe_dump(config_to_write, config_file, sort_keys=False, indent=2)
                config_file.flush()
                os.fsync(config_file.fileno())

            os.replace(temporary_path, config_path)
        except Exception:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass

            raise

    # ---------------------
    # Dict-like / Attr access
    # ---------------------
    def __getattr__(self, key: str) -> Any:
        if key in self._active_config:
            return self._active_config[key]
            
        raise AttributeError(f"Config has no attribute '{key}'")

    def __getitem__(self, key: str) -> Any:
        return self._active_config[key]

    def __setitem__(self, key: str, value: Any):
        self.set(key, value)

    def __repr__(self) -> str:
        return f"<TemplarConfig active={self._active_key} {self._active_config}>"

    def list_config(self) -> str:
        return yaml.safe_dump(self._active_config, sort_keys=False, indent=2)
    
    @property
    def active_env(self) -> str:
        """Return 'dev' or 'prod' as set in config."""
        return self._active_key
