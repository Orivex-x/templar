import json
from datetime import datetime
from pathlib import Path

from templar.core.elements.Details import Details
from templar.core.elements.Div import Div
from templar.core.elements.Heading import Heading
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Pre import Pre
from templar.core.elements.Summary import Summary
from templar.studio.components.EmptyState import empty_state


def _iter_log_entries(log_path: str | None):
    if not log_path:
        return []

    path = Path(log_path).expanduser()
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            lines = [line.strip() for line in handle if line.strip()]
    except OSError:
        return []

    entries = []
    for raw in lines:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if not isinstance(payload, dict):
            continue

        message = payload.get("message")
        timestamp = payload.get("timestamp")
        if not isinstance(message, str):
            continue

        parsed_time = None
        if isinstance(timestamp, str):
            try:
                parsed_time = datetime.fromisoformat(timestamp)
            except ValueError:
                parsed_time = None

        entries.append({
            "message": message,
            "timestamp": parsed_time,
            "context": payload.get("context", {}),
        })

    return entries


def _normalize_route(path: str | None):
    if not path:
        return "/"
    return path


def _should_skip(message: str, path: str = ""):
    lower = message.lower()
    clean_path = path.lower()
    skip_tokens = (
        "/studio",
        "/static/",
        "/favicon.ico",
        "/__templar_hot_reload__",
        "/__templar_reactive__",
    )
    return any(token in lower for token in skip_tokens) or any(token in clean_path for token in skip_tokens)


def _parse_request_activity(log_path: str | None, *, limit: int = 80):
    entries = _iter_log_entries(log_path)
    if not entries:
        return []

    activity = []
    pending = None

    for entry in entries:
        message = entry.get("message", "")
        context = entry.get("context") or {}
        if not isinstance(context, dict):
            context = {}

        timestamp = entry.get("timestamp")

        if _should_skip(message, str(context.get("path", ""))):
            continue

        if message == "[Request]":
            method = context.get("method", "GET")
            path = _normalize_route(context.get("path", "/"))

            pending = {
                "method": method,
                "path": path,
                "status": context.get("status", 200),
                "template": context.get("template", ""),
                "request": context.get("request", {}),
                "response": context.get("response", {}),
                "error": "",
                "timestamp": timestamp,
            }
            continue

        if message == "[Response]":
            if pending is not None:
                pending["template"] = context.get("template", pending.get("template", ""))
                pending["status"] = context.get("status", pending.get("status", 200))
                pending["response"] = context.get("response", {})
                activity.append(dict(pending))
                pending = None
            continue

        if "Unhandled request error" in message and context.get("traceback"):
            activity.append({
                "method": context.get("method", "UNKNOWN"),
                "path": context.get("path", "/"),
                "status": context.get("status", 500),
                "template": context.get("template", ""),
                "request": context.get("request", {}),
                "response": context.get("response", {}),
                "error": context.get("traceback", ""),
                "timestamp": timestamp,
            })

    return list(reversed(activity))[:limit]


def _safe_json(value):
    if value is None:
        return "null"

    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except TypeError:
            return str(value)

    return str(value)


def _payload_panel(title: str, value):
    return Div(
        [
            Paragraph(title, classes=["request-field-label"]),
            Pre(_safe_json(value), classes=["request-json-block"]),
        ],
        classes=["request-detail-panel"],
    )


def _error_panel(error_text: str):
    if not error_text:
        return Div(
            [
                Paragraph("Error trace", classes=["request-field-label"]),
                Div("No error trace captured.", classes=["request-empty"]),
            ],
            classes=["request-detail-panel", "request-detail-panel-wide"],
        )

    return Div(
        [
            Paragraph("Error trace", classes=["request-field-label"]),
            Pre(error_text, classes=["request-trace-block"]),
        ],
        classes=["request-detail-panel", "request-detail-panel-wide"],
    )


