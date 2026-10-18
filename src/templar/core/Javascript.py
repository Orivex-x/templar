import sys
sys.dont_write_bytecode = True

class Javascript:
    def __init__(self, scope: str = None) -> None:
        """
        scope: Optional CSS selector (e.g., '#id') so methods can default to it.
        """
        self.scope = scope
        self._snippets_set = set()
        self._snippets_ordered = []

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _add_snippet(self, snippet: str) -> None:
        if snippet not in self._snippets_set:
            self._snippets_set.add(snippet)
            self._snippets_ordered.append(snippet)

    def _escape_js(self, string: str) -> str:
        return (
            str(string)
            .replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            # Inline scripts must never contain a literal closing-tag prefix.
            .replace("&", "\\x26")
            .replace("<", "\\x3C")
            .replace(">", "\\x3E")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )

    def _resolve_selector(self, selector: str = None) -> str:
        return self.scope if selector is None and self.scope else selector

    # -----------------------------
    # jQuery DOM manipulation
    # -----------------------------
    def css(self, selector: str = None, **props):
        selector = self._resolve_selector(selector)

        if not selector or not props:
            return self

        js_props = ",".join(f"'{k}':'{self._escape_js(str(v))}'" for k, v in props.items())
        self._add_snippet(f"$('{self._escape_js(selector)}').css({{{js_props}}});")

        return self

    def html(self, selector: str = None, content: str = ""):
        selector = self._resolve_selector(selector)

        if not selector:
            return self

        content_js = self._escape_js(content)
        self._add_snippet(f"$('{self._escape_js(selector)}').html('{content_js}');")

        return self

    def attr(self, selector: str = None, **attrs):
        selector = self._resolve_selector(selector)
        
        if not selector or not attrs:
            return self
        
        js_attrs = ",".join(f"'{k}':'{self._escape_js(str(v))}'" for k, v in attrs.items())
        self._add_snippet(f"$('{self._escape_js(selector)}').attr({{{js_attrs}}});")

        return self

    def on(self, selector: str = None, event: str = "", handler: str = ""):
        selector = self._resolve_selector(selector)
        
        if not selector:
            return self
        
        self._add_snippet(
            f"$('{self._escape_js(selector)}').on('{self._escape_js(event)}', function(event) {{ {handler} }});"
        )

        return self

    # Shortcuts
    def hide(self, selector: str = None):
        return self._simple("hide()", selector)
    
    def show(self, selector: str = None):
        return self._simple("show()", selector)
    
    def toggle(self, selector: str = None):
        return self._simple("toggle()", selector)

    def _simple(self, action: str, selector: str = None):
        selector = self._resolve_selector(selector)

        if selector:
            self._add_snippet(f"$('{self._escape_js(selector)}').{action};")

        return self

    def addClass(self, classname: str, selector: str = None):
        selector = self._resolve_selector(selector)

        if selector:
            self._add_snippet(f"$('{self._escape_js(selector)}').addClass('{self._escape_js(classname)}');")

        return self

    def removeClass(self, classname: str, selector: str = None):
        selector = self._resolve_selector(selector)

        if selector:
            self._add_snippet(f"$('{self._escape_js(selector)}').removeClass('{self._escape_js(classname)}');")

        return self

    def toggleClass(self, classname: str, selector: str = None):
        selector = self._resolve_selector(selector)

        if selector:
            self._add_snippet(f"$('{self._escape_js(selector)}').toggleClass('{self._escape_js(classname)}');")

        return self

    # -----------------------------
    # Hot reload SSE
    # -----------------------------
    def hotReload(self, template_name: str = "index", debug: bool = False):
        if template_name:
            # Strip extensions if provided
            if template_name.endswith(".templar.py"):
                template_name = template_name[: -len(".templar.py")]
            elif template_name.endswith(".templar"):
                template_name = template_name[: -len(".templar")]

            # Always fallback
            if not template_name:
                template_name = "index"

        if debug:
            snippet = f"""
            if (window.__templar_sse__) {{
                window.addEventListener("beforeunload", function() {{
                    window.__templar_sse__.close();
                }});
            }}
            document.addEventListener('DOMContentLoaded', function() {{
                if (window.__templar_sse__) window.__templar_sse__.close();
                window.__templar_sse__ = new EventSource("/__templar_hot_reload__?template={self._escape_js(template_name)}");
                window.__templar_sse__.onmessage = function(e) {{
                    if (e.data === "reload") {{
                        location.reload();
                    }}
                }};
            }});
            """
            self._add_snippet(snippet)
                
        return self

    # -----------------------------
    # Render final JS
    # -----------------------------
    def render(self, include_script_tags: bool = True) -> str:
        if not self._snippets_ordered:
            return ""
        
        js_content = "\n".join(str(s).strip() for s in self._snippets_ordered)

        if include_script_tags:
            return f"<script>\n{js_content}\n</script>"

        return js_content

    def get_snippets(self) -> list[str]:
        return self._snippets_ordered.copy()
