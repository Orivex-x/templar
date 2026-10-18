import sys
import hashlib
import importlib
from pathlib import Path

from templar.cli.BaseCommand import BaseCommand
from templar.db import create_database
from templar.migrations import MigrationGenerator, MigrationRunner
from templar.auth.User import User


class MigrateCommand(BaseCommand):
    """Manage configured database migrations."""

    name = "migrate"
    help = "Run, roll back, inspect, or create database migrations"

    @staticmethod
    def add_args(parser):
        parser.add_argument("action", nargs="?", default="status", choices=("status", "run", "rollback", "create", "user-schema"))
        parser.add_argument("name", nargs="?", help="Migration name for the create action")
        parser.add_argument("--step", type=int, default=1, help="Number of migrations/batches to process")
        parser.add_argument("--type", dest="migration_type", default="blank", choices=("blank", "create_table"))
        parser.add_argument("--model", help="Custom User model as module:Class (for user-schema)")

    @staticmethod
    def _resolve_user_model(model_path):
        if model_path is None:
            return User

        if not isinstance(model_path, str) or model_path.count(":") != 1:
            raise ValueError("--model must use the form module:Class")

        module_name, class_name = model_path.split(":", 1)

        if not module_name or not class_name or "." in class_name:
            raise ValueError("--model must use an importable top-level module:Class")

        model = getattr(importlib.import_module(module_name), class_name, None)

        if not isinstance(model, type) or not issubclass(model, User):
            raise TypeError("--model must refer to User or a User subclass")

        return model

    def run(self, args, extra_args=None):
        if extra_args:
            self.output.error(f"Unrecognized arguments: {' '.join(extra_args)}", title="Migration Error")
            sys.exit(1)

        config = self.cli.config.get_active_config()
        migrations_dir = Path(config["migrations_dir"])

        if args.action == "create":
            if not args.name:
                self.output.error("A migration name is required: templar migrate create <name>", title="Migration Error")
                sys.exit(1)

            path = MigrationGenerator.generate_migration(args.name, migrations_dir, args.migration_type)
            self.output.success(f"Created migration: {path}")

            return

        database = create_database(config)

        try:
            runner = MigrationRunner(database, migrations_dir)

            if args.action == "user-schema":
                user_model = self._resolve_user_model(getattr(args, "model", None))

                if user_model is User:
                    # Preserve the tracking name used by prior releases.
                    migration_name = "templar_builtin_user_schema_v1"
                else:
                    identity = f"{user_model.__module__}:{user_model.__qualname__}:{user_model._table}"
                    migration_name = f"templar_user_schema_v1_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"

                # Migration tracking is part of the same database transaction as the provider-supported upgrade. SQLite
                # rebuilds preserve user indexes/triggers; PostgreSQL/MySQL use ALTER TABLE.
                is_sqlite = type(database._provider).__name__ == "SQLiteProvider"

                if is_sqlite:
                    # SQLite only applies this pragma outside a transaction. The following BEGIN then provides the
                    # database-level write lock for both the rebuild and migration record.
                    database.execute("PRAGMA foreign_keys = OFF")

                try:
                    # Re-check while holding the provider lock. A competing process may have completed this migration
                    # between CLI startup and lock acquisition.
                    with database.migration_lock(migration_name):
                        with database.migration_transaction():
                            if migration_name in runner.get_executed_migrations():
                                self.output.success("User schema migration is already applied")

                                return

                            user_model.migrate_schema(database)
                            database.execute(
                                "INSERT INTO templar_migrations (name, batch) VALUES (:name, :batch)",
                                {"name": migration_name, "batch": runner.get_latest_batch() + 1},
                            )
                finally:
                    if is_sqlite:
                        database.execute("PRAGMA foreign_keys = ON")

                self.output.success(f"Applied user schema migration for {user_model._table}")

                return

            if args.action == "status":
                executed = runner.get_executed_migrations()
                pending = runner._get_pending_migrations(executed)
                self.output.table(
                    columns=["Status", "Migration"],
                    rows=[["Executed", name] for name in executed] + [["Pending", name] for name in pending],
                    title="Database Migrations",
                )
            elif args.action == "run":
                executed = runner.run_pending_migrations(step=args.step)
                self.output.success(f"Executed {len(executed)} migration(s)")
            else:
                rolled_back = runner.rollback_migrations(step=args.step)
                self.output.success(f"Rolled back {len(rolled_back)} migration(s)")
        finally:
            database.close()
