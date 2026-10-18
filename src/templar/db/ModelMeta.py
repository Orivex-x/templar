import sys, re, weakref
from contextlib import nullcontext
from typing import Any, Dict, Type

from templar.db import db  # this will be your Database façade (see next file)
from templar.db.Query import QuerySet
from templar.db.Relationships import ForeignKey, OneToOne, Relationship, Reverse

sys.dont_write_bytecode = True

PY_TO_SQL = {
    int: "INTEGER",
    float: "REAL",
    str: "TEXT",
    bool: "INTEGER",  # 0/1
}

def _col_type_for(py_type):
    return PY_TO_SQL.get(py_type, "TEXT")

class ModelMeta(type):
    """Create a table when a class is defined (if the provider supports DDL)."""

    def __new__(mcs, name, bases, attrs):
        if name == "Model":
            return super().__new__(mcs, name, bases, attrs)

        annotations = attrs.get("__annotations__", {})
        declared_fields = attrs.get("_fields", {})

        if not isinstance(declared_fields, dict):
            raise TypeError("Model _fields must be a dictionary")

        # Model subclasses inherit their storage contract.  In particular, ``class Account(User): display_name: str``
        # must not discard the identity, credential, and authorization fields declared by User.
        inherited_fields = {}
        inherited_relationships = {}
        inherited_unique_fields = []
        inherited_required_fields = []

        for base in reversed(bases):
            inherited_fields.update(getattr(base, "_fields", {}))
            inherited_relationships.update(getattr(base, "_relationships", {}))

            for field_name in getattr(base, "_unique_fields", ()):
                if field_name not in inherited_unique_fields:
                    inherited_unique_fields.append(field_name)

            for field_name in getattr(base, "_required_fields", ()):
                if field_name not in inherited_required_fields:
                    inherited_required_fields.append(field_name)

        table = (
            attrs.get("__tablename__", None)
            or attrs.get("_table", None)
            or re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        )

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            raise ValueError("Model table names must be SQL identifiers")

        relationships = {
            **inherited_relationships,
            **{key: value for key, value in attrs.items() if isinstance(value, Relationship)},
        }

        fields = {**inherited_fields, **declared_fields, **annotations}

        if not all(isinstance(field_name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field_name) for field_name in fields):
            raise ValueError("Model field names must be SQL identifiers")

        for relation_name, relation in relationships.items():
            if isinstance(relation, ForeignKey):
                fields.setdefault(f"{relation_name}_id", int)

        attrs["_table"] = table
        attrs["_fields"] = fields
        attrs["_relationships"] = relationships

        # Keep database objects, not ``id(database)`` integers: object IDs can be reused after a server/database is closed,
        # which would otherwise skip schema setup for an unrelated new connection.
        attrs["_schema_databases"] = weakref.WeakSet()
        cls = super().__new__(mcs, name, bases, attrs)

        # ensure default id exists
        if "id" not in cls._fields:
            cls._fields["id"] = int

        declared_unique_fields = attrs.get("__unique_fields__", ())

        if isinstance(declared_unique_fields, str) or not isinstance(declared_unique_fields, (tuple, list, set)):
            raise TypeError("__unique_fields__ must be a collection of model field names")

        unique_fields = tuple(dict.fromkeys([*inherited_unique_fields, *declared_unique_fields]))

        if isinstance(unique_fields, str) or not isinstance(unique_fields, (tuple, list, set)):
            raise TypeError("__unique_fields__ must be a collection of model field names")

        if not all(isinstance(field_name, str) and field_name in cls._fields for field_name in unique_fields):
            raise ValueError("__unique_fields__ may contain only declared model fields")

        cls._unique_fields = tuple(unique_fields)

        declared_required_fields = attrs.get("__required_fields__", ())

        if isinstance(declared_required_fields, str) or not isinstance(declared_required_fields, (tuple, list, set)):
            raise TypeError("__required_fields__ must be a collection of model field names")

        required_fields = tuple(dict.fromkeys([*inherited_required_fields, *declared_required_fields]))

        if not all(isinstance(field_name, str) and field_name in cls._fields for field_name in required_fields):
            raise ValueError("__required_fields__ may contain only declared model fields")

        cls._required_fields = required_fields

        for relation_name, relation in relationships.items():
            if isinstance(relation, ForeignKey):
                reverse_name = f"{name.lower()}_set"

                if not hasattr(relation.to_model, reverse_name):
                    setattr(relation.to_model, reverse_name, Reverse(cls, relation_name))

        return cls

    @staticmethod
    def _ensure_table(cls: Type["Model"], *, allow_migration: bool = False) -> None:
        cols = []
        database = db.get()

        if database in cls._schema_databases:
            return

        provider = database._provider
        dialect = type(provider).__name__
        table_existed = ModelMeta._table_exists(database, cls._table, dialect)

        for name, ptype in cls._fields.items():
            if name == "id":
                if dialect == "PostgreSQLProvider":
                    cols.append("id SERIAL PRIMARY KEY")
                elif dialect == "MySQLProvider":
                    cols.append("id INTEGER PRIMARY KEY AUTO_INCREMENT")
                else:
                    cols.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
            else:
                sql_type = _col_type_for(ptype)
                relation = getattr(cls, name[:-3], None) if name.endswith("_id") else None

                if isinstance(relation, ForeignKey):
                    nullability = "" if relation.null else " NOT NULL"
                    uniqueness = " UNIQUE" if isinstance(relation, OneToOne) else ""
                    cascade = " ON DELETE CASCADE" if relation.cascade_delete else ""
                    cols.append(
                        f"{name} {sql_type}{nullability}{uniqueness} "
                        f"REFERENCES {relation.to_model._table}(id){cascade}"
                    )
                else:
                    required = " NOT NULL" if name in cls._required_fields else ""
                    cols.append(f"{name} {sql_type}{required}")

        sql = f"CREATE TABLE IF NOT EXISTS {cls._table} ({', '.join(cols)});"
        database.execute(sql)

        if table_existed:
            # Request/model access may inspect an existing schema but must never rebuild it.  Run
            # ``templar migrate user-schema`` to apply the reviewed, tracked compatibility migration.
            # Detect conflicts with framework-reserved index names before an SQLite rebuild can preserve them and mask
            # uniqueness creation.
            ModelMeta._validate_named_unique_indexes(cls, database, dialect)
            ModelMeta._enforce_required_fields(
                cls, database, dialect, cols, apply=allow_migration
            )
            ModelMeta._enforce_unique_fields(cls, database, dialect, apply=allow_migration)

        # Named indexes make uniqueness both repeatable and upgradeable for tables created before ``__unique_fields__``
        # existed. CREATE TABLE IF NOT EXISTS alone never changes an existing schema.
        if table_existed and not allow_migration:
            cls._schema_databases.add(database)

            return

        for field_name in cls._unique_fields:
            index_name = f"{cls._table}_{field_name}_uniq"

            try:
                if ModelMeta._named_unique_index_state(cls, database, dialect, index_name, field_name) is True:
                    continue

                if dialect == "MySQLProvider":
                    database.execute(f"CREATE UNIQUE INDEX {index_name} ON {cls._table} ({field_name})")
                else:
                    database.execute(
                        f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
                        f"ON {cls._table} ({field_name})"
                    )
            except Exception as exc:
                raise RuntimeError(
                    f"Could not enforce unique {cls._table}.{field_name}; "
                    "resolve duplicate existing records before starting the application"
                ) from exc

        ModelMeta._enforce_unique_fields(cls, database, dialect, apply=False)
        cls._schema_databases.add(database)

    def migrate_schema(cls: Type["Model"], database) -> None:
        """Apply required-field/unique upgrades using an explicit migration."""
        with db.use(database):
            # Prior validation-only access must not suppress this explicit operation for the same process/database.
            cls._schema_databases.discard(database)
            ModelMeta._ensure_table(cls, allow_migration=True)

    @staticmethod
    def _table_exists(database, table: str, dialect: str) -> bool:
        if dialect == "SQLiteProvider":
            return database.fetchone(
                "SELECT 1 AS present FROM sqlite_master WHERE type='table' AND name=:table",
                {"table": table},
            ) is not None
        if dialect == "PostgreSQLProvider":
            return database.fetchone(
                "SELECT 1 AS present FROM information_schema.tables "
                "WHERE table_schema=current_schema() AND table_name=:table",
                {"table": table},
            ) is not None
        if dialect == "MySQLProvider":
            return database.fetchone(
                "SELECT 1 AS present FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name=:table",
                {"table": table},
            ) is not None

        return False

    @staticmethod
    def _enforce_required_fields(
        cls: Type["Model"], database, dialect: str, cols: list[str], *, apply: bool = False
    ) -> None:
        """Upgrade nullable required fields after checking existing data.

        SQLite requires a table rebuild for ``NOT NULL`` changes; PostgreSQL
        and MySQL support provider-native ALTER statements.  Do not silently
        discard legacy rows with null identity/credential values.
        """
        if not cls._required_fields:
            return

        if dialect == "SQLiteProvider":
            metadata = {
                row["name"]: bool(row["notnull"])
                for row in database.fetchall(f"PRAGMA table_info({cls._table})")
            }
        elif dialect == "PostgreSQLProvider":
            metadata = {
                row["column_name"]: row["is_nullable"] == "NO"
                for row in database.fetchall(
                    "SELECT column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_schema=current_schema() AND table_name=:table",
                    {"table": cls._table},
                )
            }
        elif dialect == "MySQLProvider":
            metadata = {
                row["column_name"]: row["is_nullable"] == "NO"
                for row in database.fetchall(
                    "SELECT column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_schema=DATABASE() AND table_name=:table",
                    {"table": cls._table},
                )
            }
        else:
            return

        missing = [field for field in cls._required_fields if field not in metadata]

        if missing:
            raise RuntimeError(
                f"Existing table {cls._table} is missing required columns: {', '.join(missing)}; "
                "run a database migration before starting the application"
            )

        nullable = [field for field in cls._required_fields if not metadata[field]]

        if not nullable:
            return

        null_row = database.fetchone(
            f"SELECT id FROM {cls._table} WHERE " + " OR ".join(f"{field} IS NULL" for field in nullable) + " LIMIT 1"
        )

        if null_row is not None:
            raise RuntimeError(
                f"Cannot enforce required fields on {cls._table}; existing row id={null_row.get('id')} contains NULL data"
            )

        if not apply:
            raise RuntimeError(
                f"Existing table {cls._table} has nullable required fields: {', '.join(nullable)}; "
                f"run {ModelMeta._schema_migration_hint(cls)} before serving requests"
            )

        try:
            if dialect == "SQLiteProvider":
                temp_table = f"__templar_required_{cls._table}"
                # SQLite cannot ALTER a column to NOT NULL. Foreign key checks are disabled only for this controlled
                # rebuild and restored immediately afterwards.
                schema_objects = database.fetchall(
                    "SELECT type, name, sql FROM sqlite_master "
                    "WHERE tbl_name=:table AND type IN ('index', 'trigger') AND sql IS NOT NULL "
                    "ORDER BY type, name",
                    {"table": cls._table},
                )
                transaction_active = bool(getattr(database._transaction_state, "active", False))

                # A CLI migration may already own the transaction so it can atomically record completion. In that case
                # the caller has disabled foreign keys before BEGIN; SQLite cannot change the pragma from inside an
                # active transaction.
                if not transaction_active:
                    database.execute("PRAGMA foreign_keys = OFF")

                try:
                    transaction = nullcontext() if transaction_active else database.transaction()

                    with transaction:
                        database.execute(f"CREATE TABLE {temp_table} ({', '.join(cols)})")
                        field_list = ", ".join(cls._fields)
                        database.execute(
                            f"INSERT INTO {temp_table} ({field_list}) SELECT {field_list} FROM {cls._table}"
                        )
                        database.execute(f"DROP TABLE {cls._table}")
                        database.execute(f"ALTER TABLE {temp_table} RENAME TO {cls._table}")

                        # SQLite drops table-owned indexes and triggers during a rebuild. Restore every user-defined SQL
                        # object; framework unique indexes are added afterwards.
                        for schema_object in schema_objects:
                            database.execute(schema_object["sql"])
                finally:
                    if not transaction_active:
                        database.execute("PRAGMA foreign_keys = ON")
            elif dialect == "PostgreSQLProvider":
                for field in nullable:
                    database.execute(f"ALTER TABLE {cls._table} ALTER COLUMN {field} SET NOT NULL")
            elif dialect == "MySQLProvider":
                for field in nullable:
                    database.execute(
                        f"ALTER TABLE {cls._table} MODIFY COLUMN {field} "
                        f"{_col_type_for(cls._fields[field])} NOT NULL"
                    )
        except Exception as exc:
            raise RuntimeError(
                f"Could not enforce required fields on existing table {cls._table}; run a database migration"
            ) from exc

    @staticmethod
    def _schema_migration_hint(cls: Type["Model"]) -> str:
        """Return the explicit CLI invocation for this model's schema upgrade."""
        if cls.__module__ == "templar.auth.User" and cls.__name__ == "User":
            return "`templar migrate user-schema`"

        return f"`templar migrate user-schema --model {cls.__module__}:{cls.__qualname__}`"

    @staticmethod
    def _named_unique_index_state(cls: Type["Model"], database, dialect: str, index_name: str, field_name: str):
        """Return None, or whether a named index is the required unique index."""
        if dialect == "SQLiteProvider":
            row = next(
                (item for item in database.fetchall(f"PRAGMA index_list({cls._table})") if item.get("name") == index_name),
                None,
            )

            if row is None:
                return None

            escaped_name = index_name.replace("'", "''")
            columns = database.fetchall(f"PRAGMA index_info('{escaped_name}')")

            return bool(row.get("unique")) and len(columns) == 1 and columns[0]["name"] == field_name

        if dialect == "PostgreSQLProvider":
            row = database.fetchone(
                "SELECT index_definition.indisunique AS is_unique, "
                "array_length(index_definition.indkey, 1) AS column_count, attribute.attname AS column_name "
                "FROM pg_class index_class "
                "JOIN pg_index index_definition ON index_definition.indexrelid=index_class.oid "
                "JOIN pg_class table_definition ON table_definition.oid=index_definition.indrelid "
                "JOIN pg_namespace namespace ON namespace.oid=table_definition.relnamespace "
                "LEFT JOIN pg_attribute attribute ON attribute.attrelid=table_definition.oid "
                "AND attribute.attnum = ANY(index_definition.indkey) "
                "WHERE namespace.nspname=current_schema() AND table_definition.relname=:table "
                "AND index_class.relname=:index_name",
                {"table": cls._table, "index_name": index_name},
            )

            if row is None:
                return None

            return bool(row["is_unique"]) and row["column_count"] == 1 and row["column_name"] == field_name
        if dialect == "MySQLProvider":
            rows = database.fetchall(
                "SELECT non_unique, column_name FROM information_schema.statistics "
                "WHERE table_schema=DATABASE() AND table_name=:table AND index_name=:index_name",
                {"table": cls._table, "index_name": index_name},
            )

            if not rows:
                return None

            return len(rows) == 1 and not rows[0]["non_unique"] and rows[0]["column_name"] == field_name

        return None

    @staticmethod
    def _validate_named_unique_indexes(cls: Type["Model"], database, dialect: str) -> None:
        """Reject application indexes that occupy Templar's reserved names."""
        for field_name in cls._unique_fields:
            index_name = f"{cls._table}_{field_name}_uniq"

            if ModelMeta._named_unique_index_state(cls, database, dialect, index_name, field_name) is False:
                raise RuntimeError(
                    f"Existing index {index_name} conflicts with Templar's required unique index on "
                    f"{cls._table}.{field_name}; rename or remove it, then run "
                    f"{ModelMeta._schema_migration_hint(cls)}"
                )

    @staticmethod
    def _enforce_unique_fields(
        cls: Type["Model"], database, dialect: str, *, apply: bool = False
    ) -> None:
        """Validate identity uniqueness without mutating runtime schemas."""
        if not cls._unique_fields:
            return

        unique_columns: set[str] = set()

        if dialect == "SQLiteProvider":
            for index in database.fetchall(f"PRAGMA index_list({cls._table})"):
                if not index.get("unique"):
                    continue

                columns = database.fetchall(f"PRAGMA index_info({index['name']})")

                if len(columns) == 1:
                    unique_columns.add(columns[0]["name"])
        elif dialect == "PostgreSQLProvider":
            rows = database.fetchall(
                "SELECT attribute.attname AS column_name "
                "FROM pg_index index_definition "
                "JOIN pg_class table_definition ON table_definition.oid=index_definition.indrelid "
                "JOIN pg_namespace namespace ON namespace.oid=table_definition.relnamespace "
                "JOIN pg_attribute attribute ON attribute.attrelid=table_definition.oid "
                "AND attribute.attnum = ANY(index_definition.indkey) "
                "WHERE index_definition.indisunique AND array_length(index_definition.indkey, 1)=1 "
                "AND namespace.nspname=current_schema() AND table_definition.relname=:table",
                {"table": cls._table},
            )
            unique_columns = {row["column_name"] for row in rows}
        elif dialect == "MySQLProvider":
            rows = database.fetchall(
                "SELECT index_name, column_name FROM information_schema.statistics "
                "WHERE table_schema=DATABASE() AND table_name=:table AND non_unique=0 ",
                {"table": cls._table},
            )
            index_columns: dict[str, list[str]] = {}

            for row in rows:
                index_columns.setdefault(row["index_name"], []).append(row["column_name"])

            unique_columns = {
                columns[0] for columns in index_columns.values() if len(columns) == 1
            }
        else:
            return

        missing = [field for field in cls._unique_fields if field not in unique_columns]

        if missing and not apply:
            raise RuntimeError(
                f"Existing table {cls._table} is missing unique constraints for: {', '.join(missing)}; "
                f"run {ModelMeta._schema_migration_hint(cls)} before serving requests"
            )
