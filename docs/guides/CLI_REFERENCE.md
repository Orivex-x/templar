# Command-Line Interface (CLI) Reference

The `templar` executable provides project generation, runtime servers, database migrations, configuration inspection, and deployment tools.

---

## Command Overview

| Command | Description | Example |
| :--- | :--- | :--- |
| `templar create <name>` | Generate a new project workspace from the skeleton | `templar create my-site` |
| `templar new <name>` | Alias for `templar create` | `templar new my-site` |
| `templar run` | Start the development or production server | `templar run --port 8080` |
| `templar routes` | Display table of all registered and discovered routes | `templar routes` |
| `templar config <action>` | Inspect, update, or activate configuration profiles | `templar config activate prod` |
| `templar migrate <action>` | Manage database migrations (status, run, rollback, create) | `templar migrate run` |
| `templar preview <template>` | Render a template directly in the terminal | `templar preview index` |
| `templar shell` | Launch an interactive Python shell with loaded project context | `templar shell` |
| `templar deploy` | Automated deployment via Docker or SSH providers | `templar deploy --provider docker` |
| `templar install-completion` | Install shell autocompletion for Bash, zsh, Fish, PowerShell | `templar install-completion --shell zsh` |
| `templar help [cmd]` | Display detailed help for a specific command | `templar help migrate` |

---

## 1. Project Creation & Execution

### `templar create <project_name>`
Scaffolds a new project directory with templates, themes, static assets, configuration, and `app.py`.

```bash
templar create my-blog
cd my-blog
```

### `templar run [options]`
Starts the HTTP server.

**Options:**
- `--host <ip>`: Bind IP address (default: from config)
- `--port <int>`: Bind port number (default: `8000`)
- `--prod`: Run in production mode with debug mode disabled
- `--theme <name>`: Override default theme (`light` or `dark`)

```bash
# Run locally on custom port
templar run --port 3000

# Run in production mode
templar run --prod --host 0.0.0.0 --port 80
```

---

## 2. Route Inspection

### `templar routes`
Scans the `templates/` folder and `app.py` router definitions, displaying a formatted table of all active routes, their template files, and parameter types.

```bash
templar routes
```

---

## 3. Configuration Management

### `templar config show [env]`
Displays configuration for active or specified environment. Sensitive secrets are masked as `[REDACTED]` by default.

```bash
# Show active profile
templar config show active

# Reveal secret values (trusted terminal only)
templar config show active --show-secrets

# Show specific environment
templar config show prod
```

### `templar config activate <env>`
Changes the `active` environment profile in `templar.config.yml`.

```bash
templar config activate prod
```

### `templar config set <key> <val> [--env <env>]`
Updates a configuration key in `templar.config.yml` atomically.

```bash
templar config set port 8080 --env prod
templar config set debug false --env dev
```

---

## 4. Database Migrations

### `templar migrate status`
Lists all applied and pending schema migrations.

```bash
templar migrate status
```

### `templar migrate create <name> [--type <type>]`
Creates a new migration file in `db/migrations/`.

```bash
templar migrate create add_users_table --type create_table
```

### `templar migrate run`
Executes all pending migrations in chronological order inside a migration transaction.

```bash
templar migrate run
```

### `templar migrate rollback [--step <int>]`
Rolls back the last applied migration (or multiple steps).

```bash
templar migrate rollback --step 1
```

### `templar migrate user-schema [--model <path>]`
Applies compatibility updates and indexes to user tables.

```bash
templar migrate user-schema
```

---

## 5. Interactive Shell

### `templar shell`
Launches an interactive Python shell pre-loaded with `__templar_studio_config.py`, `router`, `renderer`, `db`, and `User` models for rapid testing and debugging.

```bash
templar shell
```

---

## 6. Marketplace Packages

Templar publishes and installs packages through its built-in marketplace
API. The CLI has the marketplace API URL built in
(`http://127.0.0.1:8080/api`), so no marketplace URL setting is required in
`templar.config.yml`. Package sources are directories containing
`manifest.json` and the files to install.
The manifest must declare a `type`: `template`, `utility`, `theme`, or
`component`. Package files are copied into the matching project directory:
`templates/`, `utilities/`, `themes/`, or `components/`. Place files in the
package relative to that destination (for example, put `dark.templar.py` at
the package root for a theme package).

```bash
templar marketplace pack ./my-package ./dist/my-package.json
templar marketplace publish ./dist/my-package.json
```

Package versions are immutable. Install a package and its dependencies with:

```bash
templar marketplace install my-package --version 1.0.0
```

Publishing requires a marketplace account. The CLI prompts for your username
and password for each publish and does not save the password. The first
publisher to claim a package name owns it; only that account can publish later
versions. Hosted registries must use HTTPS. Set
`TEMPLAR_MARKETPLACE_API_URL=https://marketplace.example/api` in the
environment only when using a different hosted registry; do not put registry
credentials or URLs in `templar.config.yml`.

The marketplace scans each decoded file with ClamAV before storing a release.
The CLI checks for a clean scan result before downloading and reports the scan
engine, timestamp, and static-review findings. Releases without a clean result
are not listed or installable. Malware detection and static checks are not a
guarantee that package code is safe.

### Marketplace command list

| Command | Purpose |
| :--- | :--- |
| `templar marketplace pack SRC_DIR OUTPUT` | Build an artifact from a package directory. |
| `templar marketplace publish PKG_FILE [--username USER]` | Sign in and publish an artifact to the built-in registry. |
| `templar marketplace install NAME` | Install a package and its dependencies into directories selected by manifest type. |

Use `templar marketplace <command> --help` for command options. The previous
hyphenated spellings, such as `templar marketplace-install`, remain supported
as aliases.
