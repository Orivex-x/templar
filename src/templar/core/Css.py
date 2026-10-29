import sys
from typing import Any, Dict, Optional, Union

sys.dont_write_bytecode = True

class CSS:
    def __init__(self, selector: Optional[Union[str, Dict[str, Any]]] = None):
        self.selector: Optional[str] = None
        self.rules: Dict[str, Any] = {}
        self.children: Dict[str, Dict[str, Any]] = {}
        self.variables: Dict[str, Any] = {}
        self.media_queries: Dict[str, Dict[str, Any]] = {}

        if isinstance(selector, dict):
            self.rules.update(selector)
        else:
            self.selector = selector

    # -----------------------------
    # Properties
    # -----------------------------
    def set(self, prop: str, value: str):
        self.rules[prop] = value

        return self

    def var(self, name: str, value: str):
        self.variables[name] = value

        return self

    # -----------------------------
    # Pseudo selectors helpers
    # -----------------------------
    def nested(self, pseudo: str, rules: dict):
        self.children[pseudo] = rules
        
        return self

    def hover(self, rules: dict):
        return self.nested(":hover", rules)

    def active(self, rules: dict):
        return self.nested(":active", rules)

    def focus(self, rules: dict):
        return self.nested(":focus", rules)

    # -----------------------------
    # Media query support
    # -----------------------------
    def media(self, query: str, rules: dict):
        """
        Define media query block.
        rules: dict of selector -> dict of property -> value
        Example:
        css.media("(max-width: 600px)", {"#main-container": {"padding": "10px"}})
        """
        self.media_queries[query] = rules

        return self

    # -----------------------------
    # Render CSS
    # -----------------------------
    def render(self) -> str:
        lines = []

        # Render variables
        if self.variables:
            var_lines = "; ".join(f"--{k}: {v}" for k, v in self.variables.items())
            lines.append(f"{self.selector} {{ {var_lines}; }}")

        # Render normal rules
        if self.rules:
            rules_lines = "; ".join(f"{k}: {v}" for k, v in self.rules.items())
            lines.append(f"{self.selector} {{ {rules_lines}; }}")

        # Render nested pseudo selectors
        for pseudo, pseudo_rules in self.children.items():
            rules_lines = "; ".join(f"{k}: {v}" for k, v in pseudo_rules.items())
            lines.append(f"{self.selector}{pseudo} {{ {rules_lines}; }}")

        # Render media queries
        for query, mq_rules in self.media_queries.items():
            mq_lines = []

            for sel, props in mq_rules.items():
                prop_lines = "; ".join(f"{k}: {v}" for k, v in props.items())
                mq_lines.append(f"{sel} {{ {prop_lines}; }}")

            lines.append(f"@media {query} {{ {' '.join(mq_lines)} }}")

        return "\n".join(lines)

    # -----------------------------
    # jQuery modifier
    # -----------------------------
    @classmethod
    def modify(cls, idOrClassName: str, **props) -> str:
        if not props:
            return ""
        
        cssProps = ",".join(f"'{k}':'" + str(v).replace('\'','\\\'') + "'" for k, v in props.items())

        return f"<script>$('{idOrClassName}').css({{{cssProps}}});</script>"