def _details_panel(entry):
    request_payload = entry.get("request", {})
    response_payload = entry.get("response", {})
    error_text = str(entry.get("error") or "").strip()

    return Details(
        [
            Summary("Request / Response"),
            Div(
                [
                    _payload_panel("Request payload", request_payload),
                    _payload_panel("Response payload", response_payload),
                    _error_panel(error_text),
                ],
                classes=["request-detail-grid"],
            ),
        ],
        classes=["request-collapsible"],
    )


def _status_badge(status):
    if status in (200, 201, 202, 204):
        tone = "success"
    elif status in (301, 302, 304):
        tone = "warning"
    elif status in (400, 404, 405, 409):
        tone = "danger"
    elif status in (500, 502, 503, 504):
        tone = "danger"
    else:
        tone = "neutral"

    return Div(str(status), classes=["request-status-badge", f"request-status-{tone}"])


def _method_badge(method: str):
    clean = (method or "REQ").upper()
    return Div(clean, classes=["request-method-badge", f"request-method-{clean.lower()}"])


def _build_summary_card(title: str, value: str, tone: str = "neutral"):
    return Div(
        [
            Paragraph(title, classes=["studio-stat-label"]),
            Heading(value, level=3),
        ],
        classes=["studio-stat-card", f"studio-stat-card-{tone}"],
    )


def _build_row(entry):
    method = entry.get("method", "REQ")
    path = entry.get("path", "/")
    status = entry.get("status", 200)
    template = entry.get("template") or "—"
    timestamp = entry.get("timestamp")

    time_label = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "unknown"

    row = Div(
        [
            Div(
                [
                    Paragraph("Time", classes=["request-field-label"]),
                    Paragraph(time_label, classes=["request-field-value"]),
                ],
                classes=["request-row-field"],
            ),
            Div(
                [
                    Paragraph("Route", classes=["request-field-label"]),
                    Paragraph(path, classes=["request-field-value"]),
                ],
                classes=["request-row-field"],
            ),
            Div(
                [
                    Paragraph("Method", classes=["request-field-label"]),
                    _method_badge(method),
                ],
                classes=["request-row-field"],
            ),
            Div(
                [
                    Paragraph("Status", classes=["request-field-label"]),
                    _status_badge(status),
                ],
                classes=["request-row-field"],
            ),
            Div(
                [
                    Paragraph("Template", classes=["request-field-label"]),
                    Paragraph(template, classes=["request-field-value"]),
                ],
                classes=["request-row-field"],
            ),
        ],
        classes=["request-feed-row"],
    )

    return Div(
        [row, _details_panel(entry)],
        classes=["request-feed-item"],
    )


def render_requests(cli=None):
    if cli is None:
        activity = []
    else:
        active_cfg = cli.config.get_active_config()
        log_path = active_cfg.get("log_file")
        activity = _parse_request_activity(log_path, limit=80)

    if not activity:
        return Div(
            [
                Heading("Requests", level=2),
                Paragraph("Inspect the most recent application requests and responses."),
                empty_state(
                    "No app request activity yet",
                    "Only your app routes are shown here. Studio and static asset traffic is filtered out.",
                ),
            ],
            classes=["studio-page", "studio-requests"],
        )

    total_requests = len(activity)
    success_count = sum(1 for item in activity if item.get("status", 0) in (200, 201, 202, 204, 301, 302, 304))
    failed_count = sum(1 for item in activity if item.get("status", 0) >= 400)
    trace_count = sum(1 for item in activity if item.get("error"))

    stat_cards = Div(
        [
            _build_summary_card("Total requests", str(total_requests), "primary"),
            _build_summary_card("Success", str(success_count), "success"),
            _build_summary_card("Errors", str(failed_count), "danger"),
            _build_summary_card("Tracebacks", str(trace_count), "warning"),
        ],
        classes=["request-stat-grid"],
    )

    rows = [_build_row(item) for item in activity]

    return Div(
        [
            Heading("Requests", level=2),
            Paragraph("Inspect the most recent app requests, responses, and runtime errors."),
            stat_cards,
            Div(rows, classes=["request-feed"]),
        ],
        classes=["studio-page", "studio-requests"],
    )