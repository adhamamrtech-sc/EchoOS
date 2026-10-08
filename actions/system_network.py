<<<<<<< HEAD
"""System settings and network actions."""
import subprocess
def _percent(intent):
    """Read params.value and return an int between 0 and 100, or None."""
    value=intent.get("params",{}).get("value")
    try: 
        value=int(value)
    except(TypeError,ValueError): 
        return None
    return value if 0 <= value <= 100 else None 
def _run(command, ok_message):
    """Run a command safely and return standard response status."""
    try:
        result=subprocess.run(command, capture_output=True,text=True,check=True)
        return {"status":"ok","message":ok_message if ok_message else result.stdout.strip()}
    except FileNotFoundError:
        return {"status":"error","message":f"Command not found: {command[0]}"}
    except subprocess.CalledProcessError as e:
        return {"status":"error","message":e.stderr.strip() or str(e)}
# ------------------ System Actions ---------------
def volume_up(intent):
    return _run(["pamixer","-i","10"], "Volume increased")
def set_volume(intent):
    val=_percent(intent)
    if val is None:
        return {"status":"error","message":"Invalid or missing volume value (0-100)"}
    return _run(["pamixer"," --set-volume",str(val)], f"Volume set to{val}%")
def set_brightness(intent):
    val= _percent(intent)
    if val is None:
        return {"status":"error","message":"Invalid or missing volume value (0-100)"}
    return _run(["sudo","brightnessctl","set",f"{val}%"], f"Brightness set to {val}%")
def lock_screen(intent):
    return _run(["loginctl","lock-session"],"Screen locked successfully")
def get_system_info(intent):
    return _run(["uname","-a"],None)
# ------------------ Network Actions ----------------
def get_network_status(intent):
    return _run(["nmcli","device","status"],None)
def set_wifi(intent):
    state=intent.get("params",{}).get("state","on")
    cmd="on" if state =="on" else "off"
    return _run(["nmcli","radio","wifi",cmd], f"Wi-Fi turned {state}")
def confirm_wifi_off(intent):
    return {"status":"needs_confirmation","message":"Are you sure you want to turn off Wi-Fi?"}
def set_bluetooth(intent):
    state=intent.get("params",{}).get("state","on")
    cmd="unblock" if state =="on" else "block"
    return _run(["rfkill",cmd,"bluetooth"], f"Bluetooth set to {state}")

=======
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
>>>>>>> 2c5e59d17d86773fe7687652bf85ddfb38030596
