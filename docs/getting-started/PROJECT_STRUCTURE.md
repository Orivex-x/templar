# Project Structure

When you initialize a project using `templar create <name>`, Templar generates a clean, modular workspace layout.

```text
my-app/
├── app.py                   # Main application entry point & server setup
├── templar.config.yml       # Multi-environment configuration file
├── requirements.txt         # Project Python dependencies
├── .env.example             # Template for local environment secrets
│
├── templates/               # Page templates (*.templar.py)
│   ├── index.templar.py     # Home page route (/)
│   └── about.templar.py     # About page route (/about)
│
├── static/                  # Static assets served at /static/
│   ├── css/                 # Custom CSS stylesheets
│   ├── js/                  # Client-side JavaScript scripts
│   └── images/              # Images, icons, and media files
│
├── themes/                  # UI theme definitions
│   ├── light.templar.py     # Light mode theme colors & styling
│   └── dark.templar.py      # Dark mode theme colors & styling
│
├── forms/                   # Form schemas and validation classes (optional)
├── models/                  # Active Record database models (optional)
├── db/                      # SQLite database files and migration scripts
│   └── migrations/          # Version-controlled database migrations
│
└── logs/                    # Server runtime and error logs
```

---

## Key Files & Directories

### 1. `app.py`
The primary entry point. Initializes configuration, configures optional explicit routes, binds custom middleware or user loaders, and starts the `TemplarServer`.

```python
from templar.Config import Config
from templar.Router import Router
from templar.Renderer import Renderer
from templar.TemplarServer import TemplarServer

config = Config()
router = Router(config)
renderer = Renderer(config)

server = TemplarServer(
    config=config,
    router=router,
    renderer=renderer,
)

if __name__ == "__main__":
    server.start()
```

### 2. `templar.config.yml`
Declarative multi-environment configuration file defining server parameters, database connections, caching backends, security flags, and session settings for `dev`, `prod`, and `test` environments.

### 3. `templates/`
Directory containing page templates (`*.templar.py`). Templar's router dynamically discovers files in this folder and maps them to URL routes based on file paths.

### 4. `static/`
Contains public static files such as images, stylesheets, fonts, and scripts. Files in this directory are served directly under the `/static/` URL prefix.

### 5. `themes/`
Contains theme definitions (`light.templar.py`, `dark.templar.py`) providing cohesive design tokens, palette variables, and element styling.

### 6. `db/` & `db/migrations/`
Houses the local SQLite database (`dev.db`) and timestamped migration files created via `templar migrate create`.
