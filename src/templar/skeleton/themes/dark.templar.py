import sys

from templar.themes.base import render
from templar.core.Css import CSS

sys.dont_write_bytecode = True

# ---------------------------
# Custom dark theme variables
# ---------------------------
custom_dark_vars = {
    "primary-color": "#1e272e",      # dark background
    "secondary-color": "#e74c3c",    # red accents
    "text-color": "#ecf0f1",         # light text
    "accent-color": "#9b59b6",       # purple highlights
    "background-alt": "#2c3e50",     # secondary dark background
    "link-color": "#3498db",         # link color
    "error-color": "#e74c3c",        # error color
    "border-radius": "10px",
    "shadow": "0 6px 10px rgba(0,0,0,0.4)"
}

# ---------------------------
# Optional media queries
# ---------------------------
custom_dark_media = {
    "(max-width: 768px)": {
        "#main-container": {"padding": "15px"},
        "#welcome-text": {"font-size": "18px"}
    },
    "(max-width: 480px)": {
        "#main-container": {"padding": "10px"},
        "#welcome-text": {"font-size": "16px"}
    }
}

# ---------------------------
# Optional additional component override
# ---------------------------
extra_dark_style = CSS("#custom-footer") \
    .set("background-color", "var(--accent-color)") \
    .set("color", "var(--primary-color)") \
    .set("padding", "12px") \
    .hover({"opacity": "0.85"})

# ---------------------------
# Render function
# ---------------------------
def render_custom_dark():
    base_css = render(base_vars=custom_dark_vars, media_queries=custom_dark_media)

    return "\n".join([base_css, extra_dark_style.render()])
