
"""System settings and network actions. Owner: Actions Engineer 2 (Menna)."""

import re
import subprocess


ALLOWED_METRICS = {"cpu", "ram", "disk"}


def _params(intent):
    """Return params only when they are a dictionary."""
    if not isinstance(intent, dict):
        return {}
    params = intent.get("params", {})
    return params if isinstance(params, dict) else {}


def _percent(intent):
    """Return an integer from 0 to 100, or None for invalid input."""
    value = _params(intent).get("value")

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
        number = int(value.strip())
    else:
        return None

    return number if 0 <= number <= 100 else None


def _confirmed(intent):
    """Return True only when explicit confirmation is present."""
    return _params(intent).get("confirmed") is True


def _run(command, ok_message):
    """Run a command safely and return a standard result dictionary."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        message = ok_message or result.stdout.strip()
        return {"status": "ok", "message": message}

    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"Required command is not installed: {command[0]}",
        }

    except PermissionError:
        return {
            "status": "error",
            "message": f"Permission denied while running: {command[0]}",
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Command timed out.",
        }

    except subprocess.CalledProcessError:
        return {
            "status": "error",
            "message": f"Command failed: {command[0]}",
        }

    except OSError:
        return {
            "status": "error",
            "message": f"Could not execute command: {command[0]}",
        }


# ------------------- SYSTEM ACTIONS -------------------

def volume_up(intent):
    return _run(
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"],
        "Volume increased",
    )


def set_volume(intent):
    value = _percent(intent)

    if value is None:
        return {
            "status": "error",
            "message": "Volume must be an integer from 0 to 100.",
        }

    return _run(
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{value}%"],
        f"Volume set to {value}%",
    )


def set_brightness(intent):
    value = _percent(intent)

    if value is None:
        return {
            "status": "error",
            "message": "Brightness must be an integer from 0 to 100.",
        }

    # No sudo: configure the required permissions once (see SECURITY.md).
    return _run(
        ["brightnessctl", "set", f"{value}%"],
        f"Brightness set to {value}%",
    )


def lock_screen(intent):
    return _run(
        ["loginctl", "lock-session"],
        "Screen locked",
    )


def get_system_info(intent):
    """Report CPU, RAM and disk usage using psutil."""

    # Validate requested metrics before importing optional dependencies.
    metrics = _params(intent).get("metrics")

    if metrics is None:
        metrics = ["cpu", "ram", "disk"]

    if not isinstance(metrics, (list, tuple)):
        return {
            "status": "error",
            "message": "Metrics must be a list of cpu, ram, and disk.",
        }

    if not metrics or any(
        not isinstance(metric, str) or metric not in ALLOWED_METRICS
        for metric in metrics
    ):
        return {
            "status": "error",
            "message": "No valid metrics were requested.",
        }

    try:
        import psutil
    except ImportError:
        return _run(["uname", "-a"], None)

    parts = []

    if "cpu" in metrics:
        parts.append(
            f"CPU {psutil.cpu_percent(interval=0.5):.0f}%"
        )

    if "ram" in metrics:
        parts.append(
            f"RAM {psutil.virtual_memory().percent:.0f}% used"
        )

    if "disk" in metrics:
        parts.append(
            f"Disk {psutil.disk_usage('/').percent:.0f}% used"
        )

    return {
        "status": "ok",
        "message": ", ".join(parts),
    }


# ------------------- NETWORK ACTIONS -------------------

def get_network_status(intent):
    return _run(
        ["nmcli", "device", "status"],
        None,
    )


def set_wifi(intent):
    state = _params(intent).get("state", "on")

    if state not in ("on", "off"):
        return {
            "status": "error",
            "message": "Wi-Fi state must be on or off.",
        }

    if state == "off" and not _confirmed(intent):
        return confirm_wifi_off(intent)

    return _run(
        ["nmcli", "radio", "wifi", state],
        f"Wi-Fi turned {state}",
    )


def confirm_wifi_off(intent):
    return {
        "status": "needs_confirmation",
        "message": "Are you sure you want to turn off Wi-Fi?",
    }


def set_bluetooth(intent):
    state = _params(intent).get("state", "on")

    if state not in ("on", "off"):
        return {
            "status": "error",
            "message": "Bluetooth state must be on or off.",
        }

    if state == "off" and not _confirmed(intent):
        return {
            "status": "needs_confirmation",
            "message": "Are you sure you want to turn off Bluetooth?",
        }

    command = "unblock" if state == "on" else "block"

    return _run(
        ["rfkill", command, "bluetooth"],
        f"Bluetooth set to {state}",
    )
