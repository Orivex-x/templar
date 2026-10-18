import sys, re
from typing import Dict, Tuple, Optional

sys.dont_write_bytecode = True

class Router:
    """
    Central registry for Templar routes.
    Each route maps explicitly to a template file.
    """

    def __init__(self, config) -> None:
        self._routes: Dict[re.Pattern, Dict[str, str]] = {}
        self.default_route: str = getattr(config, "default_route", "index")

    def add(self, path_pattern: str, template_file: str) -> None:
        """
        Register a new route.
        path_pattern: URL pattern (supports <param> for dynamic segments)
        template_file: name of the template file (with or without extension)
        """
        if not template_file.endswith(".templar.py"):
            template_file += ".templar.py"

        parameter_matches = list(re.finditer(r"<(\w+)>", path_pattern))
        cursor = 0
        regex_parts = []

        for match in parameter_matches:
            regex_parts.append(re.escape(path_pattern[cursor:match.start()]))
            regex_parts.append(f"(?P<{match.group(1)}>[^/]+)")
            cursor = match.end()

        regex_parts.append(re.escape(path_pattern[cursor:]))
        regex_pattern = "".join(regex_parts)
        compiled = re.compile(f"^{regex_pattern}/?$")

        if compiled in self._routes:
            raise ValueError(f"Duplicate route definition: {path_pattern}")

        self._routes[compiled] = {
            "template_file": template_file,
            "pattern": path_pattern,
            "parameter_count": len(parameter_matches),
            "literal_length": len(re.sub(r"<(\w+)>", "", path_pattern)),
        }

    def match(self, path: str) -> Tuple[Optional[str], Dict[str, str]]:
        """
        Match the request path to a registered route.
        Returns (template_file, params) or (None, {}).
        """
        ranked_routes = sorted(
            self._routes.items(),
            key=lambda item: (item[1]["parameter_count"], -item[1]["literal_length"]),
        )

        for regex, info in ranked_routes:
            match = regex.match(path)

            if match:
                return info["template_file"], match.groupdict()
            
        return None, {}

    def merge(self, other: "Router", *, override: bool = True) -> None:
        """Merge another router's definitions into this router.

        This lets the CLI retain its template-discovered routes while an
        application's ``app.py`` contributes custom routes. When both routers
        define the same path pattern, the application router wins by default.
        """
        if not isinstance(other, Router):
            raise TypeError("Can only merge another Router")

        for regex, info in other._routes.items():
            existing = next(
                (pattern for pattern, candidate in self._routes.items()
                 if candidate["pattern"] == info["pattern"]),
                None,
            )

            if existing is not None:
                if not override:
                    continue

                del self._routes[existing]

            self._routes[regex] = dict(info)

    @property
    def routes(self) -> Dict[re.Pattern, str]:
        """For CLI: regex -> template filename"""
        return {regex: info["template_file"] for regex, info in self._routes.items()}
