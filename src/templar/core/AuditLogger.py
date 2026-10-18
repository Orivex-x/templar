import sys
sys.dont_write_bytecode = True

class AuditLogger:
    logs = []

    @classmethod
    def log(cls, element_id, old_state, patch):
        cls.logs.append({"element_id": element_id, "old_state": old_state, "patch": patch})

    @classmethod
    def get_last_patch(cls, element_id):
        for log in reversed(cls.logs):
            if log["element_id"] == element_id:
                return log
            
        return None
