import re

from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.components.EmptyState import empty_state
from templar.cli.commands.Routes import RoutesCommand


def _extract_route_params(pattern: str):
    if not isinstance(pattern, str):
        return []

    return re.findall(r"<([A-Za-z_][A-Za-z0-9_]*)>", pattern)


def _route_classification(row: dict) -> str:
    if row.get("is_default"):
        return "default"

    if _extract_route_params(str(row.get("pattern", ""))):
        return "dynamic"

    return "static"


def _build_pattern_cell(row: dict):
    pattern = str(row.get("pattern", "/"))

    return Div(
        [
            Paragraph("Route", classes=["route-field-label"]),
            Heading(pattern, level=4),
        ],
        classes=["route-cell", "route-pattern-cell"],
    )


def _build_details_cell(row: dict):
    template_file = str(row.get("template_file", ""))
    params = _extract_route_params(str(row.get("pattern", "")))

    blocks = [
        Div(
            [
                Paragraph("Template", classes=["route-field-label"]),
                Paragraph(template_file or "unknown", classes=["route-field-value"]),
            ],
            classes=["route-detail-block"],
        )
    ]

    if params:
        blocks.append(
            Div(
                [
                    Paragraph("Params", classes=["route-field-label"]),
                    Div(
                        [Div(param, classes=["route-param-pill"]) for param in params],
                        classes=["route-param-list"],
                    ),
                ],
                classes=["route-detail-block"],
            )
        )

    return Div(
        blocks,
        classes=["route-cell", "route-details-cell"],
    )


def _build_status_cell(row: dict):
    exists = bool(row.get("exists", False))
    default_route = bool(row.get("is_default", False))
    params = _extract_route_params(str(row.get("pattern", "")))

    badges = []

    if default_route:
        badges.append(Div("Default Route", classes=["route-badge", "route-badge-default"]))

    if params:
        badges.append(Div("Dynamic Route", classes=["route-badge", "route-badge-dynamic"]))
    else:
        badges.append(Div("Static Route", classes=["route-badge", "route-badge-static"]))

    if exists:
        badges.append(Div("Template Found", classes=["route-badge", "route-badge-success"]))
    else:
        badges.append(Div("Template Missing", classes=["route-badge", "route-badge-danger"]))

    return Div(
        [
            Paragraph("Status", classes=["route-field-label"]),
            Div(badges, classes=["route-badge-row"]),
        ],
        classes=["route-cell", "route-status-cell"],
    )


def _build_summary_card(title: str, value: str, tone: str = "neutral"):
    return Div(
        [
            Paragraph(title, classes=["studio-stat-label"]),
            Heading(value, level=3),
        ],
        classes=["studio-stat-card", f"studio-stat-card-{tone}"],
    )


def render_routes(cli=None):
    if cli is None:
        return Div(
            [
                Heading("Routes", level=2),
                Paragraph("Inspect routes registered by this project."),
                empty_state(
                    "Routes unavailable",
                    "A CLI instance is required to inspect this project's routes.",
                ),
            ],
            classes=["studio-page", "studio-routes"],
        )

    command = RoutesCommand(cli)
    rows = command.run(args=[], return_rows=True) or []

    if not rows:
        return Div(
            [
                Heading("Routes", level=2),
                Paragraph("Inspect routes registered by this project."),
                empty_state(
                    "No routes registered",
                    "No routes were found in this project's router or templates.",
                ),
            ],
            classes=["studio-page", "studio-routes"],
        )

    total_routes = len(rows)
    default_count = sum(1 for row in rows if row.get("is_default"))
    missing_templates = sum(1 for row in rows if not row.get("exists"))
    dynamic_routes = sum(
        1
        for row in rows
        if _extract_route_params(str(row.get("pattern", "")))
    )

    summary_cards = Div(
        [
            _build_summary_card("Total routes", str(total_routes), "primary"),
            _build_summary_card("Default route", str(default_count), "accent"),
            _build_summary_card("Dynamic routes", str(dynamic_routes), "warning"),
            _build_summary_card("Missing templates", str(missing_templates), "danger"),
        ],
        classes=["studio-stat-grid"],
    )

    header = Div(
        [
            Div("Route", classes=["routes-table-heading"]),
            Div("Details", classes=["routes-table-heading"]),
            Div("Status", classes=["routes-table-heading"]),
        ],
        classes=["routes-table-row", "routes-table-header"],
    )

    route_rows = [
        Div(
            [
                _build_pattern_cell(row),
                _build_details_cell(row),
                _build_status_cell(row),
            ],
            classes=["route-row", f"route-row-{_route_classification(row)}"],
        )
        for row in rows
    ]

    content = Div(
        [
            summary_cards,
            Div(
                [header, *route_rows],
                classes=["routes-table"],
            ),
        ],
        classes=["routes-page-content"],
    )

    return Div(
        [
            Heading("Routes", level=2),
            Paragraph("Inspect routes registered by this project, including defaults, dynamic parameter routes, and template availability."),
            content,
        ],
        classes=["studio-page", "studio-routes"],
    )