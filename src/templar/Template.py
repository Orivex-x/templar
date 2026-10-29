import sys
import threading
from pathlib import Path

sys.dont_write_bytecode = True

class Template:
    def __init__(self, path):
        self.path = Path(path)
        self._last_mtime = None
        self._render_func = None
        self._reload_lock = threading.RLock()

    def get_element_tree(self, **context):
        """
        Load and execute the template, passing context variables.
        Auto-reloads if the template file has changed.
        """
        mtime = self.path.stat().st_mtime

        if self._render_func is None or self._last_mtime != mtime:
            with self._reload_lock:
                mtime = self.path.stat().st_mtime

                if self._render_func is None or self._last_mtime != mtime:
                    project_root = str(self.path.parent.parent)
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)

                    namespace = {
                        "__file__": str(self.path),
                        "__name__": "__templar_template__",
                        "__package__": None,
                    }

                    try:
                        exec(self.path.read_text(), namespace)
                    except Exception as e:
                        raise RuntimeError(f"Error executing template {self.path}: {e}")

                    if "render" not in namespace:
                        raise ValueError(f"{self.path} must define a render() function")

                    self._render_func = namespace["render"]
                    self._last_mtime = mtime

        return self._render_func(**context)