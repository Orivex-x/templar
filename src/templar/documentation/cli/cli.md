# Templar CLI

Install Templar from source (`pip install -e .`), then use:

```sh
templar <command> [options]
templar <command> --help
```

The console entry point is the supported interface. `python -m templar` is not
a supported invocation.

## First use

```sh
templar create my-site
cd my-site
python3 -m venv .venv
python -m pip install -r requirements.txt
templar run
```

Use `templar new` when you prefer the historical alias. `templar run` starts
development mode from the project’s active configuration; `templar run --prod`
selects production for that one run.

## Completion

```sh
templar install-completion
templar install-completion --shell powershell
templar install-completion --dry-run
```

Completion is user-scoped and supports Bash, zsh, Fish, and PowerShell. Open a
new terminal after installation.

## Daily workflow

```sh
templar config show active
templar config set port 8080
templar routes
templar preview index
templar migrate run
```

`templar config show` redacts sensitive resolved values unless
`--show-secrets` is explicitly supplied. See the packaged
[CLI reference](../../CLI_REFERENCE.md) for all commands, marketplace trust,
and migration examples.
