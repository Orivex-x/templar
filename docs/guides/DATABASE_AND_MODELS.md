# Database & Models (ORM) Guide

Templar includes a built-in database layer with an Active Record ORM, query builder, connection management, and automated schema migrations.

---

## 1. Supported Database Engines

Templar supports three primary relational database engines:
- **SQLite:** Default file-based database for development and light production.
- **PostgreSQL:** Production-grade engine (requires `pip install "templar[db]"`).
- **MySQL:** Production-grade engine (requires `pip install "templar[db]"`).

---

## 2. Configuration

Configure your database connection in `templar.config.yml`:

```yaml
dev:
  db_engine: sqlite
  db_uri: db/dev.db

prod:
  db_engine: postgresql
  db_uri: ${DATABASE_URL}  # e.g., postgresql://user:password@localhost:5432/myapp
```

---

## 3. Defining Active Record Models

Create models by subclassing `templar.db.Models.Model`:

```python
# models/article.py
from templar.db.Models import Model

class Article(Model):
    _table = "articles"
    _fields = {
        "id": int,
        "title": str,
        "slug": str,
        "content": str,
        "is_published": bool,
        "views": int,
        "created_at": str,
    }
    __unique_fields__ = ("slug",)
    __required_fields__ = ("title", "slug", "content")
```

---

## 4. Querying & CRUD Operations

### Creating and Saving Records

```python
from models.article import Article

# Initialize a new record
article = Article(
    title="Getting Started with Templar",
    slug="getting-started-with-templar",
    content="Templar makes Python web development fast and productive.",
    is_published=True,
    views=0,
)

# Insert into database (populates article.id automatically)
article.save()
print(f"Created article ID: {article.id}")
```

### Querying Records

```python
# Query by primary key or attributes
article = Article.objects().filter(slug="getting-started-with-templar").first()

# Fetch all matching records
published_articles = Article.objects().filter(is_published=True).all()

# Count records
count = Article.objects().filter(is_published=True).count()

# Ordering and limits
recent_articles = Article.objects().filter(is_published=True).order_by("created_at", "DESC").limit(10).all()
```

### Updating Records

```python
article = Article.objects().filter(id=1).first()
if article:
    article.views += 1
    article.save()  # Executes SQL UPDATE
```

### Deleting Records

```python
article = Article.objects().filter(id=1).first()
if article:
    article.delete()  # Executes SQL DELETE
```

---

## 5. Direct SQL Execution & Transactions

For complex analytical queries, raw SQL queries can be executed directly via `Database`:

```python
from templar.db import db

# Fetch query results as dictionaries
rows = db.fetchall(
    "SELECT author, COUNT(*) as post_count FROM articles WHERE is_published = :status GROUP BY author",
    {"status": True}
)

# Atomic transactions
with db.transaction():
    db.execute("UPDATE accounts SET balance = balance - 100 WHERE id = :id", {"id": 1})
    db.execute("UPDATE accounts SET balance = balance + 100 WHERE id = :id", {"id": 2})
```

---

## 6. Schema Migrations

Templar includes a built-in migration management engine:

### Checking Migration Status
```bash
templar migrate status
```

### Creating a New Migration
```bash
templar migrate create add_articles_table --type create_table
```

This generates a timestamped migration script in `db/migrations/`.

### Applying Pending Migrations
```bash
templar migrate run
```

### Rolling Back Migrations
```bash
templar migrate rollback --step 1
```

### Built-in User Schema Upgrade
```bash
templar migrate user-schema
```
