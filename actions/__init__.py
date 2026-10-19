"""Entry point for all actions. Owner: Team Leader (allowlist and safety)."""
from . import system_network

try:
    from . import apps_files
    has_apps = True
except ImportError:
    has_apps = False

# Only actions listed here can run. Add a line when a new action is reviewed.
ALLOWED_ACTIONS = {
    "volume_up": system_network.volume_up,
    "set_volume": system_network.set_volume,
    "set_brightness": system_network.set_brightness,
    "lock_screen": system_network.lock_screen,
    "get_network_status": system_network.get_network_status,
    "set_wifi": system_network.set_wifi,
    "confirm_wifi_off": system_network.confirm_wifi_off,
    "set_bluetooth": system_network.set_bluetooth,
    "get_system_info": system_network.get_system_info,
}

if has_apps:
    ALLOWED_ACTIONS["open_app"] = apps_files.open_app


def run(intent):
    action = intent.get("action")
    handler = ALLOWED_ACTIONS.get(action)
    if handler is None:
        return {"status": "error", "message": f"Unknown action: {action}"}
    try:
        return handler(intent)
    except Exception as e:
        return {"status": "error", "message": str(e)}
