from templar.studio.pages import (
    render_overview,
    render_routes,
    render_requests,
    render_templates,
    render_database,
    render_project_doctor
)

def test_all_pages_return_elements():
    renderers = [
        render_overview,
        render_routes,
        render_requests,
        render_templates,
        render_database,
        render_project_doctor
    ]

    for renderer in renderers:
        assert renderer() is not None