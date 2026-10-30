import json
import sys
import ssl
import hashlib
import threading
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from http.server import ThreadingHTTPServer
from typing import Any, Callable, Optional

from templar.cli.CliOutput import CliOutput
from templar.Config import Config
from templar.Router import Router
from templar.Renderer import Renderer
from templar.RequestHandler import RequestHandler
from templar.middleware.MiddlewareManager import MiddlewareManager
from templar.middleware.SessionMiddleware import install as install_session_middleware
from templar.middleware.AuthMiddleware import install as install_auth_middleware
from templar.middleware.CsrfMiddleware import install as install_csrf_middleware
from templar.cache import Cache, CacheManager
from templar.core.Performance import cache_result
from templar.core.Logger import StructuredFormatter
from templar.db import create_database

sys.dont_write_bytecode = True


class TemplarServer(ThreadingHTTPServer):
    """
    Templar server engine.

    - Uses user project templates
    - Integrates Router and Renderer
    - Honors dev/prod configuration
    """

    interrupted = False

    def __init__(
        self,
        config: Config,
        output: CliOutput,
        router: Router | None = None,
        renderer: Renderer | None = None,
        templates_dir: Path | None = None,
        themes_dir: Path | None = None,
        static_dir: Path | None = None,
        middleware: MiddlewareManager | None = None,
        user_loader: Optional[Callable[[Any], Optional[dict]]] = None,
        port_override: Optional[int] = None,
    ):
        """
        Args:
            config: Templar Config instance
            output: CliOutput instance for structured CLI output
            router: Optional Router instance; auto-created if None
            renderer: Optional Renderer instance; auto-created if None
            templates_dir: Optional Path to templates directory
        """
        self.config = config
        self.output = output

        # Config overrides can be applied by embedding applications as well as the CLI. Validate the effective values at
        # the network boundary so a proxy-only production setup can never bind public plaintext HTTP.
        self.config.validate_active_security()
        self.user_loader: Optional[Callable[[Any], Optional[dict]]] = None

        if user_loader is not None:
            self.set_user_loader(user_loader)

        self.active_config = config.get_active_config()
        self.mode = config.active_env

        # One cache facade per server. Backends are selected from the active environment's cache_backend/cache configuration.
        configured_namespace = self.active_config.get("cache_namespace")
        namespace_source = str(configured_namespace or self.active_config.get("project_root", "templar"))

        # Never place a filesystem path directly in a shared cache key.
        self.cache_namespace = hashlib.sha256(namespace_source.encode("utf-8")).hexdigest()[:24]
        self.cache = Cache(CacheManager(self.active_config).provider, namespace=self.cache_namespace)

        # Keep an independent connection per server; RequestHandler binds it to the current request before
        # application/model code is executed.
        self.database = create_database(self.active_config)

        # Resolve network configuration
        host = self.active_config.get("host", "0.0.0.0")
        port = (port_override if port_override is not None else self.active_config.get("port", 8000))

        self.default_route = self.active_config.get("default_route", "index")
        self.max_body_size = int(self.active_config.get("max_body_size", 1_048_576))
        self.max_form_fields = int(self.active_config.get("max_form_fields", 1_000))
        self.request_timeout = float(self.active_config.get("request_timeout_seconds", 30))
        self.max_workers = int(self.active_config.get("max_workers", 100))
        self.sse_heartbeat_seconds = float(self.active_config.get("sse_heartbeat_seconds", 15))
        self.log_max_bytes = int(self.active_config.get("log_max_bytes", 10_485_760))
        self.log_backup_count = int(self.active_config.get("log_backup_count", 5))

        if self.request_timeout <= 0:
            raise ValueError("request_timeout_seconds must be greater than zero")

        if self.max_form_fields <= 0:
            raise ValueError("max_form_fields must be greater than zero")

        if self.max_workers <= 0:
            raise ValueError("max_workers must be greater than zero")

        if self.sse_heartbeat_seconds <= 0:
            raise ValueError("sse_heartbeat_seconds must be greater than zero")

        if self.log_max_bytes <= 0:
            raise ValueError("log_max_bytes must be greater than zero")

        if self.log_backup_count < 1:
            raise ValueError("log_backup_count must be at least one")

        self.logger = self._configure_logger()

        # ``ThreadingHTTPServer`` otherwise creates a new handler thread for every accepted socket. The semaphore
        # deliberately applies backpressure in the acceptance loop once the configured worker limit is reached.
        self._worker_slots = threading.BoundedSemaphore(self.max_workers)

        # Static gzip HEAD responses reuse this metadata until the source file changes, avoiding a full compression pass
        # for every health probe.
        self._gzip_metadata_cache = {}
        self._gzip_metadata_lock = threading.RLock()
        self._gzip_metadata_file_locks = {}
        self._gzip_metadata_lock_factory = threading.Lock
        self.gzip_metadata_max_entries = 256
        self.allowed_hosts = self.active_config.get("allowed_hosts", [])
        self.cors_enabled = bool(self.active_config.get("cors", False))
        self.gzip_enabled = bool(self.active_config.get("gzip", False))
        self.tls_enabled = False
        self._ssl_context = None

        # Initialize HTTP server. Binding can fail (for example, when the port is occupied) after database and log
        # resources exist, so explicitly release those resources on the constructor failure path.
        try:
            super().__init__((host, port), RequestHandler)
        except Exception:
            self.database.close()
            self._close_logger_handlers()

            raise

        cert_path = self.active_config.get("ssl_cert_path")
        key_path = self.active_config.get("ssl_key_path")

        if bool(cert_path) != bool(key_path):
            self.server_close()

            raise ValueError("Both ssl_cert_path and ssl_key_path are required to enable TLS")

        if cert_path and key_path:
            try:
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(certfile=cert_path, keyfile=key_path)

                # Keep the listening socket plain. Handshaking a wrapped listener happens during accept and lets a stalled
                # TLS client block the server's acceptance loop before request timeouts apply.
                self._ssl_context = context
                self.tls_enabled = True
            except Exception:
                self.server_close()
                raise

        # Resolve templates directory
        self.templates_dir = (templates_dir or Path(self.active_config.get("templates_dir", "templates"))).resolve()
        self.themes_dir = (themes_dir or Path(self.active_config.get("themes_dir", "themes"))).resolve()
        self.static_dir = (static_dir or Path(self.active_config.get("static_dir", "static"))).resolve()

        # Initialize Renderer and Router
        self.renderer = renderer or Renderer(
            self.config,
            self.templates_dir,
            self.themes_dir,
            self.static_dir
        )
        self.router = router or Router(config=self.config)
        self.middleware = middleware or MiddlewareManager()
        install_session_middleware(self.middleware, self.config)
        install_csrf_middleware(self.middleware, self.config)
        install_auth_middleware(self.middleware)

    def _configure_logger(self) -> logging.Logger:
        """Create an isolated, configuration-backed server logger."""
        logger = logging.getLogger(f"templar.server.{id(self)}")

        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

        logger.propagate = False
        level_name = str(self.active_config.get("log_level", "INFO")).upper()
        logger.setLevel(getattr(logging, level_name, logging.INFO))
        log_file = self.active_config.get("log_file")

        if log_file:
            path = Path(log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                path,
                maxBytes=self.log_max_bytes,
                backupCount=self.log_backup_count,
                encoding="utf-8",
            )
            handler.setLevel(logger.level)
            handler.setFormatter(StructuredFormatter())
            logger.addHandler(handler)
        else:
            logger.addHandler(logging.NullHandler())

        return logger

    def log_exception(self, message: str) -> None:
        """Record an exception without exposing it in the HTTP response."""
        self.logger.exception(message)

    def get_request(self):
        """Accept one connection without doing TLS work in the accept loop."""
        request, client_address = super().get_request()
        request.settimeout(self.request_timeout)

        if self._ssl_context is None:
            return request, client_address

        try:
            tls_request = self._ssl_context.wrap_socket(
                request, server_side=True, do_handshake_on_connect=False
            )

            # Handshakes happen in RequestHandler.setup(), after the socket has been assigned a bounded worker. A stalled
            # client, therefore, cannot prevent this loop from accepting later connections.
            return tls_request, client_address
        except (OSError, ssl.SSLError):
            request.close()
            raise

    def process_request(self, request, client_address) -> None:
        """Bound handler threads without blocking the serving/shutdown loop."""
        if not self._worker_slots.acquire(blocking=False):
            self._reject_overloaded_request(request)

            return

        try:
            super().process_request(request, client_address)
        except Exception:
            self._worker_slots.release()
            raise

    def _reject_overloaded_request(self, request) -> None:
        """Return a minimal response without allocating another handler thread."""
        if self.tls_enabled:
            # The accepted socket deliberately has not completed its TLS handshake yet: that work belongs to a bounded
            # request worker. Calling ``sendall`` here would implicitly start the handshake in the acceptance loop and
            # allow a stalled client to block it. Close instead; a client can retry once worker capacity exists.
            request.close()

            return

        body = b"<h1>503</h1><p>Server is busy; retry shortly.</p>"
        response = (
            b"HTTP/1.1 503 Service Unavailable\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Connection: close\r\n"
            b"Retry-After: 1\r\n"
            + f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
            + body
        )

        try:
            request.sendall(response)
        except OSError:
            pass
        finally:
            self.shutdown_request(request)

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._worker_slots.release()

    def set_user_loader(self, loader: Callable[[Any], Optional[dict]]) -> None:
        """Register the application callback used to load users by session ID."""
        if not callable(loader):
            raise TypeError("user_loader must be callable")

        self.user_loader = loader

    def cache_result(self, ttl_seconds: int = 300):
        """Create a result-cache decorator bound to this server's cache."""
        return cache_result(ttl_seconds=ttl_seconds, cache=self.cache, namespace=self.cache_namespace)

    def start(self):
        """Start serving requests."""
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            self.interrupted = True
        finally:
            self.server_close()

    def server_close(self):
        """Close listening, database, and file-log resources once."""
        try:
            super().server_close()
        finally:
            database = getattr(self, "database", None)

            if database is not None:
                database.close()

            self._close_logger_handlers()

    def _close_logger_handlers(self) -> None:
        """Flush, close, and detach this server's isolated log handlers."""
        logger = getattr(self, "logger", None)

        if logger is None:
            return

        for handler in list(logger.handlers):
            try:
                handler.flush()
                handler.close()
            finally:
                logger.removeHandler(handler)

    def handle_request_logs(self, logs: dict) -> None:
        """
        Prints two panels:
        1. Merged HTTP + request logs (excluding static files)
        2. Renderer logs (for HTML templates only)
        """
        for entry in logs.get("request", []):
            if isinstance(entry, dict):
                self.logger.info(json.dumps(entry, default=str))
            else:
                self.logger.info(str(entry))

        if self.mode != "dev":
            return

        combined_logs = logs.get("http", []) + logs.get("request", [])
        filtered_logs = []

        for entry in combined_logs:
            if isinstance(entry, dict):
                rendered = json.dumps(entry, default=str, sort_keys=True)
            else:
                rendered = str(entry)

            if any(skip in rendered for skip in ("/static/", "/favicon.ico")):
                continue

            filtered_logs.append(rendered)

        if filtered_logs:
            self.output.panel(
                content=filtered_logs,
                title="Request / Response Log",
                border_style="green",
            )

        renderer_template = logs.get("renderer_template")
        if renderer_template:
            matrix_log = self.renderer.get_matrix_log()
            if matrix_log.strip():
                self.output.panel(
                    content=[matrix_log],
                    title=f"DOM / Render Tree [{renderer_template}]",
                    border_style="cyan",
                )