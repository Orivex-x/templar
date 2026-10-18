import json
import sys
from typing import Any, Dict, List

from templar.core.elements.RawHTML import RawHTML

sys.dont_write_bytecode = True


class State:
    """
    Client-side reactive state generated from Python templates.
    """

    _SAFE_ATTRIBUTES = {
        "id", "class", "title", "value", "placeholder", "role", "disabled",
        "hidden", "checked", "selected", "readonly", "required", "maxlength",
        "minlength", "min", "max", "step", "tabindex", "name", "alt",
    }

    def __init__(self, name: str = "app", **initial: Any) -> None:
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError("State names must be valid JavaScript identifiers")

        self.name = name
        self.initial: Dict[str, Any] = initial
        self._bindings: List[Dict[str, str]] = []

    def set(self, key: str, value: Any) -> "State":
        self.initial[key] = value

        return self

    def bind_text(self, key: str, selector: str) -> "State":
        self._bindings.append({"type": "text", "key": key, "selector": selector})

        return self

    def bind_html_unsafe(self, key: str, selector: str) -> "State":
        """Bind trusted, already-sanitized HTML using ``innerHTML``.

        Prefer: meth:`bind_text` for all requests, API, or user-controlled values. This deliberately explicit name
        highlights the XSS boundary.
        """
        self._bindings.append({"type": "html_unsafe", "key": key, "selector": selector})

        return self

    def bind_attr(self, key: str, selector: str, attribute: str) -> "State":
        normalized = attribute.lower() if isinstance(attribute, str) else ""

        if not (
            normalized in self._SAFE_ATTRIBUTES
            or normalized.startswith("aria-")
            or normalized.startswith("data-")
        ):
            raise ValueError(
                f"Unsafe reactive attribute {attribute!r}; use bind_attr_unsafe() only for trusted values"
            )

        self._bindings.append({
            "type": "attr",
            "key": key,
            "selector": selector,
            "attribute": attribute
        })

        return self

    def bind_attr_unsafe(self, key: str, selector: str, attribute: str) -> "State":
        """Bind a trusted value to any attribute, including event/URL sinks."""
        if not isinstance(attribute, str) or not attribute:
            raise ValueError("Reactive attribute names must be non-empty strings")

        self._bindings.append({
            "type": "attr_unsafe",
            "key": key,
            "selector": selector,
            "attribute": attribute,
        })

        return self

    def bind_input(self, key: str, selector: str, event: str = "input") -> "State":
        self._bindings.append({
            "type": "input",
            "key": key,
            "selector": selector,
            "event": event
        })

        return self

    def render(self) -> RawHTML:
        state_json = self._json_for_script(self.initial)
        bindings_json = self._json_for_script(self._bindings)
        api_name = f"TemplarState_{self.name}"

        script = f"""
<script>
(function () {{
  const state = {state_json};
  const bindings = {bindings_json};

  function applyBinding(binding) {{
    const value = state[binding.key] ?? "";
    document.querySelectorAll(binding.selector).forEach(function (node) {{
      if (binding.type === "text") node.textContent = value;
      if (binding.type === "html_unsafe") node.innerHTML = value;
      if (binding.type === "attr") node.setAttribute(binding.attribute, value);
      if (binding.type === "attr_unsafe") node.setAttribute(binding.attribute, value);
      if (binding.type === "input") node.value = value;
    }});
  }}

  function render(key) {{
    bindings
      .filter(function (binding) {{ return !key || binding.key === key; }})
      .forEach(applyBinding);
  }}

  bindings
    .filter(function (binding) {{ return binding.type === "input"; }})
    .forEach(function (binding) {{
      document.querySelectorAll(binding.selector).forEach(function (node) {{
        node.addEventListener(binding.event || "input", function () {{
          state[binding.key] = node.value;
          render(binding.key);
        }});
      }});
    }});

  window.{api_name} = {{
    get: function (key) {{ return state[key]; }},
    set: function (key, value) {{
      state[key] = value;
      render(key);
      return value;
    }},
    snapshot: function () {{ return Object.assign({{}}, state); }}
  }};

  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", function () {{ render(); }});
  }} else {{
    render();
  }}
}})();
</script>
"""
        return RawHTML(script)

    @staticmethod
    def _json_for_script(value: Any) -> str:
        """Serialize JSON safely for an executable HTML script element."""
        return (
            json.dumps(value, ensure_ascii=False)
            .replace("&", "\\u0026")
            .replace("<", "\\u003C")
            .replace(">", "\\u003E")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )
