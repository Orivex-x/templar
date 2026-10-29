import sys, html, re, uuid
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlsplit

from .RawHTML import RawHTML
from ..security.SafeString import SafeString
from ..Javascript import Javascript
from ..Css import CSS

sys.dont_write_bytecode = True

SELF_CLOSING_TAGS = {"img", "input", "link", "meta", "br", "hr"}
_ATTRIBUTE_NAME = re.compile(r"^[A-Za-z_:][A-Za-z0-9:_.-]*$")
_TAG_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
_UNSAFE_ATTRIBUTE_NAMES = {"srcdoc"}
_URL_ATTRIBUTE_NAMES = {"action", "background", "cite", "data", "formaction", "href", "poster", "src", "srcset", "xlink:href"}
_SAFE_URL_SCHEMES = {"", "http", "https", "mailto", "tel"}

class Element:
    def __init__(
        self,
        tag: str,
        content: Optional[Union[str, RawHTML, "Element", List[Any]]] = None,
        id: Optional[str] = None,
        classes: Optional[List[str]] = None,
        **props
    ) -> None:
        if not isinstance(tag, str) or not _TAG_NAME.fullmatch(tag):
            raise ValueError(f"Invalid HTML tag name: {tag!r}")

        self.tag: str = tag
        self.event_handlers: Dict[str, Any] = {}
        self.global_id = id or f"el-{uuid.uuid4().hex[:10]}"

        for key, value in props.items():
            if key.startswith("on_") and callable(value):
                self.event_handlers[key[3:].lower()] = value

        self.props: Dict[str, Any] = self._normalize_props(props)

        self._capture_event_handlers(props)
        self.state: Dict[str, Any] = {}

        # Parent element reference
        self.parent: Optional[Element] = None

        # Normalize classes -> "class" attribute
        if classes:
            self.props["class"] = " ".join(classes)

        # Ensure an element id exists so the framework generated JS has a selector
        if id:
            self.props["id"] = id
        else:
            self.props["id"] = self.global_id

        # Internal metadata for event bridge
        if self.event_handlers:
            self.props["data-templar-component"] = self.global_id
            self.props["data-templar-events"] = ",".join(sorted(self.event_handlers.keys()))

        # Normalize content -> always a list
        if content is None:
            self.content: List[Any] = []
        elif isinstance(content, (str, RawHTML, Element)):
            self.content = [content]
        elif isinstance(content, list):
            self.content = content
        else:
            self.content = [content]

        # Assign self as parent for any child Elements
        for c in self.content:
            if isinstance(c, Element):
                c.parent = self

        from templar.core.LiveElementRegistry import LiveElementRegistry
        LiveElementRegistry.register(self)

        # Scoped CSS & JS (only if id is provided)
        self.style: Optional[CSS] = CSS(f"#{self.props['id']}") if self.props.get("id") else None
        self.script: Optional[Javascript] = Javascript(f"#{self.props['id']}") if self.props.get("id") else None

        # Allow subclasses to provide defaults
        if self.style:
            self.default_styles(self.style)

        if self.script:
            self.default_scripts(self.script)

        # Lifecycle hook
        self.on_init()

    def _normalize_props(self, props: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}

        for key, value in props.items():
            if key.startswith("on_") and callable(value):
                # Event callbacks are handled separately and are never rendered as HTML attributes
                continue

            attr = "class" if key == "class_" else key.replace("_", "-")
            normalized[attr] = value

        return normalized

    def _capture_event_handlers(self, props: Dict[str, Any]) -> None:
        for key, value in props.items():
            if key.startswith("on_") and callable(value):
                self.event_handlers[key[3:].lower()] = value

    # -----------------------------
    # Helper to add children dynamically
    # -----------------------------
    def add_child(self, child: Any) -> None:
        if isinstance(child, Element):
            child.parent = self

        self.content.append(child)

    # -----------------------------
    # Default style/script hooks
    # -----------------------------
    def default_styles(self, style: CSS):
        """Subclasses can override to provide scoped default styles."""
        pass

    def default_scripts(self, script: Javascript):
        """Subclasses can override to provide scoped default scripts."""
        pass

    # -----------------------------
    # Lifecycle hooks
    # -----------------------------
    def on_init(self):
        """Called when the component is initialized."""
        pass

    def on_update(self, **new_props):
        """Called when component props/state change."""
        self.props.update(new_props)
        self.state.update(new_props)
        self.update_dom()

    def on_destroy(self):
        """Called before the component is removed."""
        pass

    # -----------------------------
    # Rendering hooks
    # -----------------------------
    def before_render(self):
        """Generic logging for element initialization/building."""
        attrs = {k: v for k, v in self.props.items() if v is not None}
        text = f"[{type(self).__name__}] Initialized"
        
        if attrs:
            text += " " + ", ".join(f"{k}={v}" for k, v in attrs.items())

    # -----------------------------
    # Reactive event bridge
    # -----------------------------
    def render_event_bridge(self) -> str:
        if not self.event_handlers:
            return ""

        script = Javascript(scope=f"#{self.props['id']}")

        js = f"""
(function() {{
    const el = document.getElementById("{self.props['id']}");

    if (!el) return;
    
    el.addEventListener("click", function(event) {{
        const target = event.target.closest("button");
        if (!target) return;
        
        const payload = {{
            component_id: "{self.global_id}",
            event_name: "click",
            action: target.dataset.action ?? null,
            task_id: target.dataset.taskId ?? null,
            text: target.textContent ?? null
        }};
        
        fetch("/__templar_reactive__", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify(payload)
        }})
        .then(response => response.json())
        .then(data => {{
            if (data && data.html) {{
                const root = document.getElementById("{self.props['id']}");
                if (root) root.innerHTML = data.html;
            }}
        }})
        .catch(err => {{
            console.error("Templar reactive event failed:", err);
        }});
    }});
}})();
        """
        script._add_snippet(js)

        return script.render(include_script_tags=True)

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self) -> str:
        if self.script:
            return self.script.render()
        
        return ""

    # -----------------------------
    # Attributes rendering
    # -----------------------------
    @staticmethod
    def _validate_url_attribute(name: str, value: Any) -> None:
        if name.lower() not in _URL_ATTRIBUTE_NAMES or not isinstance(value, str):
            return

        candidate = html.unescape(value).strip()
        is_srcset = name.lower() == "srcset"
        candidates = candidate.split(",") if is_srcset else [candidate]

        for item in candidates:
            url = item.strip().split(maxsplit=1)[0] if is_srcset and item.strip() else item.strip()
            scheme_candidate = "".join(url.split())
            scheme = urlsplit(scheme_candidate).scheme.lower()

            if scheme not in _SAFE_URL_SCHEMES:
                raise ValueError(f"Unsafe URL scheme for HTML attribute {name!r}: {scheme!r}")

    def render_attributes(self) -> str:
        attrs = []

        for key, value in self.props.items():
            if not isinstance(key, str) or not _ATTRIBUTE_NAME.fullmatch(key):
                raise ValueError(f"Invalid HTML attribute name: {key!r}")

            if key.lower().startswith("on") or key.lower() in _UNSAFE_ATTRIBUTE_NAMES:
                # Raw HTML event attributes are not allowed; framework-managed events are handled separately
                continue

            if value is None or value is False:
                continue

            self._validate_url_attribute(key, value)

            if value is True:
                attrs.append(html.escape(str(key)))
                continue

            attrs.append(f'{key}="{html.escape(str(value))}"')

        return " ".join(attrs)

    def after_render(self, html_output: str) -> str:
        style_block = self.style.render() if self.style else ""
        script_block = self.script.render() if self.script else ""
        bridge_block = self.render_event_bridge()
        output = html_output

        if style_block:
            output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            output += f"\n{script_block}"

        if bridge_block:
            output += f"\n{bridge_block}"

        return output

    # -----------------------------
    # Content rendering
    # -----------------------------
    def render_content(self) -> str:
        inner = ""

        for c in self.content:
            if isinstance(c, Element):
                inner += c.render()
            elif isinstance(c, RawHTML):
                inner += c.content
            elif isinstance(c, SafeString):
                inner += c.render()
            else:
                if getattr(self, "tag", "").lower() in {"script", "style"}:
                    inner += str(c)
                else:
                    inner += html.escape(str(c))

        return inner


    # -----------------------------
    # Full render
    # -----------------------------
    def render(self) -> str:
        self.before_render()

        attributes = self.render_attributes()
        inner_html = self.render_content()

        if self.tag.lower() in SELF_CLOSING_TAGS:
            if attributes:
                return self.after_render(f"<{self.tag} {attributes} />")

            return self.after_render(f"<{self.tag} />")

        if attributes:
            return self.after_render(f"<{self.tag} {attributes}>{inner_html}</{self.tag}>")

        return self.after_render(f"<{self.tag}>{inner_html}</{self.tag}>")
