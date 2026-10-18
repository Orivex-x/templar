import sys
import hashlib
from typing import Dict, Optional
from .Element import Element

from templar.core.elements import (
    Html, Head, Body,
    Meta, Title, Link, Script, Style
)

sys.dont_write_bytecode = True


class ElementMatrix:
    """
    Semantic DOM matrix.
    Builds a controlled, opinionated tree that mirrors real HTML structure.
    """

    def __init__(self):
        self.elements: Dict[str, Dict] = {}

    # -----------------------------
    # ID helpers
    # -----------------------------
    def _hash(self, obj) -> str:
        return hashlib.md5(str(id(obj)).encode()).hexdigest()[:8]

    def generate_id(self, element: Element, prefix: Optional[str] = None) -> str:
        if element.props.get("id"):
            return element.props["id"]

        base = self._hash(element)

        return f"{prefix}_{base}" if prefix else f"gen_{base}"

    # -----------------------------
    # Node factories
    # -----------------------------
    def _base_node(self, element: Element, parent: Optional[str]):
        return {
            "element": element,
            "parent": parent,
        }

    def _attribute_node(self, element: Element, parent: str):
        return {
            "element": element,
            "parent": parent,
            "attributes": dict(element.props),
        }

    # -----------------------------
    # Build
    # -----------------------------
    def build(self, root: Element, template_name: str = None):
        if not isinstance(root, Html):
            raise TypeError("ElementMatrix.build expects Html root")

        root_id = root.props.get("id", "root")

        self.elements[root_id] = {
            "element": root,
            "parent": None,
            "children": {},
            "style": root.style.render() if root.style else "",
            "script": root.script.render() if root.script else "",
        }

        for child in root.content:
            if isinstance(child, Head):
                self.elements[root_id]["children"]["head"] = self._build_head(child, root_id, template_name)
            elif isinstance(child, Body):
                self.elements[root_id]["children"]["body"] = self._build_body(child, root_id)

    # -----------------------------
    # Head
    # -----------------------------
    def _build_head(self, head: Head, parent_id: str, template_name: str = None) -> Dict:
        node = {
            "element": head,
            "parent": parent_id,
            "meta": {},
            "title": None,
            "css": {},
            "javascript": {},
        }

        for el in head.content:
            # Skip empty Link elements (no href or rel)
            if isinstance(el, Link) and not el.props.get("href") and not el.props.get("rel"):
                continue

            if isinstance(el, Meta):
                key = self._meta_key(el)
                node["meta"][key] = self._attribute_node(el, "head")

            elif isinstance(el, Title):
                node["title"] = self._attribute_node(el, "head")

            elif isinstance(el, (Link, Style)):
                key = self._head_asset_key(el, "css", template_name)
                node["css"][key] = self._attribute_node(el, "head")

            elif isinstance(el, Script):
                key = self._head_asset_key(el, "script", template_name)
                node["javascript"][key] = self._attribute_node(el, "head")

        return node

    # -----------------------------
    # Body
    # -----------------------------
    def _build_body(self, body: Body, parent_id: str) -> Dict:
        node = {
            "element": body,
            "parent": parent_id,
            "children": {},
            "style": body.style.render() if body.style else "",
            "script": body.script.render() if body.script else "",
        }

        for child in body.content:
            if isinstance(child, Element):
                child_id = self.generate_id(child)
                node["children"][child_id] = self._build_dom(
                    child,
                    child_id,
                    parent_id=node["element"].props.get("id", "body")
                )

        return node

    # -----------------------------
    # Generic DOM recursion
    # -----------------------------
    def _build_dom(self, element: Element, node_id: str, parent_id: str) -> Dict:
        if node_id == parent_id:
            raise ValueError(f"Element '{node_id}' cannot be its own parent")

        node = {
            "element": element,
            "parent": parent_id,
            "children": {},
            "style": element.style.render() if element.style else "",
            "script": element.script.render() if element.script else "",
        }

        for child in element.content:
            if isinstance(child, Element):
                cid = self.generate_id(child)
                # Correct parent ID assignment
                node["children"][cid] = self._build_dom(child, cid, parent_id=node_id)

        return node

    # -----------------------------
    # Head asset naming
    # -----------------------------
    def _head_asset_key(self, el: Element, kind: str, template_name: str = None) -> str:
        def norm(value: str) -> str:
            return (
                value
                .lower()
                .replace("-", "_")
                .replace(".", "_")
                .replace(":", "_")
            )

        if template_name:
            template_name = norm(template_name)

        # -----------------------------
        # CSS
        # -----------------------------
        if isinstance(el, Link):
            href = el.props.get("href", "").split("?")[0]

            if not href:
                return "css_unknown"

            if "font-awesome" in href:
                return "font_awesome"

            if href.endswith("/favicon.ico"):
                return "css_favicon"

            filename = href.rsplit("/", 1)[-1]

            if filename.endswith(".css"):
                name = norm(filename.replace(".css", ""))

                if template_name and name == template_name:
                    return f"css_{template_name}"

                return f"css_{name}"

        if isinstance(el, Style):
            # Deterministic inline style bucket
            return "css_inline"

        # -----------------------------
        # JavaScript
        # -----------------------------
        if isinstance(el, Script):
            src = el.props.get("src", "").split("?")[0]

            if "jquery" in src:
                return "jquery"

            if src.endswith(".js"):
                filename = src.rsplit("/", 1)[-1]
                name = norm(filename.replace(".js", ""))

                if template_name and name == template_name:
                    return f"script_{template_name}"

                return f"script_{name}"

        # Absolute fallback (should never be hit now)
        return f"{kind}_{self._hash(el)}"

    
    def _meta_key(self, meta: Meta) -> str:
        props = meta.props

        def norm(value: str) -> str:
            return (
                value
                .lower()
                .replace(":", "_")
                .replace("-", "_")
            )

        # <meta charset="UTF-8">
        if "charset" in props:
            return "meta_charset"

        # <meta http-equiv="refresh" content="5">
        if "http-equiv" in props:
            key = f"meta_http_equiv_{norm(props['http-equiv'])}"

            if "content" in props:
                key += f"_{norm(props['content'])}"
            
            return key

        # <meta name="description">
        # <meta name="twitter:site">
        if "name" in props:
            return f"meta_name_{norm(props['name'])}"

        # <meta property="og:title">
        if "property" in props:
            return f"meta_property_{norm(props['property'])}"

        # Absolute fallback (should almost never happen)
        return f"meta_{self._hash(meta)}"
