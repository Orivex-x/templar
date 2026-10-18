# Example Templar project

This example mirrors the packaged project skeleton used by `templar create`.
It is documentation and a reference project; new applications should be made
with the CLI so they receive the currently bundled scaffold.

## Run it

```sh
python3 -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
templar run
```

The server listens on `http://127.0.0.1:8000/` by default. Templates under
`templates/` are automatically routed; `app.py` provides optional explicit
routes.

## Production

Use `templar run --prod` only after configuring `templar.config.yml` and its
environment values. Production requires secure session cookies and either
direct TLS certificates or explicit loopback proxy termination. Run migrations
with `templar migrate run`; `migrate up` is not a Templar command.

Templar is its own HTTP server and is not launched with Gunicorn. Put Nginx,
Caddy, or another reverse proxy in front when you need external TLS/static-file
delivery. See `docs/deployment/DEPLOYMENT.md` in the package source.

## Files

- `templates/`: Python page modules (`index.templar.py` maps to `/`).
- `static/`: public files served below `/static/`.
- `themes/`: Python theme modules.
- `migrations/`: application migrations.
- `templar.config.yml`: dev/prod configuration.

Run `templar --help` or `templar <command> --help` for the installed CLI.
