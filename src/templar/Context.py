import re
import sys
from http import cookies
from typing import Any, Dict, Optional

sys.dont_write_bytecode = True

_HEADER_NAME = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")

class TemplarContext:
    """
    Encapsulates request/response state and useful helpers.
    Created early in RequestHandler.do_* and passed to middleware/renderer.
    """

    def __init__(
        self,
        handler,
        server,
        method: str,
        path: str,
        query: Dict[str, Any],
        headers: Dict[str, str],
        route_params: Dict[str, str],
        body: bytes = b"",
        form: Optional[Dict[str, Any]] = None,
        json_data: Any = None,
    ):
        self.handler = handler
        self.server = server
        self.method = method
        self.path = path
        self.query = query or {}
        self.route_params = route_params or {}
        self.headers = headers or {}
        self.body = body
        self.form = form or {}
        self.json = json_data
        self.status = 200
        self.response_headers = {"Content-Type": "text/html; charset=utf-8"}
        self._body: bytes = b""
        self.user = None
        self.session = {}
        self.csrf_token = None
        self._cookies = cookies.SimpleCookie()

    # response helpers
    def set_header(self, name: str, value: str) -> None:
        self._validate_header(name, value)
        # Header field names are case-insensitive. Replace an application header set with a different case instead of
        # serializing duplicates.
        for existing_name in list(self.response_headers):
            if existing_name.lower() == name.lower():
                del self.response_headers[existing_name]

        self.response_headers[name] = value

    def has_header(self, name: str) -> bool:
        return any(existing_name.lower() == name.lower() for existing_name in self.response_headers)

    def get_header(self, name: str, default: Any = None) -> Any:
        for existing_name, value in self.response_headers.items():
            if existing_name.lower() == name.lower():
                return value

        return default

    def add_vary(self, *tokens: str) -> None:
        """Merge case-insensitive Vary tokens without discarding app policy."""
        existing = self.get_header("Vary", "")
        values = [token.strip() for token in str(existing).split(",") if token.strip()]
        seen = {token.lower() for token in values}

        for token in tokens:
            if token.lower() not in seen:
                values.append(token)
                seen.add(token.lower())

        self.set_header("Vary", ", ".join(values))

    @staticmethod
    def _validate_header(name: str, value: str) -> None:
        """Reject response-splitting characters before HTTP serialization."""
        if not isinstance(name, str) or not _HEADER_NAME.fullmatch(name):
            raise ValueError(f"Invalid HTTP response header name: {name!r}")

        if not isinstance(value, str) or "\r" in value or "\n" in value:
            raise ValueError(f"Invalid HTTP response header value for {name!r}")

    def validate_response_headers(self) -> None:
        """Defend against direct mutation of ``response_headers`` by apps."""
        normalized = {}
        names_by_casefold = {}

        for name, value in self.response_headers.items():
            self._validate_header(name, value)
            key = name.lower()
            # Direct dictionary mutation bypasses set_header(). Keep its last assignment, matching normal dictionary
            # semantics, but serialize one field for each case-insensitive HTTP header name.
            previous_name = names_by_casefold.get(key)

            if previous_name is not None:
                del normalized[previous_name]

            normalized[name] = value
            names_by_casefold[key] = name

        self.response_headers = normalized

    def set_status(self, status_code: int) -> None:
        self.status = status_code

    def write(self, data: bytes | str) -> None:
        self._body += data.encode("utf-8") if isinstance(data, str) else data

    def cookie(self, name: str, value: str, **opts) -> None:
        self._cookies[name] = value

        for k, v in opts.items():
            if v is True:
                self._cookies[name][k] = True
            else:
                self._cookies[name][k] = str(v)

    def cookie_headers(self) -> list[str]:
        return [morsel.OutputString() for morsel in self._cookies.values()]
