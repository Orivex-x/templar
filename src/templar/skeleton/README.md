# MyApp

This project was created with Templar. Pages are Python template modules in
`templates/`; `templar run` discovers them automatically.

## Run locally

```sh
python3 -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
templar run
```

Open `http://127.0.0.1:8000/`. Development mode reloads templates when they
change. `templar run --prod` uses the production configuration for that run.

## Project layout

```text
.
├── app.py                 # optional explicit Router definitions
├── templates/             # *.templar.py pages
├── static/                # CSS, JavaScript, images, and other public files
├── themes/                # Python theme modules
├── migrations/            # tracked database migrations
├── models/                # application models (optional)
├── templar.config.yml     # dev and prod settings
└── requirements.txt       # application dependencies, including Templar
```

`templates/index.templar.py` serves `/`; `templates/about.templar.py` serves
`/about`. Add an `app.py` router only for explicit or parameterised routes;
those routes are merged with the automatically discovered template routes.

## Configuration

```sh
templar config show active
templar config set port 8080
templar config activate prod
```

Keep production secrets in environment variables or `.env`, referenced as
`${NAME}` in `templar.config.yml`. Production requires secure session cookies
and either direct TLS certificates or explicit loopback-only proxy termination.
See the package deployment guide before exposing the application publicly.

## Forms, database, and authentication

POST forms are available as `request.form`; JSON is available as
`request.json`. With CSRF enabled, render `request.csrf_token()` in each
state-changing form (or send it in `X-CSRF-Token`).

```sh
templar migrate create add_accounts --type create_table
templar migrate run
templar migrate status
```

For a legacy built-in user table, run `templar migrate user-schema` as part of
deployment. Do not perform schema compatibility changes during a request.

## Useful commands

```sh
templar routes
templar preview index
templar install-completion
templar <command> --help
```
