from templar.studio.pages.overview import render_overview
from templar.studio.pages.config import render_config
from templar.studio.pages.routes import render_routes
from templar.studio.pages.requests import render_requests
from templar.studio.pages.templates import render_templates
from templar.studio.pages.database import render_database
from templar.studio.pages.project_doctor import render_project_doctor

__all__ = [
    "render_overview",
    "render_config",
    "render_routes",
    "render_requests",
    "render_templates",
    "render_database",
    "render_project_doctor"
]