"""System settings and network actions. Owner:Actions Engineer 2 (Menna)."""
import subprocess
def _percent(intent):
    """ read params.value and return an integer from 0 to 100, or none."""
    value =intent.get("params",{}).get("value")
    try:
        value =int(value)
    except(TypeError,ValueError):
        return None
    return value if 0 <= value <= 100 else None
def _run(command,ok_message):
    """ run a command safely with a timeout and return a standard result."""
    try:
        result =subprocess.run(
            command,
            capture_output =True,
            text =True,
            timeout =10,
            check =True,
        )
        return {"status":"ok","message":ok_message or result.stdout.strip()}
    except FileNotFoundError:
        return {"status":"error","message":f"Command not found:{command[0]}"}
    except subprocess.TimeoutExpired:
        return {"status":"error","message":"Command time out."}
    except subprocess.CalledProcessError as error:
        return {"status":"error","message":error.stderr.strip() or "Command failed."}
# -------------------SYSTEM ACTIONS-------------------
def Volume_up(intent):
    return _run(["pactl","set-sink-volume","@DEFAULT_SINK@","+10%"],"Volume increased")
def set_volume(intent):
    value =_percent(intent)
    if value is None:
        return {"status":"error","message":"Volume must be a number from 0 to 100."}
    return _run(["pactl","set-sink-volume","@DEFAULT_SINK@",f"{value}%"],f"Volume set to {value}%")
def set_brightness(intent):
    value =_percent(intent)
    if value is None:
        return{"status":"error","message":"Brightness must be a number from 0 to 100."}
    return _run(["sudo","brightnessctl","set",f"{value}%"],f"Brightness set to {value}%")
def lock_screen(intent):
    return _run(["loginctl","lock-session"],"Screen locked")
def get_system_info(intent):
    return _run(["uname","-a"],None)
# -------------------NETWORK ACTIONS-----------
def get_network_status(intent):
    return _run(["nmcli","device","status"],None)
def set_wifi(intent):
    state =intent.get("params",{}).get("state","on")
    if state not in ("on","off"):
        return {"status":"error","message":"Wi-Fi state must be on or off."}
    if state =="off":
        return confirm_wifi_off(intent)
    return _run(["nmcli","radio","wifi",state],f"Wi-Fi turned {state}")
def confirm_wifi_off(intent):
    return{"status":"needs_confirmation","message":"are you sure you want to turn off Wi-Fi?"}
def set_bluetooth(intent):
    state =intent.get("params",{}).get("state","on")
    if state not in ("on","off"):
        return {"status":"error","message":"Bluetooth state must be on or off."}
    command = "unblock" if state =="on" else "block"
    return _run(["rfkill",command,"bluetooth"],f"Bluetooth set to {state}")
