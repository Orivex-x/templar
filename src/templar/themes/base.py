import sys

from templar.core.Css import CSS

sys.dont_write_bytecode = True

# ---------------------------
# Shared components
# ---------------------------
main_container = CSS("#main-container") \
    .set("padding", "20px") \
    .set("background-color", "var(--primary-color)") \
    .set("border-radius", "var(--border-radius)") \
    .set("box-shadow", "var(--shadow)")

welcome_text = CSS("#welcome-text") \
    .set("color", "var(--text-color)") \
    .set("font-weight", "bold") \
    .nested(":hover", {"color": "var(--secondary-color)"})

intro_text = CSS("#intro-text") \
    .set("color", "var(--text-color)") \
    .set("font-style", "italic")

all_styles = [main_container, welcome_text, intro_text]

def render(base_vars=None, media_queries=None):
    """
    Render full CSS.
    :param base_vars: dict of CSS variables
    :param media_queries: dict of media query rules
    """
    lines = []

    # Render root variables if provided
    if base_vars:
        root = CSS(":root")

        for name, value in base_vars.items():
            root.var(name, value)

        lines.append(root.render())

    # Render all component styles
    for style in all_styles:
        lines.append(style.render())

    # Render media queries if provided
    if media_queries:
        for query, rules in media_queries.items():
            rules_lines = "; ".join(f"{k}: {v}" for k, v in rules.items())
            lines.append(f"@media {query} {{ {rules_lines}; }}")

    return "\n".join(lines)
