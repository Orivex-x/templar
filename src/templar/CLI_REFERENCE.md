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
| `routes` | Show discovered and explicit routes. | `templar routes` |
| `shell` | Open a Python shell with project renderer, router, and config objects. | `templar shell` |
| `deploy` | Stage and deploy through the Docker or SSH provider. | `templar deploy --provider docker --image my-site` |
| `install-completion` | Install user-scoped completion for Bash, zsh, Fish, or PowerShell. | `templar install-completion --shell fish` |
| `marketplace-pack` | Create a marketplace package artifact. | `templar marketplace-pack ./package ./dist/package.json` |
| `marketplace-sign` | Make a detached GPG signature for an artifact. | `templar marketplace-sign ./dist/package.json --keyid FINGERPRINT` |
| `marketplace-publish` | Publish an artifact and signature to the configured marketplace. | `templar marketplace-publish ./dist/package.json` |
| `marketplace-install` | Install an approved marketplace package. | `templar marketplace-install widgets --version 1.2.0` |
| `marketplace-import-key` | Import a signing public key; `--trust` adds its fingerprint to project config. | `templar marketplace-import-key vendor.asc --trust` |
| `marketplace-verify` | Verify an artifact’s detached signature. | `templar marketplace-verify package.json package.json.asc` |
| `help [COMMAND]` | Display Rich CLI help. | `templar help migrate` |

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

## Marketplace trust

Remote marketplace installation requires a detached signature and a trusted,
full OpenPGP fingerprint. Bootstrap a vendor key with:

```sh
templar marketplace-import-key ./vendor-public.asc --trust
templar marketplace-install vendor-package
```

Do not use short key IDs as trust anchors. Package artifacts, signatures, and
public-key metadata are validated before installation. Verified package files
are materialised at `marketplace_assets_dir/<package>/<version>/` (by default,
`static/assets/marketplace/`) and are available through `/static/assets/...`.
