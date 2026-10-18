# Quickstart Guide

This tutorial walks through creating a full-stack Templar web application with custom pages, dynamic routing, database models, and forms.

---

## 1. Create a New Project

Use the `templar create` command to generate a new application from the official skeleton:

```bash
templar create my-blog
cd my-blog
```

---

## 2. Start the Development Server

Launch the development server:

```bash
templar run
```

You will see output indicating that the server is active:
```text
Templar Server started on http://127.0.0.1:8000 (dev mode)
```

Open your browser and navigate to `http://127.0.0.1:8000` to see your home page.

---

## 3. Create a Custom Page Template

In Templar, views are pure Python files located in the `templates/` directory. Create a new template at `templates/about.templar.py`:

```python
"""About page template."""

from templar.core.elements.Main import Main
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Anchor import Anchor
from templar.core.components import Card

def render(**kwargs):
    """Render the about page."""
    request = kwargs.get("request")
    
    return Main([
        Heading("About Our Application", level=1),
        Paragraph("Built with pure Python and Templar."),
        Card([
            Heading("Our Mission", level=3),
            Paragraph("Making web development in Python clean, fast, and enjoyable."),
            Anchor("Return to Home", href="/"),
        ], shadow=True)
    ], id="about-page")
```

Templar immediately maps this template to `http://127.0.0.1:8000/about`!

---

## 4. Define a Database Model

Templar includes an Active Record ORM. Define a model in `models/post.py`:

```python
from templar.db.Models import Model

class Post(Model):
    _table = "posts"
    _fields = {
        "id": int,
        "title": str,
        "content": str,
        "author": str,
    }
    __required_fields__ = ("title", "content")
```

---

## 5. Add a Form with Validation

Create a form schema in `forms/post.py`:

```python
from templar.forms import Form, TextField, TextAreaField, Required, Length

class PostForm(Form):
    title = TextField(
        label="Post Title",
        required=True,
        validators=[Required(), Length(min_len=3, max_len=100)]
    )
    content = TextAreaField(
        label="Post Content",
        required=True,
        validators=[Required(), Length(min_len=10)]
    )
    author = TextField(
        label="Author Name",
        required=True,
        validators=[Required()]
    )
```

---

## 6. Create a Dynamic Route with Form Submission

Create a template at `templates/create-post.templar.py`:

```python
"""Create post template."""

from templar.core.elements.Main import Main
from templar.core.elements.Heading import Heading
from templar.core.elements.Div import Div
from templar.core.components import Alert
from forms.post import PostForm
from models.post import Post

def render(**kwargs):
    request = kwargs.get("request")
    feedback = None
    
    form = PostForm(data=request.form if request and request.method == "POST" else None)
    
    if request and request.method == "POST":
        if form.validate():
            # Save post to database
            post = Post(
                title=form.get_field("title").value,
                content=form.get_field("content").value,
                author=form.get_field("author").value
            )
            post.save()
            feedback = Alert("Post published successfully!", type="success")
            form = PostForm()  # Reset form
        else:
            feedback = Alert("Please correct the errors in the form.", type="error")

    content = [
        Heading("Create New Post", level=1),
        feedback if feedback else Div(),
        form.render(
            submit_text="Publish Post",
            action="/create-post",
            method="POST",
            csrf_token=request.csrf_token() if request else ""
        )
    ]
    
    return Main(content, id="create-post-page")
```

---

## 7. Inspecting Routes & Config

Use Templar's CLI to inspect your application:

```bash
# View all registered routes
templar routes

# Inspect active configuration
templar config show active
```

---

## Summary

You've built a full-stack Python web application with:
- Native Python templates (`render()`)
- Dynamic URL routing
- Active Record database persistence
- Validated HTML forms with CSRF protection

Explore the **[User Guides](../README.md#user-guides)** to learn more!
