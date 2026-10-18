"""Pre-built UI components with styled defaults."""

import sys
from typing import Optional, List, Union

from templar.core.elements.Div import Div
from templar.core.elements.Span import Span
from templar.core.elements.Button import Button
from templar.core.elements.Element import Element
from templar.core.Css import CSS

sys.dont_write_bytecode = True


class Card(Div):
    """
    Card component - container with shadow and padding.
    
    Usage:
        Card([
            Heading("Title"),
            Paragraph("Content")
        ], shadow=True, hover_effect=True)
    """
    
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        shadow: bool = True,
        hover_effect: bool = False,
        padding: str = "1.5rem",
        border_radius: str = "8px",
        id: str = None,
        classes: List[str] = None,
        **props
    ):
        """Initialize a Card component."""
        classes = classes or []
        classes.append("component-card")
        
        super().__init__(content, id=id, classes=classes, **props)
        
        # Default styles
        if self.style:
            self.style.set("padding", padding) \
                .set("border-radius", border_radius) \
                .set("background-color", "#fff") \
                .set("border", "1px solid #e0e0e0")
            
            if shadow:
                self.style.set("box-shadow", "0 2px 8px rgba(0, 0, 0, 0.1)")
            
            if hover_effect:
                self.style.nested(":hover", {
                    "box-shadow": "0 4px 12px rgba(0, 0, 0, 0.15)",
                    "transform": "translateY(-2px)",
                    "transition": "all 0.3s ease"
                })


class Alert(Div):
    """
    Alert component - notification box.
    
    Usage:
        Alert("Warning!", type="warning")
        Alert("Success!", type="success")
    """
    
    TYPES = {
        "success": {
            "bg": "#d4edda",
            "border": "#c3e6cb",
            "color": "#155724",
        },
        "error": {
            "bg": "#f8d7da",
            "border": "#f5c6cb",
            "color": "#721c24",
        },
        "warning": {
            "bg": "#fff3cd",
            "border": "#ffeaa7",
            "color": "#856404",
        },
        "info": {
            "bg": "#d1ecf1",
            "border": "#bee5eb",
            "color": "#0c5460",
        },
    }
    
    def __init__(
        self,
        content: Union[str, Element],
        type: str = "info",
        dismissible: bool = False,
        id: str = None,
        **props
    ):
        """Initialize an Alert component."""
        classes = props.pop("classes", []) or []
        classes.append("component-alert")
        
        super().__init__(content, id=id, classes=classes, **props)
        
        colors = self.TYPES.get(type, self.TYPES["info"])
        
        if self.style:
            self.style.set("padding", "1rem") \
                .set("margin-bottom", "1rem") \
                .set("border", f"1px solid {colors['border']}") \
                .set("border-radius", "4px") \
                .set("background-color", colors["bg"]) \
                .set("color", colors["color"])


class Badge(Span):
    """
    Badge component - small label.
    
    Usage:
        Badge("New", variant="primary")
        Badge("Beta", variant="warning")
    """
    
    VARIANTS = {
        "primary": "#007BFF",
        "success": "#28a745",
        "danger": "#dc3545",
        "warning": "#ffc107",
        "secondary": "#6c757d",
    }
    
    def __init__(
        self,
        content: str = "",
        variant: str = "primary",
        id: str = None,
        **props
    ):
        """Initialize a Badge component."""
        classes = props.pop("classes", []) or []
        classes.append("component-badge")
        
        super().__init__(content, id=id, classes=classes, **props)
        
        color = self.VARIANTS.get(variant, self.VARIANTS["primary"])
        
        if self.style:
            self.style.set("display", "inline-block") \
                .set("padding", "0.25rem 0.75rem") \
                .set("border-radius", "12px") \
                .set("background-color", color) \
                .set("color", "#fff") \
                .set("font-size", "0.875rem") \
                .set("font-weight", "600")


class Button (Button):
    """Enhanced Button component with variants."""
    
    VARIANTS = {
        "primary": {
            "bg": "#007BFF",
            "hover": "#0056b3",
        },
        "success": {
            "bg": "#28a745",
            "hover": "#1e7e34",
        },
        "danger": {
            "bg": "#dc3545",
            "hover": "#bd2130",
        },
        "warning": {
            "bg": "#ffc107",
            "hover": "#e0a800",
        },
        "secondary": {
            "bg": "#6c757d",
            "hover": "#545b62",
        },
    }
    
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        variant: str = "primary",
        size: str = "md",
        id: str = None,
        classes: List[str] = None,
        **props
    ):
        """Initialize a Button component."""
        classes = classes or []
        classes.append("component-button")
        classes.append(f"component-button--{variant}")
        classes.append(f"component-button--{size}")
        
        super().__init__(content, id=id, classes=classes, **props)
        
        colors = self.VARIANTS.get(variant, self.VARIANTS["primary"])
        
        # Size styling
        sizes = {
            "sm": {"padding": "0.25rem 0.5rem", "font-size": "0.875rem"},
            "md": {"padding": "0.5rem 1rem", "font-size": "1rem"},
            "lg": {"padding": "0.75rem 1.5rem", "font-size": "1.125rem"},
        }
        size_style = sizes.get(size, sizes["md"])
        
        if self.style:
            self.style.set("padding", size_style["padding"]) \
                .set("font-size", size_style["font-size"]) \
                .set("background-color", colors["bg"]) \
                .set("border", "none") \
                .set("border-radius", "4px") \
                .set("color", "#fff") \
                .set("cursor", "pointer") \
                .set("transition", "all 0.2s ease") \
                .nested(":hover", {"background-color": colors["hover"]}) \
                .nested(":disabled", {
                    "background-color": "#cccccc",
                    "cursor": "not-allowed",
                    "opacity": "0.6"
                })


class Modal(Div):
    """
    Modal/dialog component.
    
    Usage:
        Modal([
            Heading("Modal Title"),
            Paragraph("Content"),
            Button("Close")
        ], title="Modal", show=True)
    """
    
    def __init__(
        self,
        content: Union[str, Element, List[Element]] = None,
        title: str = None,
        show: bool = False,
        size: str = "md",
        id: str = None,
        **props
    ):
        """Initialize a Modal component."""
        classes = props.pop("classes", []) or []
        classes.append("component-modal")
        classes.append(f"component-modal--{size}")

        if show:
            classes.append("component-modal--show")
        
        super().__init__(content, id=id, classes=classes, **props)
        
        if self.style:
            self.style.set("display", "flex" if show else "none") \
                .set("position", "fixed") \
                .set("top", "0") \
                .set("left", "0") \
                .set("width", "100%") \
                .set("height", "100%") \
                .set("background-color", "rgba(0, 0, 0, 0.5)") \
                .set("z-index", "1000") \
                .set("align-items", "center") \
                .set("justify-content", "center")


class Spinner(Div):
    """Loading spinner component."""
    
    def __init__(
        self,
        size: str = "md",
        color: str = "#007BFF",
        id: str = None,
        **props
    ):
        """Initialize a Spinner component."""
        classes = props.pop("classes", []) or []
        classes.append("component-spinner")
        classes.append(f"component-spinner--{size}")
        
        super().__init__(id=id, classes=classes, **props)
        
        sizes = {
            "sm": "20px",
            "md": "40px",
            "lg": "60px",
        }
        size_px = sizes.get(size, sizes["md"])
        
        if self.style:
            self.style.set("width", size_px) \
                .set("height", size_px) \
                .set("border", f"4px solid {color}") \
                .set("border-top-color", "transparent") \
                .set("border-radius", "50%") \
                .set("animation", "spin 0.8s linear infinite")
