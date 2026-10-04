"""Entry point for all actions. Owner: Team Leader (allowlist and safety)."""
from . import apps_files, system_network

# Only actions listed here can run. Add a line when a new action is reviewed.
ALLOWED_ACTIONS = {
    "open_app": apps_files.open_app,
    "set_volume": system_network.set_volume,
    "set_brightness": system_network.set_brightness,
    "lock_screen": system_network.lock_screen,
    "get_network_status": system_network.get_network_status,
}


def run(intent):
    """Return a dict: status (ok, error or needs_confirmation) and message."""
    action = intent.get("action")
    handler = ALLOWED_ACTIONS.get(action)
    if handler is None:
        return {"status": "error", "message": f"Unknown action: {action}"}
    try:
        return handler(intent)
    except NotImplementedError:
        return {"status": "error", "message": f"{action} is not implemented yet."}