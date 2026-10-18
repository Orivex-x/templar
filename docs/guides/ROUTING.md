# Routing & URL Resolution Guide

Templar features a dual routing system: **automatic file-based routing** by default, with support for **explicit route configuration** in `app.py`.

---

## 1. File-Based Routing (Conventions)

Templar automatically maps `.templar.py` files in your `templates/` directory to URL paths:

| File Path | Mapped URL | Description |
| :--- | :--- | :--- |
| `templates/index.templar.py` | `/` | Root home page |
| `templates/about.templar.py` | `/about` | Static page |
| `templates/contact.templar.py` | `/contact` | Static page |
| `templates/blog/index.templar.py` | `/blog` | Nested directory index |
| `templates/blog/archive.templar.py` | `/blog/archive` | Sub-path route |

---

## 2. Dynamic Route Parameters

To capture dynamic values from the URL (such as an ID or slug), use parameter placeholders:

### Bracket Syntax in File Names
- File: `templates/users/[username].templar.py`
- URL: `/users/johndoe`

The captured parameter is passed into `render()`:

```python
"""templates/users/[username].templar.py"""

from templar.core.elements.Main import Main
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

def render(**kwargs):
    request = kwargs.get("request")
    params = kwargs.get("params", {})
    username = params.get("username", "Unknown")
    
    return Main([
        Heading(f"User Profile: {username}", level=1),
        Paragraph(f"Viewing profile data for @{username}"),
    ])
```

---

## 3. Explicit Route Registration

For custom URLs, legacy endpoints, or complex regular expressions, configure explicit routes in `app.py` using the `Router`:

```python
from templar.Config import Config
from templar.Router import Router

config = Config()
router = Router(config)

# Map URLs to template names (relative to templates/)
router.add("/", "index")
router.add("/company/about-us", "about")
router.add("/articles/{slug}", "blog/article")
router.add("/api/v1/users/{id}", "api/user")
```

### Route Parameter Syntax in Explicit Routes
Parameters inside curly braces `{name}` are extracted and passed into `params`:
- `/posts/{id}` matches `/posts/42` -> `params = {"id": "42"}`
- `/shop/{category}/{item_id}` matches `/shop/electronics/99` -> `params = {"category": "electronics", "item_id": "99"}`

---

## 4. Inspecting Registered Routes

Use the Templar CLI to list all file-discovered and explicitly configured routes:

```bash
templar routes
```

Example output:
```text
┌──────────────────────────┬───────────────────────────────┬────────────┐
│ Route Path               │ Target Template               │ Type       │
├──────────────────────────┼───────────────────────────────┼────────────┤
│ /                        │ index.templar.py              │ File-based │
│ /about                   │ about.templar.py              │ File-based │
│ /users/{username}        │ users/[username].templar.py   │ Dynamic    │
│ /company/about-us        │ about.templar.py              │ Explicit   │
└──────────────────────────┴───────────────────────────────┴────────────┘
```

---

## 5. Redirects and Route Responses

To perform HTTP redirects, return a redirect response from your controller or view logic:

```python
from templar.core.Exceptions import RedirectException

def render(**kwargs):
    request = kwargs.get("request")
    user = kwargs.get("user")
    
    if not user:
        # Redirect unauthenticated users to login
        raise RedirectException("/login", status_code=302)
        
    return Main([Heading("Protected Dashboard")])
```
