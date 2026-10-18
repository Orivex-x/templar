# templar/db/Models.py
import sys
from typing import Any, Dict
from .ModelMeta import ModelMeta
from .Query import QuerySet
from templar.db import db

sys.dont_write_bytecode = True

class Model(metaclass=ModelMeta):
    _table: str
    _fields: Dict[str, type]
    _relationships: Dict[str, object]

    def __init__(self, **kwargs):
        for f in self._fields:
            setattr(self, f, kwargs.get(f))

        for relationship_name in self._relationships:
            if relationship_name in kwargs:
                setattr(self, relationship_name, kwargs[relationship_name])

    @classmethod
    def objects(cls) -> QuerySet:
        ModelMeta._ensure_table(cls)

        return QuerySet(cls)

    def to_record(self) -> Dict[str, Any]:
        """Return the database representation of this model.

        Subclasses may expose a redacted ``to_dict`` for APIs without
        accidentally omitting fields required by persistence.
        """
        return {k: getattr(self, k, None) for k in self._fields}

    def to_dict(self) -> Dict[str, Any]:
        """Return the default public representation of this model."""
        return self.to_record()

    def save(self) -> None:
        ModelMeta._ensure_table(type(self))
        values = self.to_record()
        pk = values.get("id")

        if pk:
            # update
            sets = ", ".join(f"{k}=:{k}" for k in values if k != "id")
            sql = f"UPDATE {self._table} SET {sets} WHERE id=:id"
            db.execute(sql, values)
        else:
            cols = ", ".join(k for k in values if k != "id")
            params = ", ".join(f":{k}" for k in values if k != "id")
            sql = f"INSERT INTO {self._table} ({cols}) VALUES ({params})"

            # remove id if None
            to_exec = {k: v for k, v in values.items() if k != "id"}
            self.id = db.insert_and_get_id(sql, to_exec)

    def delete(self) -> None:
        ModelMeta._ensure_table(type(self))
        pk = getattr(self, "id", None)

        if not pk:
            raise ValueError("Cannot delete object without id")

        db.execute(f"DELETE FROM {self._table} WHERE id=:id", {"id": pk})
