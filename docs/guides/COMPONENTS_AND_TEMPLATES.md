# Components & Templates Guide

Templar uses a pure Python component model for creating user interfaces. Rather than compiling text template files with embedded template tags, you construct UI trees using composable Python objects.

---

## The `render()` Contract

Every page template (`*.templar.py`) in the `templates/` directory must export a `render(**kwargs)` function. 

When a request arrives, `TemplarServer` invokes `render()` with the request context:

```python
"""templates/dashboard.templar.py"""

from templar.core.elements.Main import Main
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Div import Div

def render(**kwargs):
    # Context passed by the server:
    request = kwargs.get("request")
    user = kwargs.get("user")  # If user loader is registered
    
    username = user["username"] if user else "Guest"
    
    return Main([
        Heading(f"Welcome, {username}!", level=1),
        Paragraph("Manage your settings and projects below."),
    ], id="dashboard-page")
```

---

## Core Elements

Templar provides standard HTML elements as Python classes in `templar.core.elements.*`:

| Element Class | HTML Tag | Common Arguments / Props |
| :--- | :--- | :--- |
| `Div` | `<div>` | `content`, `id`, `classes`, `style`, `attributes` |
| `Section` | `<section>` | `content`, `id`, `classes` |
| `Article` | `<article>` | `content`, `id`, `classes` |
| `Main` | `<main>` | `content`, `id`, `classes` |
| `Heading` | `<h1>`-`<h6>` | `content`, `level=1`, `classes` |
| `Paragraph` | `<p>` | `content`, `classes` |
| `Span` | `<span>` | `content`, `classes` |
| `Anchor` | `<a>` | `content`, `href`, `target`, `classes` |
| `Button` | `<button>` | `content`, `type="button"`, `disabled`, `classes` |
| `Input` | `<input>` | `type="text"`, `name`, `value`, `placeholder`, `disabled` |
| `Image` | `<img>` | `src`, `alt`, `width`, `height` |
| `Table`, `Tr`, `Th`, `Td` | `<table>`, `<tr>`, etc. | `content`, `classes` |
| `List`, `ListItem` | `<ul>`/`<ol>`, `<li>` | `content`, `ordered=False` |

### Element Composition Example

```python
from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Anchor import Anchor
from templar.core.elements.List import List, ListItem

ui = Div([
    Heading("Features", level=2),
    Paragraph("Why developers choose Templar:"),
    List([
        ListItem("Pure Python syntax"),
        ListItem("Component-based hierarchy"),
        ListItem("Integrated security and forms"),
    ]),
    Anchor("Learn More", href="/about", classes=["btn", "btn-primary"]),
], classes=["container", "py-4"])
```

---

## Pre-Built UI Components

Templar includes pre-styled, high-level components in `templar.core.components`:

### 1. `Card`
A versatile container with shadow, border radius, and optional hover animation:

```python
from templar.core.components import Card
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

card = Card([
    Heading("Project Metrics", level=3),
    Paragraph("All systems operating within normal parameters."),
], shadow=True, hover_effect=True, padding="2rem")
```

### 2. `Alert`
Notification boxes with variants (`info`, `success`, `warning`, `error`):

```python
from templar.core.components import Alert

alert_success = Alert("Changes saved successfully!", type="success")
alert_warning = Alert("Database maintenance scheduled tonight.", type="warning")
alert_error = Alert("Failed to authenticate user credentials.", type="error")
```

### 3. `Badge`
Compact status pills and labels with color variants:

```python
from templar.core.components import Badge

badge_new = Badge("New", variant="primary")
badge_active = Badge("Active", variant="success")
badge_beta = Badge("Beta", variant="warning")
```

### 4. `Modal`
Dialog overlay component:

```python
from templar.core.components import Modal
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Button import Button

modal = Modal([
    Paragraph("Are you sure you want to delete this resource?"),
    Button("Confirm Delete", variant="danger"),
], title="Confirm Action", show=True, size="md")
```

### 5. `Spinner`
Animated loading indicator:

```python
from templar.core.components import Spinner

loader = Spinner(size="md", color="#007BFF")
```

---

## Creating Custom Reusable Components

Because components are standard Python classes, you can encapsulate complex UI layouts, state, and styles into your own custom component classes:

```python
from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Anchor import Anchor

class UserProfileCard(Div):
    """Custom reusable profile card component."""
    
    def __init__(self, username: str, email: str, role: str, avatar_url: str = None):
        classes = ["user-profile-card", f"role--{role.lower()}"]
        
        content = [
            Div(classes=["avatar-container"], style={"background-image": f"url('{avatar_url}')"} if avatar_url else None),
            Heading(username, level=3),
            Paragraph(f"Email: {email}", classes=["text-muted"]),
            Paragraph(f"Role: {role.title()}", classes=["badge", "badge-info"]),
            Anchor("View Full Profile", href=f"/users/{username}", classes=["btn", "btn-sm"]),
        ]
        
        super().__init__(content=content, classes=classes)
        
        # Component-level styling
        if self.style:
            self.style.set("border", "1px solid #e2e8f0") \
                      .set("border-radius", "8px") \
                      .set("padding", "1.5rem")
```

Use your component anywhere in any template:

```python
from components.profile import UserProfileCard

def render(**kwargs):
    return UserProfileCard(username="alice", email="alice@example.com", role="admin")
```

---

## Styling & Layout Themes

Templar supports:
1. **Utility & Custom CSS Classes:** Pass class lists via `classes=["card", "shadow-sm"]`.
2. **Inline Style Objects:** Modify `element.style.set("property", "value")` or `style={"color": "#333"}`.
3. **Themes:** Define application color palettes in `themes/light.templar.py` and `themes/dark.templar.py`.
