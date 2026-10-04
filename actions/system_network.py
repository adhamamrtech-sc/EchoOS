"""System settings and network actions. Owner: Actions Engineer 2 (Menna)."""
import subprocess


def _percent(intent):
    """Read params.value and return an int from 0 to 100, or None."""
    value = intent.get("params", {}).get("value")
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if 0 <= value <= 100 else None


def _run(command, ok_message):
    """Run a command (a list, never a shell string) and return an action result."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
    except FileNotFoundError:
        return {"status": "error", "message": f"{command[0]} is not installed."}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return {"status": "error", "message": f"Command failed: {e}"}
    return {"status": "ok", "message": ok_message or result.stdout.strip()}


def set_volume(intent):
    value = _percent(intent)
    if value is None:
        return {"status": "error", "message": "Volume must be a number from 0 to 100."}
    return _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{value}%"], f"Volume set to {value}%")


def set_brightness(intent):
    value = _percent(intent)
    if value is None:
        return {"status": "error", "message": "Brightness must be a number from 0 to 100."}
    return _run(["brightnessctl", "set", f"{value}%"], f"Brightness set to {value}%")


def lock_screen(intent):
    return _run(["loginctl", "lock-session"], "Screen locked")


def get_network_status(intent):
    return _run(["nmcli", "device", "status"], None)