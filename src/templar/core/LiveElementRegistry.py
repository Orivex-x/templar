import sys
from templar.core.AuditLogger import AuditLogger

sys.dont_write_bytecode = True

class LiveElementRegistry:
    elements = {}

    @classmethod
    def register(cls, element):
        cls.elements[element.global_id] = element

    @classmethod
    def get(cls, element_id):
        return cls.elements.get(element_id)

    @classmethod
    def apply_patch(cls, element_id, patch):
        el = cls.get(element_id)
        
        if not el:
            return
        
        old_state = el.snapshot()
        
        for k, v in patch.items():
            setattr(el, k, v)

        el.push_update()  # notify connected clients

        AuditLogger.log(element_id, old_state, patch)

        # Live Patch Format
        # {
        # "element_id": "btn-1234",
        # "patch": {
        #     "content": "New Text",
        #     "classes": ["cta", "highlight"]
        # },
        # "author": "dev123",
        # "timestamp": "2025-09-28T20:15:00Z"
        # }
