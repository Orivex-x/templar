# Engine Architecture & Subsystems

This document explains the internal architecture of the Templar framework for core contributors and subsystem maintainers.

---

## 1. System Overview

```text
                  Incoming HTTP Request
                            │
                            ▼
                  ┌───────────────────┐
                  │   TemplarServer   │ (Threaded HTTPServer)
                  └─────────┬─────────┘
                            │
                 Middleware Lifecycle Pipeline
          (RateLimit, Headers, Session, Csrf, Auth)
                            │
                            ▼
                  ┌───────────────────┐
                  │      Router       │
                  └─────────┬─────────┘
                            │
              Route Resolution & Parameter Extraction
                            │
                            ▼
                  ┌───────────────────┐
                  │     Renderer      │
                  └─────────┬─────────┘
                            │
              Template Execution & Element Tree
                            │
                            ▼
                  ┌───────────────────┐
                  │    HTML Output    │
                  └───────────────────┘
```

---

## 2. Core Subsystems

### `TemplarServer.py`
The HTTP engine is built on Python's `ThreadingHTTPServer`. It handles socket binding, TLS negotiation, request body parsing, streaming, and connection keep-alive.
- **Thread Safety:** State is never held in global singleton structures during a request cycle; request context objects are passed explicitly down the call stack.
- **Strict Framing:** Rejects HTTP request smuggling attacks by forbidding conflicting `Transfer-Encoding` / `Content-Length` headers.

### `Router.py`
Provides dual-mode route matching:
1. Dynamic file-system discovery of `templates/*.templar.py` and directory structures.
2. Trie/regex-based route table matching with named parameter extraction for explicit routes (`router.add()`).

### `Renderer.py`
Loads and executes the `render(**kwargs)` function exported by page templates. Coordinates element serialization into valid, indented HTML and injects dynamic theme styles, CSS assets, and JavaScript bundles.

### `db/` Subsystem
- **`Database.py`:** Thread-safe facade exposing connection pools, transaction blocks (`with db.transaction():`), and migration locking (`with db.migration_lock():`).
- **`Models.py` & `ModelMeta.py`:** Active Record ORM base class with dynamic query builder chaining (`Model.objects().filter().first()`).
- **`migrations/`:** Schema version runner tracking applied migrations in `_templar_migrations`.

### `auth/` Subsystem
- **`User.py`:** Core user model with identity validation, JSON-encoded roles and permissions, and password hash isolation.
- **`PasswordManager`:** Secure hashing and verification routines.
- **`Session.py`:** Encrypted cookie persistence with HMAC signatures and TTL expiry.

### `cache/` Subsystem
Unified cache interface (`CacheManager`, `CacheProvider`) supporting `MemoryCache`, `FileCache`, `RedisCache`, and `NullCache` with key namespacing.
