# templar/db/Query.py
import sys
import re
import warnings
from typing import Any, Dict, List, Optional, Tuple

from templar.db import db # db facade

sys.dont_write_bytecode = True

class QuerySet:
    def __init__(self, model_cls):
        self.model_cls = model_cls
        self._where: List[str] = []
        self._params: Dict[str, Any] = {}
        self._order: Optional[str] = None
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    def _field(self, name: str) -> str:
        if not isinstance(name, str) or name not in self.model_cls._fields:
            raise ValueError(f"Unknown or unsafe model field: {name!r}")

        return name

    def filter(self, **kwargs):
        for field, value in kwargs.items():
            field = self._field(field)
            placeholder = f"filter_{len(self._params)}"
            self._where.append(f"{field} = :{placeholder}")
            self._params[placeholder] = value

        return self

    def where_raw(self, clause: str, **params):
        """Deprecated alias for :meth:`where_unsafe`."""
        warnings.warn("where_raw() is deprecated; use where_unsafe() for trusted SQL only", DeprecationWarning, stacklevel=2)

        return self.where_unsafe(clause, **params)

    def where_unsafe(self, clause: str, **params):
        """Add trusted raw SQL. Never pass request-controlled text here."""
        if not isinstance(clause, str) or not clause.strip():
            raise ValueError("Raw WHERE clauses must be non-empty strings")

        if not all(isinstance(name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in params):
            raise ValueError("Raw SQL parameter names must be identifiers")

        if set(params) & set(self._params):
            raise ValueError("Raw SQL parameter names must be unique")

        self._where.append(f"({clause})")
        self._params.update(params)

        return self

    def order_by(self, field: str, descending: bool = False):
        """Order by a model field, optionally descending."""
        self._order = f"{self._field(field)} {'DESC' if descending else 'ASC'}"

        return self

    def order_by_unsafe(self, clause: str):
        """Set a trusted raw ORDER BY clause. Never pass request-controlled text."""
        if not isinstance(clause, str) or not clause.strip():
            raise ValueError("Raw ORDER BY clauses must be a non-empty string")

        self._order = clause

        return self

    def limit(self, n: int):
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("limit must be a non-negative integer")

        self._limit = n

        return self

    def offset(self, n: int):
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("offset must be a non-negative integer")

        self._offset = n

        return self

    def _build_sql(self, fields: Optional[List[str]] = None, limit_override: Optional[int] = None) -> Tuple[str, Dict[str, Any]]:
        selected_fields = [self._field(field) for field in fields] if fields else []
        sel = ", ".join(selected_fields) if selected_fields else "*"
        sql = f"SELECT {sel} FROM {self.model_cls._table}"

        if self._where:
            sql += " WHERE " + " AND ".join(self._where)

        if self._order:
            sql += " ORDER BY " + self._order

        effective_limit = self._limit if limit_override is None else limit_override

        if effective_limit is not None:
            sql += f" LIMIT {int(effective_limit)}"

        if self._offset is not None:
            sql += f" OFFSET {int(self._offset)}"

        return sql, self._params.copy()

    def all(self) -> List[Any]:
        sql, params = self._build_sql()
        rows = db.fetchall(sql, params)

        return [self.model_cls(**r) for r in rows]

    def first(self) -> Optional[Any]:
        sql, params = self._build_sql(limit_override=1)
        row = db.fetchone(sql, params)

        return self.model_cls(**row) if row else None

    def count(self) -> int:
        # build count query
        sql = f"SELECT COUNT(1) as cnt FROM {self.model_cls._table}"

        if self._where:
            sql += " WHERE " + " AND ".join(self._where)

        row = db.fetchone(sql, self._params)

        return int(row["cnt"]) if row else 0

    def delete(self) -> None:
        sql = f"DELETE FROM {self.model_cls._table}"

        if self._where:
            sql += " WHERE " + " AND ".join(self._where)

        db.execute(sql, self._params)
