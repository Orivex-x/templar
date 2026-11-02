# Templar CLI reference

The installed command is `templar`. Run `templar <command> --help` for the
exact parser help from the installed version.

| Command | Purpose | Example |
| --- | --- | --- |
| `create NAME` | Create a project from the bundled skeleton. | `templar create my-site` |
| `new NAME` | Alias for `create`. | `templar new my-site` |
| `run` | Start the project server. Supports `--prod`, `--host`, `--port`, and `--theme`. | `templar run --port 8080` |
| `config [show\|activate\|set]` | Inspect, select, or update project configuration. | `templar config activate prod` |
| `migrate ACTION` | Manage migrations: `status`, `run`, `rollback`, `create`, or `user-schema`. | `templar migrate run` |
| `preview TEMPLATE` | Render a template in the terminal. | `templar preview index` |
| `__templar_studio_routes.py` | Show discovered and explicit routes. | `templar routes` |
| `shell` | Open a Python shell with project renderer, router, and config objects. | `templar shell` |
| `deploy` | Stage and deploy through the Docker or SSH provider. | `templar deploy --provider docker --image my-site` |
| `install-completion` | Install user-scoped completion for Bash, zsh, Fish, or PowerShell. | `templar install-completion --shell fish` |
| `marketplace ACTION` | Publish and install marketplace packages; see the commands below. | `templar marketplace install widgets --version 1.2.0` |
| `help [COMMAND]` | Display Rich CLI help. | `templar help migrate` |

### Marketplace commands

| Command | Purpose | Example |
| --- | --- | --- |
| `marketplace pack SRC_DIR OUTPUT` | Build a package artifact from a directory containing `manifest.json`. | `templar marketplace pack ./package ./dist/package.json` |
| `marketplace publish PKG_FILE [--username USER]` | Sign in and publish an artifact to the built-in package registry. | `templar marketplace publish ./dist/package.json` |
| `marketplace install NAME` | Install a package and its dependencies from the built-in registry. | `templar marketplace install widgets --version 1.2.0` |

The previous `marketplace-pack`, `marketplace-publish`, and
`marketplace-install` spellings remain available as aliases.

## Configuration commands

```sh
templar config show
templar config show active
templar config show active --show-secrets
templar config activate prod
templar config set port 8080 --env prod
templar config set debug false
```

Configuration writes are project-local, atomic, and validated before they are
saved. Values whose keys look sensitive are redacted by default; pass
`--show-secrets` only in a trusted terminal.

## Migration commands

```sh
templar migrate status
templar migrate create add_accounts --type create_table
templar migrate run
templar migrate rollback --step 1
templar migrate user-schema
templar migrate user-schema --model myapp.models:Account
```

`migrate user-schema` is the explicit compatibility upgrade for a legacy
built-in `User` table. It must be run during deployment, not left to normal
request handling.

## Marketplace packages

The CLI is preconfigured to use the Templar Marketplace API
(`http://127.0.0.1:8080/api`) for remote publishing and installation. You do not
need to add a marketplace URL to `templar.config.yml`. Package sources need a
`manifest.json` with `name`, semantic `version`, `type`, `author`,
`description`, and `license`; `type` must be `template`, `utility`, `theme`,
or `component`. Put files relative to the destination directory: templates
install in `templates/`, themes in `themes/`, components in `components/`, and
utilities in `utilities/`. For example:

```sh
templar marketplace pack ./my-package ./dist/my-package.json
templar marketplace publish ./dist/my-package.json
```

Publishing prompts for your marketplace account credentials (or accepts
`--username`). The password is not saved. Marketplace package names belong to
the account that first publishes them, and releases are immutable. Use HTTPS
for remote registries; only localhost development registries may use HTTP.
Override the built-in registry for a hosted deployment with
`TEMPLAR_MARKETPLACE_API_URL=https://marketplace.example/api`.

Install a package and its dependencies with:

```sh
templar marketplace install my-package --version 1.0.0
```

Package artifacts and metadata are validated before installation. Downloads
are public and use HTTPS to protect package integrity in transit. Before
downloading, the CLI checks the registry's ClamAV scan status and timestamp;
it refuses packages without a clean result. The install result shows
the scanner version and any static-review findings. Installed files are copied
into the project's directory selected by the package type; those
directories can be customized with `templates_dir`, `themes_dir`,
`components_dir`, and `utilities_dir`. Package publishing and installation use
the marketplace CLI; browser ZIP uploads are not supported.
