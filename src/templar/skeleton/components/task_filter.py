from templar.core.elements.Div import Div
from templar.core.elements.Button import Button
from templar.core.elements.Paragraph import Paragraph
from templar.core.elements.Heading import Heading


class TaskFilter(Div):
    def __init__(self, tasks: list | None = None):
        self.tasks = tasks or [
            {"title": "Fix invoice export", "done": False},
            {"title": "Update security headers", "done": True},
            {"title": "Review onboarding flow", "done": False},
            {"title": "Ship release notes", "done": True},
        ]

        self.filter = "all"

        self.title = Heading("Task Board", level=3)
        self.status = Paragraph(f"Showing: {self.filter}", id="task-filter-status")

        super().__init__(content=[], id="task-filter", classes=["task-filter"])

        # Important: assign root-level click handler AFTER base init
        self.event_handlers = {"click": self.handle_click}

        self.all_btn = Button("All", id="task-filter-all", data_action="all")
        self.open_btn = Button("Open", id="task-filter-open", data_action="open")
        self.done_btn = Button("Done", id="task-filter-done", data_action="done")

        self.content = [
            self.title,
            Div([self.all_btn, self.open_btn, self.done_btn], classes=["toolbar"]),
            self.status,
            self._render_tasks(),
        ]

    def handle_click(self, payload=None):
        payload = payload or {}
        action = payload.get("action")
        task_id = payload.get("task_id")

        if action == "all":
            return self.set_all(payload)
        if action == "open":
            return self.set_open(payload)
        if action == "done":
            return self.set_done(payload)
        if action == "toggle_task":
            return self.toggle_task(payload)

        return super().render()

    def _visible_tasks(self):
        if self.filter == "all":
            return self.tasks
        if self.filter == "open":
            return [task for task in self.tasks if not task["done"]]
        if self.filter == "done":
            return [task for task in self.tasks if task["done"]]
        return self.tasks

    def _render_tasks(self):
        visible = self._visible_tasks()
        item_nodes = []

        for task in visible:
            item_nodes.append(
                Div(
                    [
                        Paragraph(str(task["title"])),
                        Button(
                            "Mark done" if not task["done"] else "Mark open",
                            data_action="toggle_task",
                            data_task_id=task["title"],
                        ),
                    ],
                    classes=["task-item"],
                )
            )

        return Div(item_nodes, classes=["task-list"])

    def set_all(self, payload=None):
        self.filter = "all"
        self.status.content = [f"Showing: {self.filter}"]
        self.content = [
            self.title,
            Div([self.all_btn, self.open_btn, self.done_btn], classes=["toolbar"]),
            self.status,
            self._render_tasks(),
        ]
        return super().render()

    def set_open(self, payload=None):
        self.filter = "open"
        self.status.content = [f"Showing: {self.filter}"]
        self.content = [
            self.title,
            Div([self.all_btn, self.open_btn, self.done_btn], classes=["toolbar"]),
            self.status,
            self._render_tasks(),
        ]
        return super().render()

    def set_done(self, payload=None):
        self.filter = "done"
        self.status.content = [f"Showing: {self.filter}"]
        self.content = [
            self.title,
            Div([self.all_btn, self.open_btn, self.done_btn], classes=["toolbar"]),
            self.status,
            self._render_tasks(),
        ]
        return super().render()

    def toggle_task(self, payload=None):
        payload = payload or {}
        task_id = payload.get("task_id")

        if not task_id:
            return super().render()

        for task in self.tasks:
            if task["title"] == task_id:
                task["done"] = not task["done"]
                break

        self.content = [
            self.title,
            Div([self.all_btn, self.open_btn, self.done_btn], classes=["toolbar"]),
            self.status,
            self._render_tasks(),
        ]
        return super().render()

    def render(self):
        self.content = [
            self.title,
            Div([self.all_btn, self.open_btn, self.done_btn], classes=["toolbar"]),
            self.status,
            self._render_tasks(),
        ]
        return super().render()