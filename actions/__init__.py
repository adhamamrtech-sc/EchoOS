"""Entry point for all actions. Owner: Team Leader (allowlist and safety)."""
from . import apps_files, system_network

# Only actions listed here can run. Add a line when a new action is reviewed.
ALLOWED_ACTIONS = {
    "open_app": apps_files.open_app,
    "volume_up": system_network.volume_up,
}


def run(intent):
    """Return a dict: status (ok, error or needs_confirmation) and message."""
    action = intent.get("action")
    handler = ALLOWED_ACTIONS.get(action)
    if handler is None:
        return {"status": "error", "message": f"Unknown action: {action}"}
    return handler(intent)