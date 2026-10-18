import sys
from typing import Dict, Any, Optional

sys.dont_write_bytecode = True

class Provider:
    def __init__(self, cfg: Optional[Dict[str, Any]] = None) -> None:
        self.cfg = cfg or {}

    def deploy(self, source_dir: str, opts: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
