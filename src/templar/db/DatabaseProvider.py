import sys
from typing import Any, Dict, List

sys.dont_write_bytecode = True

class DatabaseProvider:
    engine: str = "base"

    def execute(self, sql: str, params: Dict[str, Any] = None) -> None:
        raise NotImplementedError

    def insert_and_get_id(self, sql: str, params: Dict[str, Any] = None) -> int:
        """Insert one row and return its generated integer primary key."""
        raise NotImplementedError

    def fetchone(self, sql: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def fetchall(self, sql: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def begin_transaction(self):
        raise NotImplementedError

    def commit(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError
