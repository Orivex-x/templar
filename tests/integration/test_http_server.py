import http.client
import gzip
import socket
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from templar.auth import Auth, PasswordManager
from templar.TemplarServer import TemplarServer
from templar.cli.CliOutput import CliOutput
from templar.middleware.MiddlewareManager import MiddlewareManager


@pytest.fixture
def running_server(sample_config, temp_project_dir):
    (temp_project_dir / "templates" / "echo.templar.py").write_text(
        "from templar.core.elements.Div import Div\n"
        "def render(request, form, json, session, **context):\n"
        "    value = form.get('name') or (json or {}).get('name') or context.get('id') or request.query.get('name', '')\n"
        "    return Div(f'{request.method}:{value}:{bool(session.get(\"_sid\"))}')\n"
    )
    (temp_project_dir / "templates" / "broken.templar.py").write_text(
        "def render(**context):\n    raise RuntimeError('boom')\n"
    )
    (temp_project_dir / "templates" / "value_error.templar.py").write_text(
        "def render(request, **context):\n"
        "    raise ValueError(request.query.get('message', 'boom'))\n"
    )
    (temp_project_dir / "static" / "hello.txt").write_text("hello static")

    sample_config.set("port", 0)

    # Individual HTTP contract tests do not submit browser forms. CSRF has dedicated middleware coverage below.
    sample_config.override("csrf_enabled", False)
    middleware = MiddlewareManager()
    server = TemplarServer(
        config=sample_config,
        output=CliOutput(),
        templates_dir=temp_project_dir / "templates",
        themes_dir=temp_project_dir / "themes",
        static_dir=temp_project_dir / "static",
        middleware=middleware,
    )

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield server, middleware
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def request(server, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection(*server.server_address, timeout=2)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    payload = response.read().decode("utf-8")
    result = response.status, dict(response.getheaders()), payload
    connection.close()

    return result


@pytest.mark.integration
def test_get_post_and_request_context(running_server):
    server, _ = running_server
    status, headers, body = request(server, "GET", "/echo?name=Ada")

    assert status == 200
    assert "GET:Ada:False" in body
    assert "Set-Cookie" not in headers

    status, _, body = request(
        server,
        "POST",
        "/echo",
        body="name=Grace",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert status == 200
    assert "POST:Grace:False" in body


@pytest.mark.integration
def test_template_orm_access_uses_its_own_server_database(running_server, temp_project_dir):
    server, _ = running_server
    server.database.execute("CREATE TABLE scoped_server_data (value TEXT)")
    server.database.execute("INSERT INTO scoped_server_data (value) VALUES ('server-owned')")
    (temp_project_dir / "templates" / "database.templar.py").write_text(
        "from templar.db import db\n"
        "from templar.core.elements.Div import Div\n"
        "def render(**context):\n"
        "    return Div(db.fetchone('SELECT value FROM scoped_server_data')['value'])\n",
        encoding="utf-8",
    )

    status, _, body = request(server, "GET", "/database")

    assert status == 200
    assert "server-owned" in body


@pytest.mark.integration
def test_json_errors_static_containment_and_template_errors(running_server):
    server, _ = running_server
    status, _, body = request(server, "POST", "/echo", body="{", headers={"Content-Type": "application/json"})

    assert status == 400
    assert "Invalid JSON request body" in body

    status, _, body = request(server, "GET", "/static/hello.txt")

    assert status == 200
    assert body == "hello static"

    status, _, _ = request(server, "GET", "/static/../templar.config.yml")

    assert status == 404

    status, _, body = request(server, "GET", "/broken")

    assert status == 500
    assert "boom" not in body

    status, _, body = request(server, "GET", "/value_error?message=%3Cscript%3Ealert(1)%3C/script%3E")

    assert status == 500
    assert "<script>" not in body
    assert "Internal Server Error" in body


def test_generic_errors_discard_application_headers_and_cookies(running_server):
    server, middleware = running_server

    def unsafe_state(ctx):
        if ctx.path == "/value_error":
            ctx.set_header("Cache-Control", "public, max-age=3600")
            ctx.cookie("application_state", "stale")

    middleware.add_before(unsafe_state)
    status, headers, _ = request(server, "GET", "/value_error?message=boom")

    assert status == 500
    assert headers["Cache-Control"] == "no-store"
    assert "Set-Cookie" not in headers

    status, headers, _ = request(server, "PUT", "/echo")

    assert status == 405
    assert headers["Allow"] == "GET, POST, HEAD"
    assert headers["Connection"] == "close"


@pytest.mark.parametrize("method", ("TRACE", "CONNECT", "PROPFIND"))
def test_every_unsupported_method_closes_before_its_body_can_desynchronize(running_server, method):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            f"{method} /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: 4\r\n\r\nGET ".encode("ascii")
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 405 " in response
    assert b"Connection: close" in response


def test_overlong_request_lines_are_rejected_and_connection_is_closed(running_server):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(b"GET /" + b"a" * 65_536 + b" HTTP/1.1\r\nHost: localhost\r\n\r\n")
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 414 " in response
    assert b"Connection: close" in response


@pytest.mark.integration
def test_route_params_cannot_be_overridden_by_query_values(running_server):
    server, _ = running_server
    server.router.add("/users/<id>", "echo")

    status, _, body = request(server, "GET", "/users/42?id=99")

    assert status == 200
    assert "GET:42:False" in body


@pytest.mark.integration
def test_chunked_requests_are_rejected_and_connection_is_closed(running_server):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n"
            b"4\r\ntest\r\n0\r\n\r\n"
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 400 " in response


@pytest.mark.integration
def test_identity_transfer_encoding_is_rejected_and_connection_is_closed(running_server):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: identity\r\nContent-Length: 4\r\n\r\ntest"
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 400 " in response
    assert b"Connection: close" in response


@pytest.mark.parametrize("transfer_encoding", (b"", b","))
def test_empty_or_malformed_transfer_encoding_is_rejected_and_connection_is_closed(running_server, transfer_encoding):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: "
            + transfer_encoding
            + b"\r\nContent-Length: 4\r\n\r\ntest"
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 400 " in response
    assert b"Connection: close" in response


@pytest.mark.parametrize("content_length", (b"+4", b"1_0", b"\xd9\xa1"))
def test_non_http_content_length_syntax_is_rejected_and_connection_is_closed(running_server, content_length):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: "
            + content_length
            + b"\r\n\r\ntest"
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 400 " in response
    assert b"Connection: close" in response


def test_duplicate_or_malformed_host_headers_are_rejected(running_server):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"GET /echo HTTP/1.1\r\nHost: localhost\r\nHost: localhost\r\n\r\n"
        )
        response = connection.recv(4096)
    finally:
        connection.close()
    assert b" 400 " in response

    server.allowed_hosts = ["::1"]
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(b"GET /echo HTTP/1.1\r\nHost: [::1]invalid\r\n\r\n")
        response = connection.recv(4096)
    finally:
        connection.close()
    assert b" 400 " in response


def test_query_and_form_field_counts_are_limited(running_server):
    server, _ = running_server
    server.max_form_fields = 2

    status, _, body = request(server, "GET", "/echo?one=1&two=2&three=3")

    assert status == 400
    assert "field limit" in body

    status, _, body = request(
        server,
        "POST",
        "/echo",
        body="one=1&two=2&three=3",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert status == 400
    assert "field limit" in body


def test_directly_mutated_response_headers_are_validated_before_serialization(running_server):
    server, middleware = running_server

    def inject_header(ctx):
        if ctx.path == "/echo":
            ctx.response_headers["X-Test"] = "safe\r\nInjected: true"

    middleware.add_before(inject_header)
    status, headers, body = request(server, "GET", "/echo")

    assert status == 500
    assert "Injected" not in headers
    assert "Internal Server Error" in body


@pytest.mark.integration
def test_allowed_hosts_cors_and_gzip_settings(running_server):
    server, _ = running_server
    server.gzip_enabled = True

    status, _, _ = request(server, "GET", "/echo", headers={"Host": "not-allowed.example"})

    assert status == 400

    connection = http.client.HTTPConnection(*server.server_address, timeout=2)
    connection.request("GET", "/echo", headers={"Accept-Encoding": "gzip"})
    response = connection.getresponse()
    payload = response.read()
    headers = dict(response.getheaders())
    connection.close()

    assert response.status == 200
    assert headers["Content-Encoding"] == "gzip"
    assert "GET:" in gzip.decompress(payload).decode("utf-8")
    assert headers["Access-Control-Allow-Origin"] == "*"

    status, headers, body = request(server, "OPTIONS", "/echo")

    assert status == 204
    assert body == ""
    assert headers["Access-Control-Allow-Methods"] == "GET, POST, HEAD, OPTIONS"
    assert "Content-Length" not in headers

    status, headers, body = request(server, "GET", "/static/hello.txt")

    assert status == 200
    assert body == "hello static"
    assert headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.integration
def test_gzip_negotiation_honors_a_zero_quality_value(running_server):
    server, _ = running_server
    server.gzip_enabled = True

    status, headers, body = request(server, "GET", "/echo", headers={"Accept-Encoding": "gzip;q=0"})

    assert status == 200
    assert "Content-Encoding" not in headers
    assert "GET:" in body

    status, headers, body = request(server, "GET", "/static/hello.txt", headers={"Accept-Encoding": "br, gzip;q=0"})

    assert status == 200
    assert "Content-Encoding" not in headers
    assert body == "hello static"


def test_response_headers_are_case_insensitive_and_vary_is_merged(running_server):
    server, middleware = running_server
    server.gzip_enabled = True
    server.router.add("/preencoded", "echo")

    def application_headers(ctx):
        if ctx.path == "/preencoded":
            # Direct mapping mutation is a supported defensive-validation path, so it must receive the same
            # case-insensitive treatment.
            ctx.response_headers["content-encoding"] = "identity"

        if ctx.path == "/echo":
            ctx.response_headers["vary"] = "Origin"

    middleware.add_before(application_headers)
    status, headers, body = request(server, "GET", "/preencoded", headers={"Accept-Encoding": "gzip"})

    assert status == 200
    assert headers["content-encoding"] == "identity"
    assert "GET:" in body

    connection = http.client.HTTPConnection(*server.server_address, timeout=2)
    connection.request("GET", "/echo", headers={"Accept-Encoding": "gzip"})
    response = connection.getresponse()
    payload = response.read()
    headers = dict(response.getheaders())
    connection.close()

    assert response.status == 200
    assert gzip.decompress(payload)
    assert {token.strip().lower() for token in headers["Vary"].split(",")} == {"origin", "accept-encoding"}


@pytest.mark.integration
def test_static_assets_stream_without_refreshing_an_existing_session(running_server, monkeypatch):
    server, middleware = running_server

    def create_session(ctx):
        if ctx.path == "/login":
            ctx.session["user_id"] = 7

    middleware.add_before(create_session)
    _, login_headers, _ = request(server, "GET", "/login")
    session_cookie = login_headers["Set-Cookie"].split(";", 1)[0]

    def static_after_middleware_must_not_receive_a_fake_body(_ctx, _body):
        raise AssertionError("after middleware must not run for streaming static responses")

    middleware.add_after(static_after_middleware_must_not_receive_a_fake_body)

    def read_bytes_is_not_allowed(_path):
        raise AssertionError("static files must be streamed")

    monkeypatch.setattr(Path, "read_bytes", read_bytes_is_not_allowed)
    status, headers, body = request(server, "GET", "/static/hello.txt", headers={"Cookie": session_cookie})

    assert status == 200
    assert body == "hello static"
    assert "Set-Cookie" not in headers


@pytest.mark.integration
def test_static_assets_support_streaming_gzip(running_server):
    server, _ = running_server
    server.gzip_enabled = True

    connection = http.client.HTTPConnection(*server.server_address, timeout=2)
    connection.request("GET", "/static/hello.txt", headers={"Accept-Encoding": "gzip"})
    response = connection.getresponse()
    payload = response.read()
    headers = dict(response.getheaders())
    connection.close()

    assert response.status == 200
    assert headers["Content-Encoding"] == "gzip"
    assert headers["Transfer-Encoding"] == "chunked"
    assert headers["Vary"] == "Accept-Encoding"
    assert gzip.decompress(payload) == b"hello static"


def test_gzip_static_head_reports_the_selected_representation_length(running_server):
    server, _ = running_server
    server.gzip_enabled = True

    get_connection = http.client.HTTPConnection(*server.server_address, timeout=2)
    get_connection.request("GET", "/static/hello.txt", headers={"Accept-Encoding": "gzip"})
    get_response = get_connection.getresponse()
    compressed_payload = get_response.read()
    get_connection.close()

    head_connection = http.client.HTTPConnection(*server.server_address, timeout=2)
    head_connection.request("HEAD", "/static/hello.txt", headers={"Accept-Encoding": "gzip"})
    head_response = head_connection.getresponse()
    headers = dict(head_response.getheaders())

    assert head_response.read() == b""

    head_connection.close()

    assert head_response.status == 200
    assert headers["Content-Encoding"] == "gzip"
    assert "Transfer-Encoding" not in headers
    assert int(headers["Content-Length"]) == len(compressed_payload)


@pytest.mark.integration
def test_static_stream_abort_closes_without_sending_a_second_response(running_server, monkeypatch):
    server, _ = running_server
    original_open = Path.open

    def interrupted_open(path, *args, **kwargs):
        if path.name == "hello.txt" and args and args[0] == "rb":
            raise OSError("simulated static-file failure")

        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", interrupted_open)
    connection = http.client.HTTPConnection(*server.server_address, timeout=2)

    try:
        connection.request("GET", "/static/hello.txt")
        response = connection.getresponse()

        assert response.status == 200

        with pytest.raises(http.client.IncompleteRead) as interrupted:
            response.read()

        assert b"500" not in interrupted.value.partial
    finally:
        connection.close()

    monkeypatch.setattr(Path, "open", original_open)
    status, _, _ = request(server, "GET", "/echo")

    assert status == 200


@pytest.mark.integration
def test_cors_options_with_a_declared_body_is_rejected_and_closed(running_server):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"OPTIONS /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: 4\r\n\r\n"
            b"GET "
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 400 " in response
    assert b"Connection: close" in response


def test_expect_continue_rejects_invalid_framing_and_oversized_bodies_before_100(running_server):
    server, _ = running_server
    server.max_body_size = 3
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\nExpect: 100-continue\r\nContent-Length: 4\r\n\r\n"
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 413 " in response
    assert b"100 Continue" not in response
    assert b"Connection: close" in response


@pytest.mark.parametrize(("method", "expected_status"), (("GET", b" 400 "), ("TRACE", b" 405 ")))
def test_expect_continue_rejects_bodies_for_non_post_methods_before_100(running_server, method, expected_status):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            f"{method} /echo HTTP/1.1\r\nHost: localhost\r\nExpect: 100-continue\r\nContent-Length: 1\r\n\r\n".encode("ascii")
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert expected_status in response
    assert b"100 Continue" not in response
    assert b"Connection: close" in response


def test_expect_continue_with_optional_whitespace_receives_an_interim_response(running_server):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\nExpect: 100-continue \r\n"
            b"Content-Length: 1\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\n"
        )
        interim = connection.recv(4096)
        connection.sendall(b"x")
        final = connection.recv(4096)
    finally:
        connection.close()

    assert b"100 Continue" in interim
    assert b" 200 " in final


def test_disallowed_host_is_rejected_before_expect_continue(running_server):
    server, _ = running_server
    server.allowed_hosts = ["localhost"]
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"POST /echo HTTP/1.1\r\nHost: disallowed.example\r\nExpect: 100-continue\r\n"
            b"Content-Length: 1\r\n\r\n"
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 400 " in response
    assert b"100 Continue" not in response
    assert b"Connection: close" in response


def test_request_body_has_a_total_deadline_even_when_bytes_arrive(running_server):
    server, _ = running_server
    server.request_timeout = 0.1
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(b"POST /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: 2\r\n\r\na")
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 408 " in response
    assert b"Connection: close" in response


@pytest.mark.parametrize("expect", ("upload-token", "100-continue, custom-token"))
def test_unsupported_expectations_are_rejected(expect, running_server):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            f"POST /echo HTTP/1.1\r\nHost: localhost\r\nExpect: {expect}\r\nContent-Length: 1\r\n\r\n".encode("ascii")
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 417 " in response
    assert b"100 Continue" not in response
    assert b"Connection: close" in response


@pytest.mark.integration
def test_configured_certificate_and_key_enable_tls(sample_config, temp_project_dir):
    sample_config.override("port", 0)
    sample_config.override("ssl_cert_path", "/cert.pem")
    sample_config.override("ssl_key_path", "/key.pem")

    with patch("templar.TemplarServer.ssl.create_default_context") as create_context:
        context = create_context.return_value
        context.wrap_socket.side_effect = lambda sock, **_kwargs: sock
        server = TemplarServer(
            config=sample_config,
            output=CliOutput(),
            templates_dir=temp_project_dir / "templates",
            themes_dir=temp_project_dir / "themes",
            static_dir=temp_project_dir / "static",
        )

        try:
            context.load_cert_chain.assert_called_once_with(certfile="/cert.pem", keyfile="/key.pem")

            assert server.tls_enabled is True
        finally:
            server.server_close()


@pytest.mark.integration
def test_failed_socket_bind_closes_database_and_log_handlers(sample_config, temp_project_dir, monkeypatch):
    captured = {}

    def fail_bind(instance, *_args, **_kwargs):
        captured["server"] = instance

        raise OSError("address already in use")

    monkeypatch.setattr("templar.TemplarServer.ThreadingHTTPServer.__init__", fail_bind)

    with pytest.raises(OSError, match="address already in use"):
        TemplarServer(
            config=sample_config,
            output=CliOutput(),
            templates_dir=temp_project_dir / "templates",
            themes_dir=temp_project_dir / "themes",
            static_dir=temp_project_dir / "static",
        )

    failed_server = captured["server"]

    assert failed_server.database._connected is False
    assert failed_server.logger.handlers == []


@pytest.mark.integration
def test_one_server_middleware_registry_handles_early_and_after_hooks(running_server):
    server, middleware = running_server

    def before(ctx):
        if ctx.path == "/blocked":
            return "blocked"

    def after(ctx, _body):
        ctx.set_header("X-Templar-Middleware", "active")

    middleware.add_before(before)
    middleware.add_after(after)
    status, headers, _ = request(server, "GET", "/echo")

    assert status == 200
    assert headers["X-Templar-Middleware"] == "active"

    status, headers, body = request(server, "GET", "/blocked")

    assert status == 200
    assert body == "blocked"
    assert headers["X-Templar-Middleware"] == "active"


@pytest.mark.integration
def test_registered_user_loader_attaches_the_session_user(running_server, temp_project_dir):
    server, middleware = running_server
    (temp_project_dir / "templates" / "whoami.templar.py").write_text(
        "from templar.core.elements.Div import Div\n"
        "def render(user, **context):\n"
        "    return Div(user['name'] if user else 'anonymous')\n"
    )
    server.set_user_loader(lambda user_id: {"id": user_id, "name": "Ada"} if user_id == 7 else None)

    def log_in(ctx):
        if ctx.path == "/login":
            ctx.session["user_id"] = 7

    middleware.add_before(log_in)
    _, headers, _ = request(server, "GET", "/login")
    session_cookie = headers["Set-Cookie"].split(";", 1)[0]

    status, _, body = request(server, "GET", "/whoami", headers={"Cookie": session_cookie})

    assert status == 200
    assert "Ada" in body


@pytest.mark.integration
def test_login_rotates_an_existing_session_id(running_server):
    server, middleware = running_server
    auth = Auth("test-secret")
    password_hash = PasswordManager.hash_password("correct horse", iterations=PasswordManager.MIN_ITERATIONS)
    server.set_user_loader(lambda user_id: {"id": user_id, "name": "Ada"} if user_id == 7 else None)

    def establish_anonymous_session(ctx):
        if ctx.path == "/cart":
            ctx.session["cart"] = "item"

    def log_in(ctx):
        if ctx.path == "/login":
            assert auth.authenticate(
                "ada",
                "correct horse",
                lambda username: {"id": 7, "password_hash": password_hash} if username == "ada" else None,
                session=ctx.session,
            )

    middleware.add_before(establish_anonymous_session)
    middleware.add_before(log_in)
    _, headers, _ = request(server, "GET", "/cart")
    before_login = headers["Set-Cookie"].split(";", 1)[0]

    _, headers, _ = request(server, "GET", "/login", headers={"Cookie": before_login})
    after_login = headers["Set-Cookie"].split(";", 1)[0]

    assert after_login != before_login


@pytest.mark.integration
def test_body_on_unsupported_method_closes_the_connection(running_server):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"PUT /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: 4\r\n\r\n"
            b"bodyGET /echo HTTP/1.1\r\nHost: localhost\r\n\r\n"
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 405 " in response
    assert b"Connection: close" in response


@pytest.mark.integration
def test_conflicting_content_lengths_are_rejected(running_server):
    server, _ = running_server
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 1\r\nContent-Length: 2\r\n\r\na"
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 400 " in response


@pytest.mark.integration
def test_invalid_or_oversized_body_framing_closes_the_connection(running_server):
    server, _ = running_server

    for content_length, expected_status in ((b"invalid", b" 400 "), (b"999999999", b" 413 ")):
        connection = socket.create_connection(server.server_address, timeout=2)

        try:
            connection.sendall(
                b"POST /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: "
                + content_length
                + b"\r\n\r\nGET /echo HTTP/1.1\r\nHost: localhost\r\n\r\n"
            )
            response = connection.recv(4096)
        finally:
            connection.close()

        assert expected_status in response
        assert b"Connection: close" in response


@pytest.mark.integration
def test_incomplete_request_body_times_out_and_releases_the_connection(running_server):
    server, _ = running_server
    server.request_timeout = 0.05
    connection = socket.create_connection(server.server_address, timeout=2)

    try:
        connection.sendall(
            b"POST /echo HTTP/1.1\r\nHost: localhost\r\nContent-Length: 4\r\n\r\na"
        )
        response = connection.recv(4096)
    finally:
        connection.close()

    assert b" 408 " in response
    assert b"Connection: close" in response


@pytest.mark.integration
def test_worker_limit_rejects_excess_connections_without_blocking_shutdown(running_server):
    server, _ = running_server
    server._worker_slots = threading.BoundedSemaphore(1)
    occupied = socket.create_connection(server.server_address, timeout=2)

    try:
        # The first handler waits for a request line and owns the only slot.
        threading.Event().wait(0.05)
        overloaded = socket.create_connection(server.server_address, timeout=2)

        try:
            overloaded.sendall(b"GET /echo HTTP/1.1\r\nHost: localhost\r\n\r\n")
            response = overloaded.recv(4096)
        finally:
            overloaded.close()
    finally:
        occupied.close()

    assert b" 503 " in response
    assert b"Retry-After: 1" in response


@pytest.mark.integration
def test_after_middleware_failures_do_not_acknowledge_unsaved_state(running_server):
    server, middleware = running_server

    def broken_persistence(_ctx, _body):
        raise RuntimeError("persistence failed")

    middleware.add_after(broken_persistence)
    status, headers, body = request(server, "GET", "/echo")

    assert status == 500
    assert headers["Cache-Control"] == "no-store"
    assert "persistence failed" not in body


@pytest.mark.integration
def test_before_middleware_errors_are_not_allowed_to_bypass_request_handling(running_server):
    server, middleware = running_server

    def broken_guard(ctx):
        raise RuntimeError("guard failed")

    middleware.add_before(broken_guard)
    status, _, body = request(server, "GET", "/echo")

    assert status == 500
    assert "guard failed" not in body


@pytest.mark.integration
def test_production_templates_are_private_unless_the_application_overrides_cache_control(running_server):
    server, _ = running_server
    server.mode = "prod"

    status, headers, _ = request(server, "GET", "/echo")

    assert status == 200
    assert headers["Cache-Control"] == "private, no-store"


@pytest.mark.integration
def test_production_server_writes_sanitized_request_and_error_logs(running_server):
    server, _ = running_server
    server.mode = "prod"
    log_file = Path(server.active_config["log_file"])

    status, _, _ = request(server, "GET", "/echo?token=private-value")

    assert status == 200

    status, _, _ = request(server, "GET", "/broken")

    assert status == 500

    contents = log_file.read_text(encoding="utf-8")

    assert "[Request] GET /echo" in contents
    assert "private-value" not in contents
    assert "Unhandled request error" in contents
    assert "query_params" not in contents
