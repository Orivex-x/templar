import sys

sys.dont_write_bytecode = True

class CacheProvider:
    def get(self, key: str):
        raise NotImplementedError
    
    def set(self, key: str, value, ttl=None):
        raise NotImplementedError
    
    def delete(self, key: str):
        raise NotImplementedError
    
    def clear(self):
        raise NotImplementedError

    def clear_prefix(self, prefix: str):
        """Delete only keys beginning with ``prefix``."""
        raise NotImplementedError
