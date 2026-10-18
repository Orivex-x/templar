"""Thread-safety coverage for renderer diagnostics and template caching."""

from concurrent.futures import ThreadPoolExecutor

from templar.Renderer import Renderer


def test_each_render_keeps_its_own_matrix_log(sample_config, temp_project_dir):
    (temp_project_dir / "templates" / "alpha.templar.py").write_text(
        "from templar.core.elements.Div import Div\n"
        "def render(**context): return Div('alpha')\n",
        encoding="utf-8",
    )
    (temp_project_dir / "templates" / "beta.templar.py").write_text(
        "from templar.core.elements.Div import Div\n"
        "def render(**context): return Div('beta')\n",
        encoding="utf-8",
    )
    renderer = Renderer(
        sample_config,
        temp_project_dir / "templates",
        temp_project_dir / "themes",
        temp_project_dir / "static",
    )

    def render_and_log(template_name):
        renderer.render_template(template_name)

        return template_name, renderer.get_matrix_log()

    names = ["alpha", "beta"] * 20

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(render_and_log, names))

    for name, matrix_log in results:
        assert f"Title id={name}-title" in matrix_log
