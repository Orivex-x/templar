from templar.studio.navigation import (
    DEFAULT_PAGE,
    get_navigation_item,
)

from templar.studio.shell import build_shell

from templar.studio.pages import (
    render_overview,
    render_config,
    render_routes,
    render_requests,
    render_templates,
    render_database,
    render_project_doctor,
)


PAGE_RENDERERS = {
    "overview": render_overview,
    "config": render_config,
    "routes": render_routes,
    "requests": render_requests,
    "templates": render_templates,
    "database": render_database,
    "project_doctor": render_project_doctor,
}


def build_studio_page(page_id: str = DEFAULT_PAGE, *, cli=None):
    item = get_navigation_item(page_id)
    render_page = PAGE_RENDERERS[item.id]

    if item.id in ["config", "routes"]:
        content = render_page(cli) if cli is not None else render_page()
    else:
        content = render_page()

    return build_shell(content=content, active_page=item.id)