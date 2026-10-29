"""Session-backed CSRF protection for browser form submissions."""

import hmac
import secrets

from templar.middleware.MiddlewareManager import MiddlewareManager, middleware


def install(manager: MiddlewareManager = middleware, config=None) -> None:
    """Register CSRF token issuance and POST validation when enabled."""
    enabled = bool(config.get("csrf_enabled", False)) if config else False

    if not enabled:
        return

    def csrf_token(ctx) -> str:
        token = ctx.session.get("_csrf_token")

        if not isinstance(token, str):
            token = secrets.token_urlsafe(32)
            ctx.session["_csrf_token"] = token

        return token

    def header_value(ctx, name: str):
        return next((value for key, value in ctx.headers.items() if key.lower() == name.lower()), None)

    def protect(ctx):
        ctx.csrf_token = lambda: csrf_token(ctx)

        # Internal reactive bridge should not require a CSRF token.
        if ctx.path == "/__templar_reactive__":
            return None

        if ctx.method != "POST":
            return None

        expected = ctx.session.get("_csrf_token")
        supplied = ctx.form.get("csrf_token") or header_value(ctx, "X-CSRF-Token")

        if isinstance(ctx.json, dict):
            supplied = supplied or ctx.json.get("csrf_token")

        if not isinstance(expected, str) or not isinstance(supplied, str) or not hmac.compare_digest(expected, supplied):
            ctx.set_status(403)
            ctx.set_header("Content-Type", "text/plain; charset=utf-8")

            return "Forbidden: invalid CSRF token"

        return None

    manager.add_before(protect)
