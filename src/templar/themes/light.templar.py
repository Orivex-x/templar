import sys
from templar.themes.base import render

sys.dont_write_bytecode = True

# ---------------------------
# Light theme variables
# ---------------------------
light_vars = {
    "primary-color": "#ffffff",
    "secondary-color": "#3498db",
    "text-color": "#333333",
    "accent-color": "#1abc9c",
    "background-alt": "#f5f5f5",
    "link-color": "#2980b9",
    "error-color": "#e74c3c",
    "border-radius": "8px",
    "shadow": "0 4px 6px rgba(0,0,0,0.1)"
}

# Optional dynamic media queries
light_media = {
    "(max-width: 600px)": {
        "#main-container": "padding: 10px"
    }
}

def render_light():
    return render(base_vars=light_vars, media_queries=light_media)
