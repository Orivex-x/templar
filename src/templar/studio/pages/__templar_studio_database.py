import re
from pathlib import Path

from templar.core.elements.Button import Button
from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.db import create_database

from templar.cli.commands.Migrate import MigrationRunner

from templar.studio.components.EmptyState import empty_state


def _safe_identifier(value: str, *, allow_dot: bool = False) -> str:
    if not isinstance(value, str):
        return ""

    if allow_dot:
        cleaned = re.sub(r"[^A-Za-z0-9_.]", "", value)
    else:
        cleaned = re.sub(r"[^A-Za-z0-9_]", "", value)

    return cleaned


def _engine_label(engine: str | None) -> str:
    if not engine:
        return "sqlite"

    engine = str(engine).lower()

    if engine in ("sqlite", "sqlite3"):
        return "sqlite"

    if engine in ("postgres", "postgresql"):
        return "postgresql"

    if engine in ("mysql", "mariadb"):
        return "mysql"

    return engine


def _table_names(database, engine: str):
    engine = _engine_label(engine)

    if engine == "sqlite":
        rows = database.fetchall(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )

        return [str(row.get("name", "")) for row in rows if str(row.get("name", "")).strip()]

    if engine == "postgresql":
        rows = database.fetchall(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )

        return [str(row.get("table_name", "")) for row in rows if str(row.get("table_name", "")).strip()]

    if engine == "mysql":
        rows = database.fetchall("SHOW TABLES")

        if rows and "Tables_in_" in rows[0]:
            return [str(row.get(next(iter(row.keys())), "")) for row in rows if row]

        return [str(next(iter(row.values()), "")) for row in rows if row]

    return []


def _table_row_count(database, engine: str, table_name: str) -> int:
    engine = _engine_label(engine)
    table = _safe_identifier(table_name)

    if not table:
        return 0

    try:
        if engine == "sqlite":
            row = database.fetchone(f'SELECT COUNT(*) AS row_count FROM "{table}"')

            return int(row.get("row_count", 0) if row else 0)

        if engine == "postgresql":
            row = database.fetchone(f'SELECT COUNT(*) AS row_count FROM public."{table}"')

            return int(row.get("row_count", 0) if row else 0)

        if engine == "mysql":
            row = database.fetchone(f"SELECT COUNT(*) AS row_count FROM `{table}`")

            return int(row.get("row_count", 0) if row else 0)

    except Exception:
        return 0

    return 0


