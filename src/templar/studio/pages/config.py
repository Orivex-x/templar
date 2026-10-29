from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph

from templar.studio.components.EmptyState import empty_state
from templar.cli.commands.ConfigCmd import ConfigCommand


def _format_environment_name(environment):
    return environment.replace("_", " ").title()


def _format_config_value(value):
    if value is None:
        return "None"

    if isinstance(value, bool):
        return "Enabled" if value else "Disabled"

    if isinstance(value, (dict, list, tuple)):
        return str(value)

    return str(value)


def _build_environment_card(environment, rows):
    enabled_count = sum(
        1
        for row in rows
        if isinstance(row.get("value"), bool) and row["value"]
    )

    header = Div(
        [
            Div(
                [
                    Div(
                        _format_environment_name(environment),
                        classes=["config-environment-name"],
                    ),
                    Div(
                        f"{len(rows)} configuration "
                        f"{'value' if len(rows) == 1 else 'values'}",
                        classes=["config-environment-count"],
                    ),
                ],
                classes=["config-environment-title"],
            ),
            Div(
                [
                    Div(
                        str(len(rows)),
                        classes=["config-stat-value"],
                    ),
                    Div(
                        "Settings",
                        classes=["config-stat-label"],
                    ),
                ],
                classes=["config-environment-stat"],
            ),
        ],
        classes=["config-environment-header"],
    )

    config_rows = []

    for row in sorted(rows, key=lambda item: str(item.get("key", "")).lower()):
        key = str(row.get("key", ""))
        value = row.get("value")

        if isinstance(value, bool):
            value_classes = [
                "config-value",
                "config-value-boolean",
                "is-enabled" if value else "is-disabled",
            ]
        elif value is None:
            value_classes = ["config-value", "config-value-null"]
        else:
            value_classes = ["config-value"]

        config_rows.append(
            Div(
                [
                    Div(
                        [
                            Div(
                                key,
                                classes=["config-key"],
                            ),
                        ],
                        classes=["config-setting-key"],
                    ),
                    Div(
                        _format_config_value(value),
                        classes=value_classes,
                    ),
                ],
                classes=["config-setting-row"],
            )
        )

    return Div(
        [
            header,
            Div(
                config_rows,
                classes=["config-settings"],
            ),
        ],
        classes=["config-environment-card"],
    )


def render_config(cli):
    command = ConfigCommand(cli)
    rows = command.run(args=[], return_rows=True) or []

    page_header = Div(
        [
            Div(
                [
                    Heading("Configuration", level=2),
                    Paragraph(
                        "Inspect application settings across your "
                        "development and production environments."
                    ),
                ],
                classes=["config-page-heading"],
            ),
            Div(
                [
                    Div(
                        [
                            Div(
                                str(len(rows)),
                                classes=["config-overview-value"],
                            ),
                            Div(
                                "Total settings",
                                classes=["config-overview-label"],
                            ),
                        ],
                        classes=["config-overview-card"],
                    ),
                    Div(
                        [
                            Div(
                                str(
                                    len(
                                        {
                                            row.get("environment", "unknown")
                                            for row in rows
                                        }
                                    )
                                ),
                                classes=["config-overview-value"],
                            ),
                            Div(
                                "Environments",
                                classes=["config-overview-label"],
                            ),
                        ],
                        classes=["config-overview-card"],
                    ),
                ],
                classes=["config-overview"],
            ),
        ],
        classes=["config-page-header"],
    )

    if not rows:
        content = empty_state(
            "No configuration found",
            "Configuration values will appear here when they are available.",
        )
    else:
        environments = {}

        for row in rows:
            environment = row.get("environment", "unknown")
            environments.setdefault(environment, []).append(row)

        preferred_order = ["active", "dev", "prod"]
        ordered_environments = sorted(
            environments,
            key=lambda environment: (
                preferred_order.index(environment)
                if environment in preferred_order
                else len(preferred_order),
                environment.lower(),
            ),
        )

        environment_cards = [
            _build_environment_card(
                environment,
                environments[environment],
            )
            for environment in ordered_environments
        ]

        content = Div(
            [
                Div(
                    [
                        Heading("Environment settings", level=3),
                        Paragraph(
                            "Browse configuration values grouped by "
                            "their environment. Sensitive values should "
                            "remain redacted by the configuration command."
                        ),
                    ],
                    classes=["config-section-heading"],
                ),
                Div(
                    environment_cards,
                    classes=["config-environment-grid"],
                ),
            ],
            classes=["config-content"],
        )

    return Div(
        [
            page_header,
            content,
        ],
        classes=["studio-page", "studio-config"],
    )