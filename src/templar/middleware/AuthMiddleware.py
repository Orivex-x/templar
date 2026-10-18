import sys
from collections.abc import Mapping

from templar.auth import Auth
from templar.middleware.MiddlewareManager import MiddlewareManager, middleware

sys.dont_write_bytecode = True


def install(manager: MiddlewareManager = middleware) -> None:
    """Add optional session-backed user loading to a middleware registry."""
    def load_user(ctx):
        if not ctx.session or not ctx.session.get("user_id"):
            return

        # User loaders are application callables, not YAML configuration. The server owns their registration, so each
        # request resolves its own user.
        loader = getattr(ctx.server, "user_loader", None)

        if not callable(loader):
            return

        user = loader(ctx.session["user_id"])

        if user is None:
            ctx.session.pop("user_id", None)

            return

        if not isinstance(user, Mapping):
            serializer = getattr(user, "to_dict", None)

            if not callable(serializer):
                raise TypeError("The registered user loader must return a mapping, model with to_dict(), or None")

            user = serializer()

        try:
            user = Auth.normalize_public_user(user, expected_id=ctx.session["user_id"])
        except (TypeError, ValueError):
            # A malformed or mismatched loader result must never become an authenticated request. Remove the stale
            # server-side identity.
            ctx.session.pop("user_id", None)

            return

        if not user["is_active"]:
            # Account deactivation revokes an already-issued server-side session on its next request, not only future
            # password logins.
            ctx.session.pop("user_id", None)

            return

        ctx.user = user

    manager.add_before(load_user)
