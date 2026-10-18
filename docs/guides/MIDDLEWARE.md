# Middleware Pipeline Guide

Middleware provides request and response interceptors to handle authentication, cross-cutting security headers, CSRF validation, rate limiting, and custom request processing.

---

## 1. Middleware Lifecycle

Every incoming HTTP request passes through the middleware pipeline before reaching the template `render()` function, and every response passes back through the pipeline in reverse order:

```text
Incoming Request
   │
   ▼
┌─────────────────────────────────┐
│ 1. RateLimitMiddleware          │
│ 2. SecurityHeadersMiddleware    │
│ 3. SessionMiddleware            │
│ 4. CsrfMiddleware               │
│ 5. AuthMiddleware               │
│ 6. Custom Application Middleware│
└─────────────────────────────────┘
   │
   ▼
Page Template render()
   │
   ▼
Response Processing (after_request)
   │
   ▼
Client Response
```

---

## 2. Built-in Middleware

Templar comes pre-configured with essential security and state middleware:

- **`SessionMiddleware`:** Manages signed and encrypted session cookies, restoring session dictionaries onto `request.session`.
- **`CsrfMiddleware`:** Generates and verifies session-bound CSRF tokens for state-changing HTTP requests (`POST`, `PUT`, `DELETE`).
- **`AuthMiddleware`:** Validates session credentials, loads active user identity, and attaches `request.user`.
- **`SecurityHeadersMiddleware`:** Adds security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, Content Security Policy, etc.).
- **`RateLimitMiddleware`:** Protects endpoints from abuse and brute-force traffic.

---

## 3. Writing Custom Middleware

To create custom middleware, implement a class with `before_request` and/or `after_request` methods:

```python
# middleware/timing.py
import time
from templar.core.Logger import get_logger

logger = get_logger(__name__)

class RequestTimingMiddleware:
    """Logs the execution time of each HTTP request."""
    
    def before_request(self, request):
        request.start_time = time.time()
        return None  # Returning None allows the request to continue

    def after_request(self, request, response):
        if hasattr(request, "start_time"):
            duration = (time.time() - request.start_time) * 1000
            logger.info(f"{request.method} {request.path} completed in {duration:.2f}ms")
        return response
```

### Short-Circuiting Requests in `before_request`

If `before_request` returns an element or response object (or raises a redirect / error), execution stops immediately and that response is returned without executing subsequent middleware or page templates:

```python
# middleware/ip_whitelist.py
from templar.core.Exceptions import ForbiddenException

class IpWhitelistMiddleware:
    ALLOWED_IPS = {"127.0.0.1", "10.0.0.1"}

    def before_request(self, request):
        client_ip = request.client_address[0]
        if client_ip not in self.ALLOWED_IPS:
            raise ForbiddenException("Access restricted to whitelisted IP addresses.")
        return None
```

---

## 4. Registering Middleware in `app.py`

Register your custom middleware on the `TemplarServer` instance before starting:

```python
from templar.Config import Config
from templar.TemplarServer import TemplarServer
from middleware.timing import RequestTimingMiddleware
from middleware.ip_whitelist import IpWhitelistMiddleware

config = Config()
server = TemplarServer(config=config)

# Add custom middleware
server.add_middleware(RequestTimingMiddleware())
server.add_middleware(IpWhitelistMiddleware())

if __name__ == "__main__":
    server.start()
```
