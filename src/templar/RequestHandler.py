import json
import mimetypes
import gzip
import html
import ipaddress
import re
import select
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler
from http import HTTPStatus

from templar.Context import TemplarContext
from templar.db import db

sys.dont_write_bytecode = True


class _ChunkedWriter:
    """Small binary writer that frames streamed output as HTTP chunks."""

    def __init__(self, raw) -> None:
        self.raw = raw

    def write(self, data: bytes) -> int:
        if not data:
            return 0

        self.raw.write(f"{len(data):X}\r\n".encode("ascii"))
        self.raw.write(data)
        self.raw.write(b"\r\n")

        return len(data)

    def finish(self) -> None:
        self.raw.write(b"0\r\n\r\n")


class _CountingWriter:
    """File-like sink used to determine a streamed representation's length."""

    def __init__(self) -> None:
        self.length = 0

    def write(self, data: bytes) -> int:
        self.length += len(data)

        return len(data)


class _DeadlineReader:
    """Buffered reader with an optional monotonic deadline for HTTP headers."""

    def __init__(self, raw, connection, deadline: float, original_timeout) -> None:
        self.raw = raw
        self.connection = connection
        self.deadline = deadline
        self.original_timeout = original_timeout
        self._buffer = bytearray()

    def set_header_deadline(self, deadline: float, original_timeout) -> None:
        self.deadline = deadline
        self.original_timeout = original_timeout

    def clear_header_deadline(self) -> None:
        self.deadline = None

    def _read_chunk(self, size: int) -> bytes:
        if self.deadline is not None:
            remaining = self.deadline - time.monotonic()

            if remaining <= 0:
                raise TimeoutError("Request headers exceeded the total read deadline")

            timeout = remaining if self.original_timeout is None else min(self.original_timeout, remaining)
            self.connection.settimeout(timeout)

        return self.raw.read1(size)

    def readline(self, limit: int = -1) -> bytes:
        while True:
            newline = self._buffer.find(b"\n")

            if newline >= 0:
                end = newline + 1

                if limit >= 0:
                    end = min(end, limit)

                result = bytes(self._buffer[:end])
                del self._buffer[:end]

                return result

            if limit >= 0 and len(self._buffer) >= limit:
                result = bytes(self._buffer[:limit])
                del self._buffer[:limit]

                return result

            chunk = self._read_chunk(4096)

            if not chunk:
                result = bytes(self._buffer)
                self._buffer.clear()

                return result

            self._buffer.extend(chunk)

    def read1(self, size: int = -1) -> bytes:
        if self._buffer:
            if size < 0:
                size = len(self._buffer)

            result = bytes(self._buffer[:size])
            del self._buffer[:size]

            return result

        return self._read_chunk(size)

    def close(self) -> None:
        """Match the file interface expected by StreamRequestHandler."""
        self.raw.close()


class _DeadlineWriter:
    """File-like adapter for gzip streaming through a response deadline."""

    def __init__(self, handler, deadline: float) -> None:
        self.handler = handler
        self.deadline = deadline

    def write(self, data: bytes) -> int:
        self.handler._write_response_bytes(data, self.deadline)

        return len(data)


class _InvalidResponseHeader(ValueError):
    """An application attempted to serialize an unsafe HTTP response header."""


