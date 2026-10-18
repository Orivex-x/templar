"""Database migration system."""

import importlib.util
import inspect
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

sys.dont_write_bytecode = True

class Migration(ABC):
    description: str = "Database migration"

    @abstractmethod
    def up(self, db) -> None:
        pass

    @abstractmethod
    def down(self, db) -> None:
        pass


_MIGRATION_BASE = Migration
sys.modules.setdefault(f"{__name__}.Migration", sys.modules[__name__])


class MigrationRunner:
    """Manages migration execution."""

    def __init__(self, db, migrations_dir: Path):
        self.db = db
        self.migrations_dir = Path(migrations_dir)
        self._setup_migrations_table()

    def _setup_migrations_table(self) -> None:
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS templar_migrations (
                name VARCHAR(255) PRIMARY KEY,
                batch INTEGER NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def get_executed_migrations(self) -> List[str]:
        result = self.db.fetchall(
            "SELECT name FROM templar_migrations ORDER BY batch, name"
        )

        return [row['name'] for row in result]

    def get_latest_batch(self) -> int:
        result = self.db.fetchone(
            "SELECT MAX(batch) as batch FROM templar_migrations"
        )

        return (result['batch'] or 0) if result else 0

    def run_pending_migrations(self, step: int = None) -> List[str]:
        executed = self.get_executed_migrations()
        pending = self._get_pending_migrations(executed)

        if step:
            pending = pending[:step]

        if not pending:
            return []

        batch = self.get_latest_batch() + 1
        executed_list = []

        for migration_name in pending:
            try:
                migration = self._load_migration(migration_name)

                with self.db.transaction():
                    migration.up(self.db)
                    self.db.execute(
                        "INSERT INTO templar_migrations (name, batch) VALUES (:name, :batch)",
                        {"name": migration_name, "batch": batch}
                    )

                executed_list.append(migration_name)
            except Exception:
                raise

        return executed_list

    def rollback_migrations(self, step: int = 1) -> List[str]:
        executed = self.get_executed_migrations()

        if not executed:
            return []

        latest_batch = self.get_latest_batch()
        rollback_batch = latest_batch - (step - 1)

        result = self.db.fetchall(
            "SELECT name FROM templar_migrations WHERE batch >= :batch ORDER BY name DESC",
            {"batch": rollback_batch}
        )

        migrations_to_rollback = [row['name'] for row in result]
        rolled_back = []

        for migration_name in migrations_to_rollback:
            try:
                migration = self._load_migration(migration_name)

                with self.db.transaction():
                    migration.down(self.db)
                    self.db.execute(
                        "DELETE FROM templar_migrations WHERE name = :name",
                        {"name": migration_name}
                    )

                rolled_back.append(migration_name)
            except Exception:
                raise

        return rolled_back

    def _get_pending_migrations(self, executed: List[str]) -> List[str]:
        if not self.migrations_dir.exists():
            return []

        migration_files = sorted(
            self.migrations_dir.glob("*.py")
        )

        pending = []

        for file in migration_files:
            name = file.stem

            if name.startswith("__"):
                continue

            if name not in executed:
                pending.append(name)

        return pending

    def _load_migration(self, migration_name: str) -> Migration:
        path = (self.migrations_dir / f"{migration_name}.py").resolve()

        if self.migrations_dir.resolve() not in path.parents or not path.is_file():
            raise FileNotFoundError(f"Migration not found: {migration_name}")

        module_name = f"templar_migration_{migration_name}"
        spec = importlib.util.spec_from_file_location(module_name, path)

        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load migration: {migration_name}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        migration_classes = [
            cls for _, cls in inspect.getmembers(module, inspect.isclass)
            if cls.__module__ == module.__name__
            and issubclass(cls, _MIGRATION_BASE)
            and cls is not _MIGRATION_BASE
        ]

        if len(migration_classes) != 1:
            raise ValueError(
                f"Migration '{migration_name}' must define exactly one Migration subclass; found {len(migration_classes)}"
            )

        return migration_classes[0]()


class MigrationGenerator:
    """Generate migration files."""

    @staticmethod
    def generate_migration(
        name: str,
        migrations_dir: Path,
        migration_type: str = "blank"
    ) -> Path:
        normalized_name = name.strip().lower()

        if not re.fullmatch(r"[a-z][a-z0-9_]*", normalized_name):
            raise ValueError(
                "Migration names must use lowercase letters, numbers, and underscores, "
                "and must start with a letter."
            )

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        migrations_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{timestamp}_{normalized_name}.py"
        filepath = migrations_dir / filename

        content = _MIGRATION_TEMPLATE.format(class_name=_to_class_name(normalized_name))

        filepath.write_text(content)

        return filepath


def _to_class_name(name: str) -> str:
    return ''.join(word.capitalize() for word in name.split('_'))


_MIGRATION_TEMPLATE = """\"\"\"Migration: {class_name}\"\"\"

from templar.migrations import Migration


class {class_name}(Migration):
    description = "{class_name}"

    def up(self, db):
        pass

    def down(self, db):
        pass
"""
