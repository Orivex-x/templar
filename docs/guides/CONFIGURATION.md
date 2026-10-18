# Configuration & Environments Guide

Templar uses a declarative YAML-based configuration file (`templar.config.yml`) with support for environment profiles, dynamic secret substitution (`${NAME}`), and CLI management.

---

## 1. The `templar.config.yml` Schema

A standard configuration file defines distinct profiles for `dev`, `prod`, and `test`:

```yaml
active: dev

dev:
  mode: dev
  host: 127.0.0.1
  port: 8000
  debug: true
  session_secret: "dev-insecure-secret-key-change-in-prod"
  session_ttl: 86400
  csrf_enabled: true
  db_engine: sqlite
  db_uri: db/dev.db
  cache_backend: memory
  cache_ttl: 300
  gzip: true
  cors: false

prod:
  mode: prod
  host: 0.0.0.0
  port: 8000
  debug: false
  session_secret: ${TEMPLAR_SESSION_SECRET}
  session_ttl: 86400
  csrf_enabled: true
  db_engine: postgresql
  db_uri: ${DATABASE_URL}
  cache_backend: redis
  cache_redis_url: ${REDIS_URL}
  cache_ttl: 3600
  gzip: true
  cors: false
  allowed_hosts:
    - "example.com"
    - "www.example.com"

test:
  mode: test
  host: 127.0.0.1
  port: 8001
  debug: true
  session_secret: "test-secret-key"
  db_engine: sqlite
  db_uri: ":memory:"
  cache_backend: null
```

---

## 2. Dynamic Secret Substitution

Templar supports `${VARIABLE_NAME}` interpolation inside `templar.config.yml`.

When Templar loads configuration:
1. It looks for matching environment variables in the host process environment.
2. If not found, it checks the local `.env` file in the project root.
3. If a required placeholder cannot be resolved, Templar raises a configuration error during startup to prevent unsafe runtime defaults.

```bash
# Example .env file:
TEMPLAR_SESSION_SECRET=super-secret-random-32-byte-hex-string
DATABASE_URL=postgresql://user:pass@localhost:5432/production_db
REDIS_URL=redis://localhost:6379/0
```

---

## 3. Managing Configuration with the CLI

Templar includes dedicated CLI commands to inspect and update configuration safely:

```bash
# Show active configuration (secrets redacted by default)
templar config show active

# Show configuration for a specific environment
templar config show prod

# Show raw values including secrets (trusted terminal only)
templar config show active --show-secrets

# Switch active environment profile
templar config activate prod

# Update a configuration value atomically
templar config set port 8080 --env prod
templar config set debug false --env dev
```

---

## 4. Environment Variable Overrides

You can temporarily override configuration parameters at runtime without modifying `templar.config.yml`:

```bash
TEMPLAR_ENV=prod TEMPLAR_PORT=9000 templar run
```
