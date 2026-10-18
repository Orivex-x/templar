import sys
from http.cookies import SimpleCookie

from templar.Session import MemorySessionStore, RedisSessionStore, sign, unsign
from templar.middleware.MiddlewareManager import MiddlewareManager, middleware

sys.dont_write_bytecode = True

DEFAULT_SESSION_COOKIE_NAME = "templar_session"


def install(manager: MiddlewareManager = middleware, config=None) -> None:
    """Register session hooks on one server-owned middleware registry."""
    secret_key = (config.get("session_secret") if config else None) or "changeme"
    cookie_name = (config.get("session_cookie_name") if config else None) or DEFAULT_SESSION_COOKIE_NAME
    cookie_secure = bool(config.get("session_cookie_secure", False)) if config else False

    if (
        config
        and getattr(config, "active_env", None) == "prod"
        and config.get("session_cookie_secure") is not True
    ):
        raise ValueError("Production requires session_cookie_secure: true")

    cookie_samesite = (config.get("session_cookie_samesite") if config else None) or "Lax"
    session_ttl = int(config.get("session_ttl_seconds", 86_400)) if config else 86_400
    session_backend = (config.get("session_backend", "memory") if config else "memory").lower()

    if session_backend == "redis":
        redis_url = config.get("session_redis_url") if config else None

        if not redis_url:
            raise ValueError("session_redis_url is required when session_backend is 'redis'")

        session_store = RedisSessionStore(redis_url, session_ttl)
    elif session_backend == "memory":
        session_store = MemorySessionStore(session_ttl)
    else:
        raise ValueError(f"Unsupported session backend: {session_backend}")

    def load_session(ctx):
        # Static responses are deliberately public/cacheable. Loading or refreshing an existing session here would attach
        # Set-Cookie to those responses and defeat shared caches.
        if ctx.path.startswith("/static/") or ctx.path == "/favicon.ico":
            ctx._templar_skip_session = True

            return

        cookie = SimpleCookie()
        cookie.load(ctx.headers.get("Cookie", ""))
        raw_cookie = cookie.get(cookie_name)
        payload = unsign(raw_cookie.value, secret_key) if raw_cookie else None
        sid = payload.get("_sid") if isinstance(payload, dict) else None
        session_data, version = session_store.load(sid) if isinstance(sid, str) else (None, None)

        # Do not allocate sessions for anonymous/static requests. A server-side entry and cookie are created only once
        # application code stores data.
        ctx.session = {**session_data, "_sid": sid} if session_data is not None else {}
        ctx._templar_session_original = dict(session_data or {})
        ctx._templar_session_version = version

    def save_session(ctx, _response_body):
        if getattr(ctx, "_templar_skip_session", False):
            return

        rotate = bool(ctx.session.pop("_templar_rotate_session", False))
        sid = ctx.session.get("_sid")
        session_data = {key: value for key, value in ctx.session.items() if key != "_sid"}

        if rotate and sid:
            session_store.delete(sid)
            sid = None

        if not session_data:
            if sid:
                session_store.delete(sid)
                ctx.cookie(
                    cookie_name,
                    "",
                    path="/",
                    httponly=True,
                    secure=cookie_secure,
                    samesite=cookie_samesite,
                    max_age=0,
                )

            return

        if not sid:
            sid = session_store.create(session_data)
        else:
            original = getattr(ctx, "_templar_session_original", {})
            expected_version = getattr(ctx, "_templar_session_version", None)
            updated = {key: value for key, value in session_data.items() if original.get(key) != value}
            deleted = set(original) - set(session_data)

            for _ in range(5):
                if expected_version is not None and session_store.save_if_version(sid, session_data, expected_version):
                    break

                latest, expected_version = session_store.load(sid)

                if latest is None or expected_version is None:
                    sid = session_store.create(session_data)
                    break

                session_data = dict(latest)
                session_data.update(updated)

                for key in deleted:
                    session_data.pop(key, None)
            else:
                raise RuntimeError("Session was modified concurrently; retry the request")

        ctx.session["_sid"] = sid
        ctx.cookie(
            cookie_name,
            sign({"_sid": sid}, secret_key),
            path="/",
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,
        )

    manager.add_before(load_session)
    manager.add_after(save_session)
