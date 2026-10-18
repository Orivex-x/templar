from pathlib import Path
from http.cookies import SimpleCookie

import pytest

from templar.Config import Config
from templar.Context import TemplarContext
from templar.Renderer import Renderer
from templar.Session import unsign
from templar.middleware.MiddlewareManager import MiddlewareManager
from templar.middleware.CsrfMiddleware import install as install_csrf_middleware
from templar.middleware.SessionMiddleware import install as install_session_middleware


@pytest.mark.integration
def test_production_disables_hot_reload_and_sets_secure_session_cookie(sample_config, temp_project_dir):
    sample_config.set_active_config("prod")
    renderer = Renderer(
        sample_config,
        temp_project_dir / "templates",
        temp_project_dir / "themes",
        temp_project_dir / "static",
    )

    html = renderer.render_template("index", debug=sample_config.get("debug"))

    assert "data-templar=\"hot-reload\"" not in html

    manager = MiddlewareManager()
    install_session_middleware(manager, sample_config)
    ctx = TemplarContext(
        handler=None,
        server=None,
        method="GET",
        path="/",
        query={},
        headers={"Cookie": "unrelated=value"},
        route_params={},
    )
    manager.run_before(ctx)
    ctx.session["purpose"] = "security-test"
    manager.run_after(ctx, b"")
    cookies = ctx.cookie_headers()

    assert len(cookies) == 1
    assert "templar_session=" in cookies[0]
    assert "unrelated" not in cookies[0]
    assert "HttpOnly" in cookies[0]
    assert "Secure" in cookies[0]
    assert "SameSite=Lax" in cookies[0]

    parsed_cookie = SimpleCookie()
    parsed_cookie.load(cookies[0])
    signed_value = parsed_cookie["templar_session"].value

    assert unsign(signed_value, "prod-secret")["_sid"] == ctx.session["_sid"]


@pytest.mark.integration
def test_production_rejects_default_session_secret(tmp_path):
    config_path = tmp_path / "templar.config.yml"
    config_path.write_text(
        "dev:\n  mode: dev\n  session_secret: dev-secret\n  log_file: logs/dev.log\n"
        "prod:\n  mode: prod\n  session_secret: changeme\n  log_file: logs/prod.log\n"
        "  deployment_domain: example.com\n  ssl_cert_path: cert.pem\n  ssl_key_path: key.pem\n"
        "  db_engine: sqlite\n  db_uri: sqlite:///prod.db\nactive: prod\n"
    )

    with pytest.raises(ValueError, match="non-default session_secret"):
        Config(config_path=str(config_path))


@pytest.mark.integration
def test_sessions_are_opaque_cookies_with_server_side_data(sample_config):
    manager = MiddlewareManager()
    install_session_middleware(manager, sample_config)
    first = TemplarContext(None, None, "GET", "/", {}, {}, {})
    manager.run_before(first)
    first.session["role"] = "admin"
    manager.run_after(first, b"")

    cookie = SimpleCookie()
    cookie.load(first.cookie_headers()[0])
    signed_value = cookie["templar_session"].value

    assert unsign(signed_value, "test-secret") == {"_sid": first.session["_sid"]}
    assert "admin" not in signed_value

    second = TemplarContext(
        None,
        None,
        "GET",
        "/",
        {},
        {"Cookie": f"templar_session={signed_value}"},
        {},
    )
    manager.run_before(second)

    assert second.session["role"] == "admin"


@pytest.mark.integration
def test_concurrent_session_updates_merge_independent_changes(sample_config):
    manager = MiddlewareManager()
    install_session_middleware(manager, sample_config)
    initial = TemplarContext(None, None, "GET", "/", {}, {}, {})
    manager.run_before(initial)
    initial.session["base"] = "present"
    manager.run_after(initial, b"")
    cookie = SimpleCookie()
    cookie.load(initial.cookie_headers()[0])
    headers = {"Cookie": f"templar_session={cookie['templar_session'].value}"}

    first = TemplarContext(None, None, "GET", "/", {}, headers, {})
    second = TemplarContext(None, None, "GET", "/", {}, headers, {})
    manager.run_before(first)
    manager.run_before(second)
    first.session["first"] = True
    second.session["second"] = True
    manager.run_after(first, b"")
    manager.run_after(second, b"")

    latest = TemplarContext(None, None, "GET", "/", {}, headers, {})
    manager.run_before(latest)

    assert latest.session["base"] == "present"
    assert latest.session["first"] is True
    assert latest.session["second"] is True


@pytest.mark.integration
def test_csrf_middleware_issues_and_validates_session_bound_tokens(sample_config):
    manager = MiddlewareManager()
    install_session_middleware(manager, sample_config)
    install_csrf_middleware(manager, sample_config)
    first = TemplarContext(None, None, "GET", "/form", {}, {}, {})
    manager.run_before(first)
    token = first.csrf_token()
    manager.run_after(first, b"")
    cookie = SimpleCookie()
    cookie.load(first.cookie_headers()[0])

    valid_post = TemplarContext(
        None, None, "POST", "/form", {},
        {"Cookie": f"templar_session={cookie['templar_session'].value}"}, {},
        form={"csrf_token": token},
    )

    assert manager.run_before(valid_post) is None

    invalid_post = TemplarContext(None, None, "POST", "/form", {}, {}, {}, form={})

    assert manager.run_before(invalid_post) == "Forbidden: invalid CSRF token"
    assert invalid_post.status == 403
