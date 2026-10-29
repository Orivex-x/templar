import sys, logging
from typing import Callable, List, Optional, Any

sys.dont_write_bytecode = True

class MiddlewareManager:
    """
    Central middleware dispatcher controlling before/after hooks.
    Server-agnostic: compatible with Templar's HTTPServer handlers
    and future async backends.
    """

    def __init__(self) -> None:
        self.before_request: List[Callable] = [] # functions(handler)
        self.after_request: List[Callable] = [] # functions(handler, response_body)

    # Registration
    def add_before(self, func: Callable) -> None:
        """Register a function to run before request handling."""
        self.before_request.append(func)

    def add_after(self, func: Callable) -> None:
        """Register a function to run after request handling."""
        self.after_request.append(func)

    # Execution
    def run_before(self, handler) -> Optional[Any]:
        """
        Execute before-request middleware.

        If middleware returns a non-None value:
            -> processing stops
            -> the caller uses the returned value to send an early response
              (e.g. auth guard, redirect, JSON error, rate limit block)
        """
        for func in self.before_request:
            try:
                result = func(handler)

                if result is not None:
                    return result  # short-circuit
            except Exception as exc:
                logging.error(
                    f"[Templar Middleware] Error in before_request '{func.__name__}': {exc}",
                    exc_info=True
                )

                # Continuing could bypass authorization, CSRF, or rate limits. Let the HTTP boundary turn this into a controlled 500.
                raise

        return None

    def run_after(self, handler, response_body: bytes) -> None:
        """
        Execute after-request middleware.

        Errors are logged and propagated while the HTTP boundary can still
        replace the response with a controlled failure. Silently continuing is
        unsafe for persistence middleware such as sessions.
        """
        for func in self.after_request:
            try:
                func(handler, response_body)
            except Exception as exc:
                logging.error(
                    f"[Templar Middleware] Error in after_request '{func.__name__}': {exc}",
                    exc_info=True
                )

                raise

    # Introspection/Debug
    def list_before(self) -> list[str]:
        """Return registered before-request middleware names."""
        return [f.__name__ for f in self.before_request]

    def list_after(self) -> list[str]:
        """Return registered after-request middleware names."""
        return [f.__name__ for f in self.after_request]

# Singleton
middleware = MiddlewareManager()