class _BadRequest(ValueError):
    """A controlled HTTP framing or request-parsing failure."""


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP boundary for a TemplarServer instance."""

    server_version = "TemplarServer/1.0"
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        """Complete deferred TLS handshakes in the worker, not accept loop."""
        if getattr(self.server, "tls_enabled", False):
            deadline = time.monotonic() + float(self.server.request_timeout)
            self.request.setblocking(False)

            try:
                while True:
                    remaining = deadline - time.monotonic()

                    if remaining <= 0:
                        raise TimeoutError("TLS handshake timed out")

                    try:
                        self.request.do_handshake()
                        break
                    except ssl.SSLWantReadError:
                        readable, _, _ = select.select([self.request], [], [], remaining)

                        if not readable:
                            raise TimeoutError("TLS handshake timed out")
                    except ssl.SSLWantWriteError:
                        _, writable, _ = select.select([], [self.request], [], remaining)

                        if not writable:
                            raise TimeoutError("TLS handshake timed out")
            except Exception:
                self.close_connection = True
                self.request.close()
                raise
            finally:
                # Request parsing and response writes use this as their idle timeout after the total handshake deadline
                # has elapsed.
                if not self.request._closed:
                    self.request.settimeout(float(self.server.request_timeout))
        super().setup()

    def handle_one_request(self) -> None:
        """Dispatch every unsupported method through Templar's safe 405 path.

        BaseHTTPRequestHandler's default 501 path does not consume a body or
        close a persistent HTTP/1.1 connection. Replacing that fallback keeps
        arbitrary extension methods from leaving request bytes buffered.
        """
        try:
            original_reader = self.rfile
            original_timeout = self.connection.gettimeout()
            deadline = time.monotonic() + float(getattr(self.server, "request_timeout", 30))

            if isinstance(original_reader, _DeadlineReader):
                self.rfile = original_reader
                self.rfile.set_header_deadline(deadline, original_timeout)
            else:
                self.rfile = _DeadlineReader(original_reader, self.connection, deadline, original_timeout)

            self.raw_requestline = self.rfile.readline(65_537)

            if len(self.raw_requestline) > 65_536:
                self.requestline = ""
                self.request_version = ""
                self.command = ""
                self.close_connection = True
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)

                return

            if not self.raw_requestline:
                self.close_connection = True

                return

            if not self.parse_request():
                return

            # Header parsing uses the deadline-aware wrapper only. Request bodies have their own bounded reader and
            # deadline below.
            self.rfile.clear_header_deadline()
            self.connection.settimeout(original_timeout)
            self._response_committed = False

            if not self._request_host_is_allowed():
                self.close_connection = True
                self._reject_expectation(400, "Host is not allowed")

                return

            method = getattr(self, f"do_{self.command}", None)

            if method is None:
                self._method_not_allowed()
            else:
                method()

            self.wfile.flush()
        except TimeoutError as exc:
            self.log_error("Request timed out: %r", exc)
            self.close_connection = True

            try:
                self._reject_expectation(408, "Request timed out")
            except OSError:
                pass
        finally:
            if "original_reader" in locals():
                if isinstance(self.rfile, _DeadlineReader):
                    self.rfile.clear_header_deadline()

                self.connection.settimeout(original_timeout)

    def parse_request(self) -> bool:
        """Reject unsupported expectations that the base parser ignores."""
        self._expect_continue_sent = False
        parsed = super().parse_request()

        if not parsed:
            return False

        if self.headers.get_all("Expect"):
            if not self._has_supported_expectation():
                return self._reject_expectation(417, "Expectation Failed")

            # BaseHTTPRequestHandler recognizes only the exact untrimmed value. HTTP optional whitespace is valid,
            # so send the interim response ourselves when its parser did not invoke the hook.
            if not self._expect_continue_sent:
                return self.handle_expect_100()

        return True

    @staticmethod
    def _status_allows_body(status: int) -> bool:
        return not 100 <= status < 200 and status not in {204, 304}

    def log_message(self, format: str, *args) -> None:
        if not hasattr(self, "_log_buffer"):
            self._log_buffer = []

        message = format % args
        # ``BaseHTTPRequestHandler`` includes the complete request target in its normal access log. Query strings commonly
        # carry reset tokens, signed URLs, and other credentials, so retain only the path in both file and development
        # console diagnostics.
        request_target = getattr(self, "path", "")

        if request_target:
            message = message.replace(request_target, urlparse(request_target).path or "/")

        self._log_buffer.append(f"[HTTP] {self.address_string()} - {message}")

    @staticmethod
    def _flatten(values: dict) -> dict:
        return {key: value[0] if len(value) == 1 else value for key, value in values.items()}

    def _transfer_encodings(self) -> list[str]:
        return [
            encoding.strip().lower()
            for value in (self.headers.get_all("Transfer-Encoding") or [])
            for encoding in value.split(",")
            if encoding.strip()
        ]

    def _reject_transfer_encoding(self) -> None:
        # Templar implements only Content-Length request framing. Even an empty/malformed Transfer-Encoding field must
        # be rejected: accepting it while a proxy interprets it differently reopens desynchronization and request
        # smuggling risks.
        if self.headers.get_all("Transfer-Encoding"):
            self.close_connection = True

            raise _BadRequest("Transfer-Encoding is not supported; send a Content-Length request body")

    def _read_body(self) -> bytes:
        self._reject_transfer_encoding()
        lengths = self._content_lengths()
        length = lengths[0] if lengths else 0
        max_body_size = getattr(self.server, "max_body_size", 1_048_576)

        if length > max_body_size:
            self.close_connection = True

            raise OverflowError(f"Request body exceeds the {max_body_size}-byte limit")

        if not length:
            return b""

        # Socket timeouts only limit idle gaps. Use bounded read1() calls and a monotonic deadline so a client trickling
        # bytes can never reserve a worker forever.
        body_chunks = []
        remaining = length
        deadline = time.monotonic() + float(getattr(self.server, "request_timeout", 30))
        original_timeout = self.connection.gettimeout()

        try:
            while remaining:
                time_left = deadline - time.monotonic()

                if time_left <= 0:
                    raise TimeoutError("Request body exceeded the total read deadline")

                if original_timeout is None:
                    self.connection.settimeout(time_left)
                else:
                    self.connection.settimeout(min(original_timeout, time_left))

                chunk = self.rfile.read1(min(64 * 1024, remaining))

                if not chunk:
                    self.close_connection = True

                    raise _BadRequest("Incomplete request body")

                body_chunks.append(chunk)
                remaining -= len(chunk)
            return b"".join(body_chunks)
        finally:
            self.connection.settimeout(original_timeout)

    def _has_supported_expectation(self) -> bool:
        values = self.headers.get_all("Expect") or []

        return len(values) == 1 and values[0].strip().lower() == "100-continue"

    def _reject_expectation(self, status: int, message: str, *, allow: bool = False) -> bool:
        """Send a framing rejection before accepting an Expect request body."""
        body = f"<h1>{status}</h1><p>{message}</p>".encode("utf-8")
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")

        if allow:
            self.send_header("Allow", "GET, POST, HEAD, OPTIONS")

        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self._response_committed = True
        self.end_headers()
        self.wfile.write(body)

        return False

    def handle_expect_100(self) -> bool:
        """Validate framing and limits before inviting a client to upload."""
        self._response_committed = False

        if not self._has_supported_expectation():
            return self._reject_expectation(417, "Expectation Failed")

        if not self._request_host_is_allowed():
            self.close_connection = True

            return self._reject_expectation(400, "Host is not allowed")

        try:
            self._reject_transfer_encoding()
            lengths = self._content_lengths()
            length = lengths[0] if lengths else 0
            max_body_size = getattr(self.server, "max_body_size", 1_048_576)

            if length > max_body_size:
                return self._reject_expectation(413, f"Request body exceeds the {max_body_size}-byte limit")

            if length and self.command != "POST":
                supported_bodyless = self.command in {"GET", "HEAD", "OPTIONS"}

                return self._reject_expectation(
                    400 if supported_bodyless else 405,
                    f"Request bodies are not supported for {self.command}",
                    allow=not supported_bodyless,
                )
        except _BadRequest as exc:
            return self._reject_expectation(400, str(exc))

        self.send_response_only(HTTPStatus.CONTINUE)
        self.end_headers()
        self._expect_continue_sent = True

        return True

    def _content_lengths(self) -> list[int]:
        """Parse Content-Length using the HTTP field-value grammar only."""
        raw_lengths = self.headers.get_all("Content-Length") or []
        values = [value.strip() for raw in raw_lengths for value in raw.split(",")]

        if any(not re.fullmatch(r"[0-9]+", value) for value in values):
            self.close_connection = True

            raise _BadRequest("Invalid Content-Length")

        lengths = [int(value) for value in values]

        if len(set(lengths)) > 1:
            self.close_connection = True

            raise _BadRequest("Conflicting Content-Length headers")

        return lengths

    def _has_declared_body(self) -> bool:
        self._reject_transfer_encoding()
        lengths = self._content_lengths()

        return bool(lengths and lengths[0] > 0)

    def _parse_body(self, body: bytes) -> tuple[dict, object]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].lower()

        if not body:
            return {}, None

        if content_type == "application/json":
            try:
                return {}, json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _BadRequest("Invalid JSON request body") from exc

        if content_type == "application/x-www-form-urlencoded":
            try:
                return self._parse_fields(body.decode("utf-8"), "form body"), None
            except UnicodeDecodeError as exc:
                raise _BadRequest("Form body must be UTF-8") from exc

        return {}, None

    def _parse_fields(self, value: str, source: str) -> dict:
        max_fields = getattr(self.server, "max_form_fields", 1_000)

        try:
            return self._flatten(
                parse_qs(value, keep_blank_values=True, max_num_fields=max_fields)
            )
        except ValueError as exc:
            raise _BadRequest(f"Request exceeds the {max_fields}-field limit for {source}") from exc

    def _new_context(self) -> TemplarContext:
        parsed_url = urlparse(self.path)
        path = parsed_url.path or "/"

        if self.command == "POST":
            body = self._read_body()
        elif self._has_declared_body():
            self.close_connection = True
            raise _BadRequest(f"Request bodies are not supported for {self.command}")
        else:
            body = b""

        form, json_data = self._parse_body(body)

        return TemplarContext(
            self,
            self.server,
            self.command,
            path,
            self._parse_fields(parsed_url.query, "query string"),
            dict(self.headers.items()),
            {},
            body=body,
            form=form,
            json_data=json_data,
        )

    def _send(self, ctx: TemplarContext, body: bytes | str | None = None) -> None:
        if body is not None:
            ctx.write(body)

        response_body = ctx._body

        try:
            self.server.middleware.run_after(ctx, response_body)
        except Exception:
            # After middleware (notably session persistence) still runs before headers are emitted. Do not acknowledge
            # a request whose state could not be durably saved.
            self.close_connection = True
            ctx.status = 500
            ctx.response_headers = {
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "no-store",
            }
            ctx._cookies.clear()
            response_body = b"<h1>500</h1><p>Internal Server Error</p>"

        self._apply_cors_headers(ctx)
        accepts_gzip = self._accepts_gzip()

        if (
            self._status_allows_body(ctx.status)
            and
            getattr(self.server, "gzip_enabled", False)
            and accepts_gzip
            and response_body
            and not ctx.has_header("Content-Encoding")
        ):
            response_body = gzip.compress(response_body)
            ctx.set_header("Content-Encoding", "gzip")
            ctx.add_vary("Accept-Encoding")

        if not self._status_allows_body(ctx.status):
            response_body = b""

        self._send_headers(ctx, len(response_body) if self._status_allows_body(ctx.status) else None)

        if self.command != "HEAD" and self._status_allows_body(ctx.status):
            self._write_response_bytes(response_body)

    def _write_response_bytes(self, data: bytes, deadline: float | None = None) -> None:
        """Send response bytes with a total deadline, not merely idle timeouts."""
        if not data:
            return

        # Headers are emitted through wfile; flush it before switching to the underlying socket for deadline-aware
        # sendall() body writes.
        self.wfile.flush()
        deadline = deadline or (time.monotonic() + float(getattr(self.server, "request_timeout", 30)))
        original_timeout = self.connection.gettimeout()

        try:
            for offset in range(0, len(data), 64 * 1024):
                remaining = deadline - time.monotonic()

                if remaining <= 0:
                    raise TimeoutError("Response exceeded the total write deadline")

                timeout = remaining if original_timeout is None else min(original_timeout, remaining)
                self.connection.settimeout(timeout)
                self.connection.sendall(data[offset:offset + 64 * 1024])
        finally:
            self.connection.settimeout(original_timeout)

    def _apply_cors_headers(self, ctx: TemplarContext) -> None:
        """Apply the server's public, non-credentialed CORS policy."""
        if not getattr(self.server, "cors_enabled", False):
            return

        ctx.set_header("Access-Control-Allow-Origin", "*")
        ctx.set_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        ctx.set_header("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token")
        # Wildcard CORS deliberately does not permit credentials. This keeps session cookies out of cross-origin requests.

    def _accepts_gzip(self) -> bool:
        """Honor HTTP Accept-Encoding tokens, including refusal via ``q=0``."""
        gzip_quality = None
        wildcard_quality = None

        for header in self.headers.get_all("Accept-Encoding") or []:
            for item in header.split(","):
                parts = [part.strip() for part in item.split(";")]
                coding = parts[0].lower() if parts else ""

                if not coding:
                    continue

                quality = 1.0

                for parameter in parts[1:]:
                    key, separator, value = parameter.partition("=")

                    if key.strip().lower() != "q" or not separator:
                        continue

                    try:
                        quality = float(value.strip())
                    except ValueError:
                        quality = 0.0
                if coding == "gzip":
                    gzip_quality = quality
                elif coding == "*":
                    wildcard_quality = quality

        quality = gzip_quality if gzip_quality is not None else wildcard_quality

        return quality is not None and quality > 0

    def _send_headers(self, ctx: TemplarContext, content_length: int | None, *, chunked: bool = False) -> None:
        """Emit response headers once middleware has finalized them."""
        try:
            ctx.validate_response_headers()
        except ValueError as exc:
            self.close_connection = True
            raise _InvalidResponseHeader(str(exc)) from exc

        self.send_response(ctx.status)

        for name, value in ctx.response_headers.items():
            self.send_header(name, value)

        if self.close_connection and not ctx.has_header("Connection"):
            self.send_header("Connection", "close")

        for value in ctx.cookie_headers():
            self.send_header("Set-Cookie", value)

        if not self._status_allows_body(ctx.status):
            content_length = None
            chunked = False

        if chunked:
            self.send_header("Transfer-Encoding", "chunked")
        elif content_length is not None:
            self.send_header("Content-Length", str(content_length))

        # Any later write failure must not enter the normal error responder: the socket may already contain a partial
        # HTTP response.
        self._response_committed = True
        self.end_headers()

    def _send_file(self, ctx: TemplarContext, file_path: Path, chunk_size: int = 64 * 1024) -> None:
        """Stream a static file without allocating its full contents in RAM.

        Static responses are intentionally marked as streaming and do not run
        response-body middleware: there is no safe complete body to hand to
        hooks without restoring the memory problem this path avoids.
        """
        ctx.is_streaming_response = True
        headers_sent = False
        write_deadline = time.monotonic() + float(getattr(self.server, "request_timeout", 30))

        try:
            self._apply_cors_headers(ctx)
            use_gzip = getattr(self.server, "gzip_enabled", False) and self._accepts_gzip()

            if use_gzip:
                ctx.set_header("Content-Encoding", "gzip")
                ctx.add_vary("Accept-Encoding")

                if self.command == "HEAD":
                    self._send_headers(ctx, self._gzip_file_size(file_path, chunk_size))
                else:
                    self._send_headers(ctx, None, chunked=True)
            else:
                self._send_headers(ctx, file_path.stat().st_size)

            headers_sent = True

            if self.command == "HEAD":
                return

            with file_path.open("rb") as static_file:
                if use_gzip:
                    chunked_writer = _ChunkedWriter(_DeadlineWriter(self, write_deadline))
                    self._write_gzip_stream(static_file, chunked_writer, chunk_size)
                    chunked_writer.finish()
                else:
                    while chunk := static_file.read(chunk_size):
                        self._write_response_bytes(chunk, write_deadline)
        except (OSError, TimeoutError):
            if not headers_sent:
                raise

            # Once headers have been emitted, another HTTP error response would corrupt the connection. Closing lets the
            # client detect the truncated transfer and keeps the handler's outer error path from writing a second response.
            self.close_connection = True
            self.server.logger.info("Static stream aborted after response headers were sent")

    @staticmethod
    def _write_gzip_stream(source, destination, chunk_size: int) -> None:
        """Write one deterministic gzip representation without buffering it."""
        with gzip.GzipFile(fileobj=destination, mode="wb", mtime=0) as compressed:
            while chunk := source.read(chunk_size):
                compressed.write(chunk)

    def _gzip_file_size(self, file_path: Path, chunk_size: int) -> int:
        """Count the exact streamed gzip representation for a HEAD response."""
        metadata = file_path.stat()
        fingerprint = (metadata.st_mtime_ns, metadata.st_size)
        cache = self.server._gzip_metadata_cache
        cache_key = str(file_path)

        with self.server._gzip_metadata_lock:
            cached = cache.get(cache_key)

            if cached is not None and cached[:2] == fingerprint:
                return cached[2]

            calculation_lock = self.server._gzip_metadata_file_locks.setdefault(
                cache_key, self.server._gzip_metadata_lock_factory()
            )

        # Only HEAD requests for the same file wait together. Other assets can calculate their metadata concurrently.
        with calculation_lock:
            cached_successfully = False

            try:
                metadata = file_path.stat()
                fingerprint = (metadata.st_mtime_ns, metadata.st_size)

                with self.server._gzip_metadata_lock:
                    cached = cache.get(cache_key)

                    if cached is not None and cached[:2] == fingerprint:
                        return cached[2]

                counter = _CountingWriter()

                with file_path.open("rb") as static_file:
                    self._write_gzip_stream(static_file, counter, chunk_size)

                with self.server._gzip_metadata_lock:
                    cache[cache_key] = (*fingerprint, counter.length)
                    self._prune_gzip_metadata_locked(cache_key)

                cached_successfully = True

                return counter.length
            finally:
                if not cached_successfully:
                    with self.server._gzip_metadata_lock:
                        if cache_key not in cache:
                            self.server._gzip_metadata_file_locks.pop(cache_key, None)

    def _prune_gzip_metadata_locked(self, current_key: str) -> None:
        """Bound server-wide gzip metadata and remove deleted static assets."""
        cache = self.server._gzip_metadata_cache
        locks = self.server._gzip_metadata_file_locks

        for key in list(cache):
            if key != current_key and not Path(key).is_file():
                cache.pop(key, None)
                locks.pop(key, None)

        max_entries = self.server.gzip_metadata_max_entries

        while len(cache) > max_entries:
            stale_key = next(iter(cache))

            if stale_key == current_key and len(cache) > 1:
                stale_key = next(key for key in cache if key != current_key)

            cache.pop(stale_key, None)
            locks.pop(stale_key, None)

    def _error(self, ctx: TemplarContext, status: int, message: str) -> None:
        ctx.set_status(status)
        ctx.set_header("Content-Type", "text/html; charset=utf-8")
        self._send(ctx, f"<h1>{status}</h1><p>{html.escape(message)}</p>")

    @staticmethod
    def _prepare_safe_error(ctx: TemplarContext) -> None:
        """Discard the application response state before serializing an error."""
        ctx.response_headers = {
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "no-store",
        }
        ctx._cookies.clear()

    def _serve_static_file(self, ctx: TemplarContext, requested_path: str, root: Path | None = None) -> bool:
        file_root = (root or self.server.static_dir).resolve()
        file_path = (file_root / requested_path).resolve()

        if (file_path != file_root and file_root not in file_path.parents) or not file_path.is_file():
            self._error(ctx, 404, "Static file not found")

            return False

        ctx.set_header("Content-Type", mimetypes.guess_type(str(file_path))[0] or "application/octet-stream")
        ctx.set_header("Cache-Control", "public, max-age=31536000" if self.server.mode == "prod" else "no-cache")
        ctx.is_static_response = True
        self._send_file(ctx, file_path)

        return True

    def _handle_sse(self, ctx: TemplarContext, template_name: str, logs: list) -> None:
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.wfile.write(b": connected\n\nretry: 1000\n\n")
            self.wfile.flush()
            last_mtime = self.server.renderer.get_file_mtime(template_name)
            last_heartbeat = time.monotonic()

            while True:
                time.sleep(1)
                new_mtime = self.server.renderer.get_file_mtime(template_name)

                if new_mtime > last_mtime:
                    last_mtime = new_mtime
                    self.wfile.write(b"data: reload\n\n")
                    self.wfile.flush()
                    logs.append(f"[SSE] Reload triggered for template: {template_name}")
                elif time.monotonic() - last_heartbeat >= self.server.sse_heartbeat_seconds:
                    # A browser close is only observed when the socket is written to. Heartbeats ensure idle disconnected
                    # clients cannot leave a handler thread running forever.
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    last_heartbeat = time.monotonic()
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            logs.append("SSE client disconnected")

    def _handle_template_request(self, ctx: TemplarContext) -> None:
        template_name, route_params = self.server.router.match(ctx.path)

        if not template_name:
            candidate = ctx.path.lstrip("/")
            template_file = self.server.templates_dir / f"{candidate}.templar.py"
            template_name = self.server.default_route if ctx.path == "/" else candidate

            if ctx.path != "/" and not template_file.is_file():
                self._error(ctx, 404, "Not Found")

                return

        ctx.route_params = route_params
        context = {
            **ctx.query,
            **route_params,
            "request": ctx,
            "session": ctx.session,
            "form": ctx.form,
            "json": ctx.json,
            "user": ctx.user,
        }
        html = self.server.renderer.render_template(
            template_name,
            debug=self.server.mode == "dev",
            **context,
        )

        # Dynamic templates can render session/user-specific content. They are private by default; applications explicitly
        # opt into public caching.
        if not ctx.has_header("Cache-Control"):
            ctx.set_header("Cache-Control", "no-cache" if self.server.mode == "dev" else "private, no-store")

        self._send(ctx, html)

    def _handle(self) -> None:
        self._log_buffer = []
        request_logs: list = []
        renderer_template = None

        with db.use(self.server.database):
            try:
                ctx = self._new_context()

                if not self._host_is_allowed(ctx):
                    self._error(ctx, 400, "Host is not allowed")

                    return

                # Queries frequently contain reset links, signed URLs, or API credentials. Keep both file and development
                # console logs to the path; application code can opt into safe structured logs.
                request_logs.append(f"[Request] {ctx.method} {ctx.path}")
                early_response = self.server.middleware.run_before(ctx)

                if early_response is not None:
                    self._send(ctx, early_response)

                    return

                if ctx.path.startswith("/static/"):
                    self._serve_static_file(ctx, ctx.path.removeprefix("/static/"))

                    return

                if ctx.path == "/favicon.ico":
                    self._serve_static_file(ctx, "favicon.ico", self.server.templates_dir.parent)

                    return

                if self.command == "GET" and self.server.mode == "dev" and ctx.path == "/__templar_hot_reload__":
                    template_name = str(ctx.query.get("template", self.server.default_route)).replace(".templar.py", "").replace(".templar", "")
                    self._handle_sse(ctx, template_name or self.server.default_route, request_logs)

                    return

                self._handle_template_request(ctx)
                renderer_template = self.server.default_route if ctx.path == "/" else ctx.path.lstrip("/")
                request_logs.append(f"[Response] Served template: {renderer_template}")
            except _InvalidResponseHeader as exc:
                if self._response_committed:
                    self._abort_committed_response("Unsafe response header rejected after response commitment")

                    return

                self.server.logger.warning("Unsafe response header rejected: %s", exc)
                ctx = locals().get("ctx") or TemplarContext(self, self.server, self.command, self.path, {}, dict(self.headers.items()), {})
                self._prepare_safe_error(ctx)
                self._error(ctx, 500, "Internal Server Error")
            except OverflowError as exc:
                if self._response_committed:
                    self._abort_committed_response("Request body error after response commitment")

                    return

                self.server.logger.warning("Request body rejected: %s", exc)
                ctx = locals().get("ctx") or TemplarContext(self, self.server, self.command, self.path, {}, dict(self.headers.items()), {})
                self._error(ctx, 413, str(exc))
            except TimeoutError:
                if self._response_committed:
                    self._abort_committed_response("Request timed out after response commitment")

                    return

                self.server.logger.warning("Request timed out")
                self.close_connection = True
                ctx = locals().get("ctx") or TemplarContext(self, self.server, self.command, self.path, {}, dict(self.headers.items()), {})
                self._error(ctx, 408, "Request timed out")
            except _BadRequest as exc:
                if self._response_committed:
                    self._abort_committed_response("Invalid request after response commitment")

                    return

                self.server.logger.warning("Invalid request: %s", exc)
                ctx = locals().get("ctx") or TemplarContext(self, self.server, self.command, self.path, {}, dict(self.headers.items()), {})
                self._error(ctx, 400, str(exc))
            except Exception:
                if self._response_committed:
                    self._abort_committed_response("Response stream aborted after headers were sent")

                    return

                self.server.log_exception("Unhandled request error")
                ctx = locals().get("ctx") or TemplarContext(self, self.server, self.command, self.path, {}, dict(self.headers.items()), {})
                self._prepare_safe_error(ctx)
                self._error(ctx, 500, "Internal Server Error")
            finally:
                self.server.handle_request_logs({"http": self._log_buffer, "request": request_logs, "renderer_template": renderer_template})

    def _abort_committed_response(self, message: str) -> None:
        """Stop a failed response without emitting a second HTTP message."""
        self.close_connection = True
        self.server.logger.info(message)

    def do_GET(self) -> None:
        self._response_committed = False
        self._handle()

    def do_POST(self) -> None:
        self._response_committed = False
        self._handle()

    def do_HEAD(self) -> None:
        self._response_committed = False
        self._handle()

    def _method_not_allowed(self) -> None:
        # The body is deliberately not read for unsupported methods. Closing the persistent connection prevents it being
        # interpreted as the next request.
        self.close_connection = True
        ctx = TemplarContext(self, self.server, self.command, self.path, {}, dict(self.headers.items()), {})
        ctx.set_header("Allow", "GET, POST, HEAD")
        ctx.set_header("Connection", "close")
        self._error(ctx, 405, "Method Not Allowed")

    def do_PUT(self) -> None:
        self._response_committed = False
        self._method_not_allowed()

    def do_DELETE(self) -> None:
        self._response_committed = False
        self._method_not_allowed()

    def do_PATCH(self) -> None:
        self._response_committed = False
        self._method_not_allowed()

    def do_OPTIONS(self) -> None:
        self._response_committed = False
        ctx = TemplarContext(self, self.server, self.command, self.path, {}, dict(self.headers.items()), {})

        try:
            # OPTIONS is bodyless in Templar's HTTP contract. Never leave a declared body in the HTTP/1.1 input buffer
            # where it could be interpreted as a following request.
            if self._has_declared_body():
                self.close_connection = True
                ctx.set_header("Connection", "close")
                self._error(ctx, 400, "Request bodies are not supported for OPTIONS")

                return
        except _BadRequest as exc:
            self.close_connection = True
            ctx.set_header("Connection", "close")
            self._error(ctx, 400, str(exc))

            return

        if getattr(self.server, "cors_enabled", False):
            if not self._host_is_allowed(ctx):
                self._error(ctx, 400, "Host is not allowed")

                return

            ctx.set_status(204)
            self._send(ctx)

            return

        self._method_not_allowed()

    def _host_is_allowed(self, ctx: TemplarContext) -> bool:
        return self._request_host_is_allowed()

    def _request_host_is_allowed(self) -> bool:
        host = self._request_host()

        if host is None:
            # Host ambiguity is a framing/routing error. Do not reuse this HTTP/1.1 connection after rejecting it.
            self.close_connection = True

            return False

        allowed_hosts = getattr(self.server, "allowed_hosts", []) or []

        if not allowed_hosts or "*" in allowed_hosts:
            return True

        return host in {str(item).lower() for item in allowed_hosts}

    def _request_host(self) -> str | None:
        """Return one strictly valid Host value, rejecting ambiguity."""
        hosts = self.headers.get_all("Host") or []

        if len(hosts) != 1:
            return None

        value = hosts[0].strip()

        if not value or any(character.isspace() for character in value):
            return None

        if value.startswith("["):
            match = re.fullmatch(r"\[([0-9A-Fa-f:.]+)\](?::([0-9]+))?", value)

            if not match:
                return None

            try:
                parsed = ipaddress.ip_address(match.group(1))
            except ValueError:
                return None

            if parsed.version != 6:
                return None

            port = match.group(2)
            host = str(parsed)
        else:
            if value.count(":") > 1:
                return None

            host, separator, raw_port = value.partition(":")
            port = raw_port if separator else None

            if not re.fullmatch(
                r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
                r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?",
                host,
            ):
                return None

            if separator and not port:
                return None

            host = host.lower()

        if port is not None and (not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65_535):
            return None

        return host
