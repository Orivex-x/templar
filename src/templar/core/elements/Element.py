import sys, html, re
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
        self.props: Dict[str, Any] = self._normalize_props(props)
        self.state: Dict[str, Any] = {}

        # Parent element reference
        self.parent: Optional[Element] = None

        # Normalize classes → "class" attribute
        if classes:
            self.props["class"] = " ".join(classes)

        if id:
            self.props["id"] = id

        # Normalize content → always a list
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

        # Scoped CSS & JS (only if id is provided)
        self.style: Optional[CSS] = CSS(f"#{id}") if id else None
        self.script: Optional[Javascript] = Javascript(f"#{id}") if id else None

        # Allow subclasses to provide defaults
        if self.style:
            self.default_styles(self.style)

        if self.script:
            self.default_scripts(self.script)

        # Lifecycle hook
        self.on_init()

    # -----------------------------
    # Helper to add children dynamically
    # -----------------------------
    def add_child(self, child: Any) -> None:
        if isinstance(child, Element):
            child.parent = self

        self.content.append(child)

    def _normalize_props(self, props: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}

        for key, value in props.items():
            attr = "class" if key == "class_" else key.replace("_", "-")
            normalized[attr] = value

        return normalized

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
        
        # Log element type and basic attributes
        attrs = {k: v for k, v in self.props.items() if v is not None}
        text = f"[{type(self).__name__}] Initialized"
        
        if attrs:
            text += " " + ", ".join(f"{k}={v}" for k, v in attrs.items())
        
        # print(SafeString(text).content)  # or use a safe logging function if available

        # Log style/script blocks if they exist
        if self.style:
            style_lines = self.style.render().splitlines()
            
            for line in style_lines:
                pass
                # print(f"  [Style] {line.strip()}")

        if self.script:
            script_lines = self.script.render().splitlines()

            for line in script_lines:
                pass
                # print(f"  [Script] {line.strip()}")

    # -----------------------------
    # Reactive patching
    # -----------------------------
    def update_dom(self):
        if self.script:
            return self.script.render()
        
        return ""

    # -----------------------------
    # Attributes rendering
    # -----------------------------
    @staticmethod
    def _validate_url_attribute(name: str, value: Any) -> None:
        """Reject executable or otherwise unsupported URL schemes.

        HTML escaping prevents markup injection but does not neutralize a
        ``javascript:`` URL. Whitespace and character references are removed
        for Scheme inspection because browsers normalize them before deciding
        whether a URL is executable.
        """
        if name.lower() not in _URL_ATTRIBUTE_NAMES or not isinstance(value, str):
            return

        candidate = html.unescape(value).strip()
        # ``srcset`` is a comma-separated list. Checking only its first URL would leave later candidates free to use an
        # executable scheme.
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
                raise ValueError(f"Unsafe HTML attribute name: {key!r}")

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
        output = html_output

        if style_block:
            output += f"\n<style>\n{style_block}\n</style>"

        if script_block:
            output += f"\n{script_block}"

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
                # Script and style contents are raw text in HTML.
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
