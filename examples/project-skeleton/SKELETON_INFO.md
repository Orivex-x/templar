# Templar Project Skeleton

This directory contains the skeleton/template structure for new Templar Framework projects.

## What is This?

When users create a new Templar project, the files in this directory are used as a starting template. This ensures every new project has:

- Proper directory structure
- Configuration files
- Sample templates
- Example code
- Documentation

## Directory Structure

```
skeleton/
├── app.py                   # Main application entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
├── templar.config.yml      # Templar configuration
├── README.md               # Project documentation
├── templates/              # Page templates
│   ├── index.templar.py    # Home page
│   └── about.templar.py    # About page
├── themes/                 # Theme definitions
│   ├── light.templar.py    # Light theme
│   └── dark.templar.py     # Dark theme
├── migrations/             # Database migrations
│   └── example_migration.py
└── static/                 # Static assets (CSS, JS, images)
```

## Files

### app.py
Main application file with:
- Configuration loading
- Router setup
- Renderer initialization
- Server startup

### templar.config.yml
Configuration file for:
- Server settings (host, port, mode)
- Database connection
- Cache backend
- Session settings
- Logging configuration

### templates/
Page templates written in Python using Templar elements:
- `index.templar.py` - Home page with example components
- `about.templar.py` - About page example

### themes/
Theme files defining CSS and styling:
- `light.templar.py` - Light color theme
- `dark.templar.py` - Dark color theme

### migrations/
Example database migration file showing how to create migrations.

### static/
Placeholder for CSS, JavaScript, and image files.

## Using This Skeleton

When a user creates a new Templar project with:
```bash
templar create my-project
```

The contents of this `skeleton/` directory are copied to create the new project structure.

## Customizing the Skeleton

To modify what new projects look like:

1. **Update `app.py`** to change the default application code
2. **Modify `templar.config.yml`** to change default configuration
3. **Edit templates** in `templates/` to change default pages
4. **Update `requirements.txt`** to change default dependencies
5. **Modify `README.md`** to change project documentation

Any changes made to files in this directory will be reflected in all newly created projects.

## Example: Adding Authentication

To make all new projects have authentication by default:

1. Add auth templates to `templates/auth/`
2. Update `app.py` to include auth routes
3. Add database migration for users table
4. Include models directory with User model
5. Update `README.md` with auth instructions

All new projects will then include these features automatically.

---

This skeleton ensures new Templar projects are production-ready with best practices built-in from the start.
