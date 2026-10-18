import sys
from templar.themes.base import render

sys.dont_write_bytecode = True

# ---------------------------
# Dark theme variables
# ---------------------------
dark_vars = {
    "primary-color": "#2c3e50",
    "secondary-color": "#e74c3c",
    "text-color": "#ecf0f1",
    "accent-color": "#9b59b6",
    "background-alt": "#34495e",
    "link-color": "#3498db",
    "error-color": "#e74c3c",
    "border-radius": "8px",
    "shadow": "0 4px 6px rgba(0,0,0,0.3)"
}

# Optional dynamic media queries
dark_media = {
    "(max-width: 600px)": {
        "#main-container": "padding: 10px"
    }
}

def render_dark():
    return render(base_vars=dark_vars, media_queries=dark_media)
