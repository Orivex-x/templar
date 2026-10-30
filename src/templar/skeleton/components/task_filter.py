from templar.core.Css import CSS
from templar.core.elements.Div import Div
from templar.core.elements.Button import Button
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Heading import Heading


class TaskFilter(Div):
    def __init__(self, tasks: list | None = None, css: CSS | None = None):
        self.tasks = tasks if tasks is not None else [
            {"title": "Fix invoice export", "done": False},
            {"title": "Update security headers", "done": True},
            {"title": "Review onboarding flow", "done": False},
            {"title": "Ship release notes", "done": True},
        ]

        self.filter = "all"

        super().__init__(
            content=[],
            id="task-filter",
            classes=["task-filter"],
            css=css or CSS({
                "width": "100%",
                "padding": "24px",
                "box-sizing": "border-box",
                "background-color": "#ffffff",
                "border": "1px solid #e2e8f0",
                "border-radius": "16px",
                "color": "#0f172a",
            }),
        )

        self.title = Heading(
            "Task Board",
            level=3,
            css=CSS({
                "margin": "0 0 20px",
                "font-size": "22px",
                "font-weight": "750",
                "letter-spacing": "-0.03em",
                "color": "#0f172a",
            }),
        )

        self.status = Paragraph(
            "Showing: all",
            id="task-filter-status",
            css=CSS({
                "margin": "18px 0 12px",
                "font-size": "13px",
                "color": "#64748b",
            }),
        )

        self.all_btn = self._make_filter_button("All", "all")
        self.open_btn = self._make_filter_button("Open", "open")
        self.done_btn = self._make_filter_button("Done", "done")

        self.event_handlers = {"click": self.handle_click}
        self._refresh_content()

    def _make_filter_button(self, label: str, action: str):
        is_active = self.filter == action

        return Button(
            label,
            id=f"task-filter-{action}",
            data_action=action,
            aria_pressed=str(is_active).lower(),
            css=CSS({
                "padding": "8px 14px",
                "border": ("1px solid #4f46e5" if is_active else "1px solid #e2e8f0"),
                "border-radius": "8px",
                "background-color": ("#4f46e5" if is_active else "#ffffff"),
                "color": ("#ffffff" if is_active else "#334155"),
                "font-weight": "600",
                "cursor": "pointer",
                "transition": "background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease",
                "box-shadow": ("0 0 0 2px rgba(79, 70, 229, 0.12)" if is_active else "none"),
            }),
        )

    def handle_click(self, payload=None):
        payload = payload or {}
        action = payload.get("action")

        if action in ("all", "open", "done"):
            self.filter = action
            self._refresh_content()
            return super().render()

        if action == "toggle_task":
            task_id = payload.get("task_id")

            if task_id:
                for task in self.tasks:
                    if task["title"] == task_id:
                        task["done"] = not task["done"]
                        break

            self._refresh_content()
            return super().render()

        return super().render()

    def _refresh_content(self):
        self.status.content = [f"Showing: {self.filter}"]

        self.all_btn = self._make_filter_button("All", "all")
        self.open_btn = self._make_filter_button("Open", "open")
        self.done_btn = self._make_filter_button("Done", "done")

        toolbar = Div(
            [self.all_btn, self.open_btn, self.done_btn],
            classes=["toolbar"],
            css=CSS({
                "display": "flex",
                "flex-wrap": "wrap",
                "gap": "8px",
                "align-items": "center",
            }),
        )

        visible_tasks = [
            task for task in self.tasks
            if self.filter == "all"
            or (self.filter == "open" and not task["done"])
            or (self.filter == "done" and task["done"])
        ]

        task_items = []

        for task in visible_tasks:
            task_items.append(
                Div(
                    [
                        Paragraph(
                            str(task["title"]),
                            css=CSS({
                                "margin": "0",
                                "font-size": "14px",
                                "font-weight": "500",
                                "color": "#0f172a",
                            }),
                        ),
                        Button(
                            "Mark open" if task["done"] else "Mark done",
                            data_action="toggle_task",
                            data_task_id=task["title"],
                            css=CSS({
                                "padding": "7px 10px",
                                "border": "1px solid #cbd5e1",
                                "border-radius": "7px",
                                "background-color": "#f8fafc",
                                "color": "#334155",
                                "font-size": "12px",
                                "font-weight": "600",
                                "cursor": "pointer",
                            }),
                        ),
                    ],
                    classes=["task-item"],
                    css=CSS({
                        "display": "flex",
                        "align-items": "center",
                        "justify-content": "space-between",
                        "gap": "16px",
                        "padding": "14px 0",
                        "border-bottom": "1px solid #e2e8f0",
                    }),
                )
            )

        task_list = Div(
            task_items,
            classes=["task-list"],
            css=CSS({
                "display": "flex",
                "flex-direction": "column",
            }),
        )

        self.content = [
            self.title,
            toolbar,
            self.status,
            task_list,
        ]

    def render(self):
        self._refresh_content()
        return super().render()