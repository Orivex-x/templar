import re
import importlib.util
import sys
import threading
from contextvars import ContextVar
from pathlib import Path

from templar.Config import Config
from templar.Template import Template
from templar.core.Javascript import Javascript
from templar.core.elements import (
    Html, Head, Title, Meta, Script, Link,
    Body, RawHTML, Style
)
from templar.core.elements.Element import Element
from templar.core.elements.ElementMatrix import ElementMatrix
from templar.core.security.SafeString import SafeString

sys.dont_write_bytecode = True


class Renderer:
    """
    Renderer that builds HTML, logs a semantic DOM via ElementMatrix,
    maps static assets, and supports element-level hot reload.
    """

    def __init__(
        self,
        config: Config,
        templates_dir: Path,
        themes_dir: Path,
        static_dir: Path
    ) -> None:
        self.templateDir = templates_dir.resolve()
        self.themesDir = themes_dir.resolve()
        self.staticDir = static_dir.resolve()
        self._template_cache = {}
        self._template_lock = threading.RLock()
        self._request_matrix: ContextVar[ElementMatrix | None] = ContextVar(
            "templar_renderer_matrix", default=None
        )

        self.jquery_url = "https://code.jquery.com/jquery-3.6.4.min.js"
        self.fontawesome_url = (
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
        )

        self.theme_css = self._load_theme_css(config)

    # -----------------------------
    # Template resolution
    # -----------------------------
    def _resolve_template_path(self, template_name_or_file: str) -> Path:
        template_path = Path(template_name_or_file)

        if template_path.is_absolute():
            resolved = template_path.resolve()
        elif not template_path.suffix.endswith(".py"):
            resolved = (self.templateDir / f"{template_path}.templar.py").resolve()
        else:
            resolved = (self.templateDir / template_path).resolve()

        if resolved != self.templateDir and self.templateDir not in resolved.parents:
            raise ValueError("Template path must stay inside the templates directory")

        return resolved

    def get_file_mtime(self, template_name: str) -> float:
        template_file = self._resolve_template_path(template_name)
        css_file = self.staticDir / "css" / f"{template_name}.css"
        js_file = self.staticDir / "javascript" / f"{template_name}.js"

        mtimes = [0]

        for f in (template_file, css_file, js_file):
            if f.exists():
                mtimes.append(f.stat().st_mtime)

        return max(mtimes)

    def _inject_optional_reset_css(self, html_output: str) -> str:
        """
        Inject the application's optional CSS reset into a full HTML document.

        The stylesheet is loaded only if the optional static/css/reset.css exists.
        It is inserted at the beginning of <head>, before application styles.
        """
        static_dir = Path(self.staticDir)
        reset_path = static_dir / "css" / "reset.css"

        if not reset_path.is_file():
            return html_output

        # Avoid inserting the same stylesheet more than once.
        reset_link_pattern = re.compile(
            r'<link\b'
            r'(?=[^>]*\bhref\s*=\s*["\']/?static/css/reset\.css(?:[?#][^"\']*)?["\'])'
            r'[^>]*>',
            re.IGNORECASE,
        )

        if reset_link_pattern.search(html_output):
            return html_output

        reset_link = (
            '<link rel="stylesheet" href="/static/css/reset.css">'
        )

        # Insert the reset before other stylesheets in the document head.
        head_pattern = re.compile(r"<head\b[^>]*>", re.IGNORECASE)

        if not head_pattern.search(html_output):
            return html_output

        return head_pattern.sub(
            lambda match: f"{match.group(0)}\n    {reset_link}",
            html_output,
            count=1,
        )

    # -----------------------------
    # Theme CSS loader
    # -----------------------------
    def _load_theme_css(self, config: Config) -> str:
        theme_name = config.get("theme", "light")
        theme_path = (
            self.themesDir / f"{theme_name}.templar.py"
        ).resolve()

        if not theme_path.exists():
            return ""

        spec = importlib.util.spec_from_file_location("theme", theme_path)
        theme_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(theme_module)

        for render_name in (
            "render",
            "get_styles",
            f"render_{theme_name}",
            f"render_custom_{theme_name}",
        ):
            render_func = getattr(theme_module, render_name, None)

            if callable(render_func):
                return render_func()

        return ""

    # -----------------------------
    # Return ElementMatrix as string
    # -----------------------------
    @property
    def matrix(self) -> ElementMatrix:
        """The current request's render matrix (or an empty matrix outside one)."""
        return self._request_matrix.get() or ElementMatrix()

    def get_matrix_log(self, matrix: ElementMatrix | None = None) -> str:
        lines = []

        def fmt_element(el: Element):
            """Return element type + key props as a string."""
            parts = [el.__class__.__name__]

            for key in ("id", "class", "href", "src", "rel", "name", "property", "charset", "type", "content"):
                if key in el.props and el.props[key]:
                    parts.append(f"{key}={el.props[key]}")
            return " ".join(parts)

        def walk_node(node: dict, depth=0):
            el = node["element"]
            indent = "  " * depth
            lines.append(f"{indent}- {fmt_element(el)}")

            # HEAD special handling
            if el.__class__.__name__ == "Head":
                for meta in node.get("meta", {}).values():
                    walk_node(meta, depth + 1)

                if node.get("title"):
                    walk_node(node["title"], depth + 1)

                for css in node.get("css", {}).values():
                    walk_node(css, depth + 1)

                for js in node.get("javascript", {}).values():
                    walk_node(js, depth + 1)

            # Recursively walk children (Body or other elements)
            for child in node.get("children", {}).values():
                walk_node(child, depth + 1)

        # Walk roots
        for root_id, root_node in (matrix or self.matrix).elements.items():
            walk_node(root_node, 0)

        return "\n".join(lines)
        
    # -----------------------------
    # Render template
    # -----------------------------
    def render_template(
        self,
        template_name_or_file: str,
        user_input: dict|None = None,
        debug: bool = True,
        **context
    ) -> str:
        user_input = user_input or {}

        for k, v in user_input.items():
            context[k] = (
                SafeString(v)
                if not isinstance(v, (SafeString, RawHTML))
                else v
            )

        # Resolve template
        template_path = self._resolve_template_path(template_name_or_file)

        with self._template_lock:
            if template_path not in self._template_cache:
                self._template_cache[template_path] = Template(
                    path=str(template_path)
                )

            template = self._template_cache[template_path]

        template_name = template_path.stem.replace(".templar", "")

        # Build template content
        template_content = template.get_element_tree(**context)

        if not isinstance(template_content, list):
            template_content = [template_content]

        # -----------------------------
        # Head construction
        # -----------------------------
        head_elements = [
            Meta(charset="UTF-8"),
            RawHTML("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"),
            Link(rel="icon", href="/favicon.ico", type="image/x-icon"),
            Title(id=f"{template_name}-title", content=template_name.capitalize()),
        ]

        css_path = self.staticDir / "css" / f"{template_name}.css"
        js_path = self.staticDir / "javascript" / f"{template_name}.js"

        if css_path.exists():
            head_elements.append(
                Link(
                    rel="stylesheet",
                    href=f"/static/css/{css_path.name}?v={int(css_path.stat().st_mtime)}"
                )
            )

        if js_path.exists():
            head_elements.append(
                Script(
                    src=(f"/static/javascript/{js_path.name}?v={int(js_path.stat().st_mtime)}")
                )
            )

        # Global assets
        head_elements.append(Link(rel="stylesheet", href=self.fontawesome_url))
        head_elements.append(Script(src=self.jquery_url))

        if self.theme_css:
            head_elements.append(Style(content=self.theme_css))
        
        # -----------------------------
        # HTML tree
        # -----------------------------
        head = Head(head_elements)
        body = Body(template_content)

        if debug and not any(
            isinstance(el, Script) and el.props.get("data_templar") == "hot-reload"
            for el in body.content
        ):
            hot_reload_js = Javascript().hotReload(template_name, debug)

            if hot_reload_js:
                body.content.append(
                    Script(
                        content=hot_reload_js.render(False),
                        id="hot-reload",
                        type="text/javascript",
                        **{"data-templar": "hot-reload"}
                    )
                )

        html_doc = Html([head, body], id="templar-root", lang="en")

        # -----------------------------
        # Build ElementMatrix
        # -----------------------------
        matrix = ElementMatrix()
        matrix.build(html_doc, template_name)
        self._request_matrix.set(matrix)

        html_output = "<!DOCTYPE html>\n" + html_doc.render()

        return self._inject_optional_reset_css(html_output)