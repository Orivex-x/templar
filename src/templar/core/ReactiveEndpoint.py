import json

from templar.core.LiveElementRegistry import LiveElementRegistry

class ReactiveEndpoint:
    """
    Server-side callback dispatcher for reactive DOM events.
    This is the execution point for python event handlers.
    """

    @staticmethod
    def handle(request):
        body = (request.body.decode("utf-8") if getattr(request, "body", None) else "{}")

        payload = json.loads(body or "{}")

        component_id = payload.get("component_id")
        event_name = payload.get("event_name")

        component = LiveElementRegistry.get(component_id)

        if component is None:
            return {
                "ok": False,
                "error": "component_not_found"
            }

        handler = component.event_handlers.get((event_name or "").lower())

        if handler is None:
            return {
                "ok": False,
                "error": "handler_not_found"
            }

        result = handler(payload)

        # A handler can specify an individual DOM element to update.
        if isinstance(result, dict) and {
            "target_id",
            "html"
        }.issubset(result):
            return {
                "ok": True,
                "target_id": result["target_id"],
                "html": result["html"]
            }

        # Component-rendering.
        if hasattr(component, "render"):
            return {
                "ok": True,
                "html": component.render()
            }

        return {
            "ok": True,
            "result": result
        }