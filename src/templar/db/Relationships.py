"""Relationship descriptors for Templar's SQL ORM."""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from templar.db.Models import Model


class Relationship:
    """Base descriptor shared by model relationships."""

    def __init__(self, to_model: type, name: str = None):
        self.to_model = to_model
        self.name = name
        self.from_model = None

    def __set_name__(self, owner, name: str) -> None:
        self.from_model = owner
        if self.name is None:
            self.name = name


class ForeignKey(Relationship):
    """A many-to-one relation persisted as ``<relationship>_id``."""

    def __init__(
        self,
        to_model: type,
        name: str = None,
        cascade_delete: bool = False,
        null: bool = False,
    ):
        super().__init__(to_model, name)
        self.cascade_delete = cascade_delete
        self.null = null

    @property
    def id_field(self) -> str:
        return f"{self.name}_id"

    @property
    def cache_field(self) -> str:
        return f"_{self.name}_cached_relation"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        related_id = getattr(obj, self.id_field, None)
        cached = getattr(obj, self.cache_field, None)

        if cached is not None and getattr(cached, "id", None) == related_id:
            return cached

        if related_id is None:
            return None

        related = self.to_model.objects().filter(id=related_id).first()
        setattr(obj, self.cache_field, related)

        return related

    def __set__(self, obj, value) -> None:
        if value is None:
            setattr(obj, self.id_field, None)
            setattr(obj, self.cache_field, None)

            return

        if not isinstance(value, self.to_model):
            raise TypeError(f"Expected {self.to_model.__name__} instance")

        if getattr(value, "id", None) is None:
            raise ValueError("Related objects must be saved before assignment")

        setattr(obj, self.id_field, value.id)
        setattr(obj, self.cache_field, value)


class OneToOne(ForeignKey):
    """A foreign key with a unique relationship ID column."""

    def __init__(self, to_model: type, name: str = None, cascade_delete: bool = True, null: bool = False):
        super().__init__(to_model, name, cascade_delete=cascade_delete, null=null)


class ManyToMany(Relationship):
    """A many-to-many relation backed by an automatically-created join table."""

    def __init__(self, to_model: type, name: str = None, through_model: type = None, cascade_delete: bool = False):
        if through_model is not None:
            raise NotImplementedError(
                "Explicit through models are not supported; omit through_model "
                "to use Templar's automatic join table."
            )

        super().__init__(to_model, name)
        self.through_model = through_model
        self.cascade_delete = cascade_delete

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return ManyToManyManager(self, obj)


class ManyToManyManager:
    def __init__(self, relationship: ManyToMany, from_obj):
        self.relationship = relationship
        self.from_obj = from_obj
        self.to_model = relationship.to_model

    @property
    def _table(self) -> str:
        return self.relationship.through_model._table if self.relationship.through_model else f"{self.relationship.from_model._table}_{self.relationship.name}"

    @property
    def _source_column(self) -> str:
        return f"{self.relationship.from_model._table}_id"

    @property
    def _target_column(self) -> str:
        return f"{self.relationship.name}_id"

    def _require_saved_source(self) -> None:
        if getattr(self.from_obj, "id", None) is None:
            raise ValueError("Save the source object before managing relationships")

    def _ensure_join_table(self) -> None:
        from templar.db import db

        cascade = " ON DELETE CASCADE" if self.relationship.cascade_delete else ""
        db.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            f"{self._source_column} INTEGER NOT NULL REFERENCES {self.relationship.from_model._table}(id){cascade}, "
            f"{self._target_column} INTEGER NOT NULL REFERENCES {self.to_model._table}(id){cascade}, "
            f"UNIQUE ({self._source_column}, {self._target_column})"
            ")"
        )

    def all(self) -> List["Model"]:
        from templar.db import db

        self._require_saved_source()
        self._ensure_join_table()

        rows = db.fetchall(
            f"SELECT {self.to_model._table}.* FROM {self.to_model._table} "
            f"INNER JOIN {self._table} ON {self.to_model._table}.id = {self._table}.{self._target_column} "
            f"WHERE {self._table}.{self._source_column} = :source_id",
            {"source_id": self.from_obj.id},
        )

        return [self.to_model(**row) for row in rows]

    def add(self, obj: "Model") -> None:
        from templar.db import db

        self._require_saved_source()

        if not isinstance(obj, self.to_model):
            raise TypeError(f"Expected {self.to_model.__name__} instance")

        if getattr(obj, "id", None) is None:
            raise ValueError("Related objects must be saved before assignment")

        self._ensure_join_table()
        existing = db.fetchone(
            f"SELECT 1 AS present FROM {self._table} WHERE {self._source_column} = :source_id "
            f"AND {self._target_column} = :target_id",
            {"source_id": self.from_obj.id, "target_id": obj.id},
        )

        if existing is None:
            db.execute(
                f"INSERT INTO {self._table} ({self._source_column}, {self._target_column}) "
                "VALUES (:source_id, :target_id)",
                {"source_id": self.from_obj.id, "target_id": obj.id},
            )

    def remove(self, obj: "Model") -> None:
        from templar.db import db

        self._require_saved_source()

        if not isinstance(obj, self.to_model):
            raise TypeError(f"Expected {self.to_model.__name__} instance")

        self._ensure_join_table()

        db.execute(
            f"DELETE FROM {self._table} WHERE {self._source_column} = :source_id "
            f"AND {self._target_column} = :target_id",
            {"source_id": self.from_obj.id, "target_id": obj.id},
        )

    def clear(self) -> None:
        from templar.db import db

        self._require_saved_source()
        self._ensure_join_table()

        db.execute(
            f"DELETE FROM {self._table} WHERE {self._source_column} = :source_id",
            {"source_id": self.from_obj.id},
        )

    def count(self) -> int:
        return len(self.all())


class Reverse:
    """Reverse accessor automatically added for foreign-key relations."""

    def __init__(self, from_model: type, relationship_name: str):
        self.from_model = from_model
        self.relationship_name = relationship_name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return _BoundReverse(self, obj)

    def all(self, obj) -> List["Model"]:
        if getattr(obj, "id", None) is None:
            return []

        return self.from_model.objects().filter(**{f"{self.relationship_name}_id": obj.id}).all()

    def count(self, obj) -> int:
        return len(self.all(obj))


class _BoundReverse:
    def __init__(self, reverse: Reverse, obj):
        self.reverse = reverse
        self.obj = obj

    def all(self):
        return self.reverse.all(self.obj)

    def count(self):
        return self.reverse.count(self.obj)