def _table_columns(database, engine: str, table_name: str):
    engine = _engine_label(engine)
    table = _safe_identifier(table_name)

    if not table:
        return []

    try:
        if engine == "sqlite":
            rows = database.fetchall(f'PRAGMA table_info("{table}")')

            return [str(row.get("name", "")) for row in rows if str(row.get("name", "")).strip()]

        if engine == "postgresql":
            rows = database.fetchall(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = :table_name
                ORDER BY ordinal_position
                """,
                {"table_name": table_name},
            )

            return [str(row.get("column_name", "")) for row in rows if str(row.get("column_name", "")).strip()]

        if engine == "mysql":
            rows = database.fetchall(
                f"DESCRIBE `{table}`"
            )

            return [str(row.get("Field", "")) for row in rows if str(row.get("Field", "")).strip()]

    except Exception:
        return []

    return []


def _build_summary_card(
    title: str,
    value: str,
    tone: str = "neutral"
):
    return Div(
        [
            Paragraph(title, classes=["studio-stat-label"]),
            Heading(value, level=3),
        ],
        classes=["studio-stat-card", f"studio-stat-card-{tone}"],
    )


def _build_table_card(table_name: str, row_count: int, columns):
    columns_preview = (", ".join(columns[:5]) if columns else "No columns reported")

    extra = (f" ... +{len(columns) - 5}" if len(columns) > 5 else "")

    return Div(
        [
            Div(
                [
                    Heading(table_name, level=3),
                    Paragraph(f"{row_count} rows", classes=["db-table-rowcount"]),
                ],
                classes=["db-table-header"],
            ),
            Div(
                [
                    Paragraph("Columns", classes=["db-table-label"]),
                    Paragraph(f"{columns_preview}{extra}", classes=["db-table-value"]),
                ],
                classes=["db-table-meta"],
            ),
        ],
        classes=["db-table-card"],
    )


def _make_run_migrations_action(cli, migration_output):
    """
    Create a migration event handler bound to the active CLI
    and the migration output element.
    """

    def _run_migrations_action(payload=None):
        database = None

        try:
            config = cli.config.get_active_config()

            database = create_database(config)

            runner = MigrationRunner(database, Path(config["migrations_dir"])
            )

            # Execute pending migrations.
            executed = runner.run_pending_migrations()
            executed_count_text_placeholder = "migration" + ("s" if len(executed) > 1 else "")

            # Check the actual migration state after execution.
            completed = runner.get_executed_migrations()

            pending = runner._get_pending_migrations(completed)

            if pending:
                message = (
                    f"{len(executed)} {executed_count_text_placeholder} executed. "
                    f"{len(pending)} {executed_count_text_placeholder} remain pending."
                )

            elif executed:
                message = (
                    f"{len(executed)} {executed_count_text_placeholder} executed. "
                    "All migrations have been run."
                )

            else:
                message = "All migrations have already been run."

            migration_output.content = [message]

            return {
                "target_id": "database-migration-output",
                "html": migration_output.render_content()
            }

        except Exception as exc:
            message = f"Migration failed: {exc}"

            migration_output.content = [message]

            return {
                "target_id": "database-migration-output",
                "html": migration_output.render_content()
            }

        finally:
            if database is not None:
                try:
                    database.close()
                except Exception:
                    pass

    return _run_migrations_action


def render_database(cli=None):

    if cli is None:
        return Div(
            [
                Heading("Database", level=2),
                Paragraph("Inspect the active project database."),
                empty_state(
                    "Database inspector is unavailable",
                    "This page requires a live CLI instance for the active project configuration.",
                ),
            ],
            classes=["studio-page", "studio-database"],
        )

    try:
        config = cli.config
        active_cfg = config.get_active_config()

        engine = _engine_label(active_cfg.get("db_engine"))
        uri = active_cfg.get("db_uri", "")

        database = create_database(active_cfg)

    except Exception as exc:
        return Div(
            [
                Heading("Database", level=2),
                Paragraph("Inspect the active project database."),
                empty_state(
                    "Database is unavailable",
                    f"Templar could not open the configured database: {exc}",
                ),
            ],
            classes=["studio-page", "studio-database"],
        )

    try:
        # --------------------------------------------------
        # Database inspection
        # --------------------------------------------------

        tables = _table_names(database, engine)

        table_cards = []
        total_rows = 0

        for table_name in tables:
            row_count = _table_row_count(database, engine, table_name)
            columns = _table_columns(database, engine, table_name)

            total_rows += row_count

            table_cards.append(
                _build_table_card(table_name, row_count, columns)
            )

        # --------------------------------------------------
        # Summary
        # --------------------------------------------------

        summary_cards = Div(
            [
                _build_summary_card("Engine", engine.upper(), "primary"),
                _build_summary_card("Tables", str(len(tables)), "success"),
                _build_summary_card("Rows",str(total_rows),"warning"),
                _build_summary_card("Connection","Live","danger"),
            ],
            classes=["studio-stat-grid"],
        )

        # --------------------------------------------------
        # Migration output
        # --------------------------------------------------

        migration_output = Div(
            "Migrations have not been run.",
            id="database-migration-output",
            classes=["db-migration-output"],
        )

        # Bind the handler to this page's CLI and output.
        migration_handler = _make_run_migrations_action(cli, migration_output)

        migration_button = Button(
            "Run migrations",
            id="database-migrate-button",
            classes=["db-action-button"],
            type="button",
            on_click=migration_handler,
        )

        actions = Div(
            [
                # Paragraph(
                #     "Migrations",
                #     classes=["db-section-label"]
                # ),
                migration_button,
                migration_output,
            ],
            classes=["db-actions"],
        )

        # --------------------------------------------------
        # Table content
        # --------------------------------------------------

        if not table_cards:
            content = empty_state(
                "No tables found",
                f"The configured database at '{uri}' is connected but has no tables yet.",
            )

        else:
            content = Div(
                [
                    Div(
                        [
                            Heading("Tables", level=3),
                            Paragraph(
                                "Each card shows a table name, row count, and a preview of its columns.",
                                classes=["db-section-copy"],
                            ),
                        ],
                        classes=["db-section-heading"],
                    ),
                    Div(
                        table_cards,
                        classes=["db-table-grid"],
                    ),
                ],
                classes=["db-content"],
            )

        # --------------------------------------------------
        # Page
        # --------------------------------------------------

        return Div(
            [
                Heading("Database", level=2),
                Paragraph(f"Database connection: {uri}"),
                summary_cards,
                actions,
                content,
            ],
            classes=["studio-page", "studio-database"],
        )

    except Exception as exc:
        return Div(
            [
                Heading("Database", level=2),
                Paragraph("Inspect the active project database."),
                empty_state(
                    "Database inspection failed",
                    f"The database connection was opened but inspection failed: {exc}",
                ),
            ],
            classes=["studio-page", "studio-database"],
        )

    finally:
        try:
            database.close()
        except Exception:
            pass