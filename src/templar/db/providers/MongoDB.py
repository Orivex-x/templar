"""Removed MongoDB adapter.

Templar's ORM is deliberately SQL-based; MongoDB has a different query and
transaction model and is not presented as a supported database engine.
"""


class MongoDBProvider:
    def __init__(self, *_args, **_kwargs) -> None:
        raise RuntimeError(
            "MongoDB is not supported by Templar's SQL ORM. "
            "Use sqlite, postgresql, or mysql."
        )
