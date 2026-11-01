
"""System settings and network actions. Owner: Actions Engineer 2 (Menna)."""
import subprocess

"""System settings and network actions. Owner:Actions Engineer 2 (Menna)."""
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, unquote




def _percent(intent):
    """Read params.value and return an int from 0 to 100, or None."""
    value = intent.get("params", {}).get("value")
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if 0 <= value <= 100 else None



def _confirmed(intent):
    """True only when the user already confirmed this risky action."""
    return intent.get("params", {}).get("confirmed") is True


def _run(command, ok_message):
    """Run a command (a list, never a shell string) with a timeout and return a standard result."""

def _confirmed(intent):
    """True only when the user already confirmed this risky action."""
    return intent.get("params",{}).get("confirmed") is True
def _run(command,ok_message):
    """ run a command (a list,never a shell string) with a timeout and return a standard result."""

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return {"status": "ok", "message": ok_message or result.stdout.strip()}
    except FileNotFoundError:
        return {"status": "error", "message": f"Command not found: {command[0]}"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out."}
    except subprocess.CalledProcessError as error:

        return {"status": "error", "message": (error.stderr or "").strip() or "Command failed."}


# ------------------- SYSTEM ACTIONS -------------------
def volume_up(intent):
    return _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"], "Volume increased")



        return {"status":"error","message":(error.stderr or"").strip() or "Command failed."}
    except OSError:
        return {"status":"error","message":f"Could not run:{command[0]}"}
# -------------------SYSTEM ACTIONS-------------------
def _current_volume():
    """return the current volume percent as an int, or None if it cannot be read"""
    try:
        result =subprocess.run(["pactl","get-sink-volume","@DEFAULT_SINK@"],capture_output=True,text=True,timeout=10,check=True)
    except(OSError,subprocess,SubprocessError):
        return None
    match =re.search(r"(\d+)%",result.stdout)
    return int(match.group(1)) if match else None
def volume_up(intent):
    current =_current_volume()
    if current is None:
        return _run(["pactl","set-sink-volume","@DEFAULT_SINK@","+10%"],"Volume increased")
    new_value =min(current +10,100) #never go above 100%
    return _run(["pactl","set-sink-volume","@DEFAULT_SINK@",f"{new_value}%"],f"Volume set to {new_value}%")

def set_volume(intent):
    value = _percent(intent)
    if value is None:
        return {"status": "error", "message": "Volume must be a number from 0 to 100."}
    return _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{value}%"], f"Volume set to {value}%")


def set_brightness(intent):
    value = _percent(intent)
    if value is None:

        return {"status": "error", "message": "Brightness must be a number from 0 to 100."}
    # No sudo: add your user to the "video" group once instead (see SECURITY.md).
    return _run(["brightnessctl", "set", f"{value}%"], f"Brightness set to {value}%")


        return{"status":"error","message":"Brightness must be a number from 0 to 100."}
    if not shutil.which("brightnessctl"):
        return {"status":"error","message":"brightnessct is not installed"}
    if not any (Path("/sys/class/backlight").glob("*")):
        return {"status":"error","message":"No backlight device found on this machine"}
    value =max(value, 5) # a black screen would be hard to recover from 
    # no sudo : add your user to the "video" group once instead (see SECURITY.md).
    return _run(["brightnessctl","set",f"{value}%"],f"Brightness set to {value}%")

def lock_screen(intent):
    return _run(["loginctl", "lock-session"], "Screen locked")


def get_system_info(intent):

    """Report CPU, RAM and disk usage (psutil); fall back to `uname -a`."""
    try:
        import psutil
    except ImportError:
        return _run(["uname", "-a"], None)

    metrics = intent.get("params", {}).get("metrics") or ["cpu", "ram", "disk"]
    parts = []


    """ report CPU,RAM and dick usage (psutil);fall back to 'uname -a'."""
    try:
        import pustil
    except ImportError:
        return _run(["uname","-a"],None)
    metrics = intent.get("params",{}).get("metrics") or ["cpu","ram","disk"]
    parts =[]

    if "cpu" in metrics:
        parts.append(f"CPU {psutil.cpu_percent(interval=0.5):.0f}%")
    if "ram" in metrics:
        parts.append(f"RAM {psutil.virtual_memory().percent:.0f}% used")
    if "disk" in metrics:

        parts.append(f"Disk {psutil.disk_usage('/').percent:.0f}% used")

    if not parts:
        return {"status": "error", "message": "No known metric was asked for."}

    return {"status": "ok", "message": ", ".join(parts)}


# ------------------- NETWORK ACTIONS -------------------
def get_network_status(intent):
    return _run(["nmcli", "device", "status"], None)


def set_wifi(intent):
    state = intent.get("params", {}).get("state", "on")
    if state not in ("on", "off"):
        return {"status": "error", "message": "Wi-Fi state must be on or off."}
    if state == "off" and not _confirmed(intent):

        parts,append(f"Disk {psutil.disk_usage('/').percent:.0f}% used")
    if not parts:
        return {"status":"error","message":"no known metric was asked for."}
    return {"status":"ok","message":",".join(parts)}
def get_time(intent):
    now =datetime.now()
    hour =now.hour %12 or 12
    suffix ="AM" if now.hour < 12 else "PM"
    return {"status":"ok","message":f"It is {hour}:{now.minute:02d} {suffix}"}
def show_processes(intent):
    """ top 5 processes by CPU usage"""
    try:
        import psutil
    except ImportError:
        return {"status":"error","message":"psutil is not installed"}
    procs = list(psutil.process_iter(["name"]))
    for p in procs: # the first call only primes the CPU counters
        try:
            p.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(0.5)
    usage =[]
    for p in procs:
        try:
            usage.append((p.cpu_percent(None), p.info["name"]))
        except (psutil.NoSuchProcess,psutil.AccessDenied):
            pass
    usage.sort(reverse =True)
    top =",".join(f"{name} {cpu:.0f}%" for cpu, name in usage [:5])
    return {"status":"ok","message":f"Top processes: {top}"}
def screenshot(intent):
    folder =Path.home() / "Pictures"
    folder.mkdir(exist_ok=True)
    path =folder /f"echoos_{datetime.now():%Y%m%d_%H%M%S}.png"
    for command in (["gnome-screenshot","-f", str(path)],
                    ["grim", str(path)],
                    ["scrot", str(path)],                       
                    ["import","-window","root",str(path)]):
        if shutil.which(command[0]):
            result =_run(command,"Screenshot saved to Pictures")
            if result ["status"] == "ok" and path.exists():
                if path.stat().st_size  >5000:
                    return result
                path.unlink()
    return {"status":"error","message":"Screenshot failed: the desktop blocked capture or returned a blank image"}
# -------------------NETWORK ACTIONS-----------
def get_network_status(intent):
    return _run(["nmcli","-t","-f","DEVICE,TYPE,STATE","device","status"],None)
    if result ["status"] !="ok":
        return result
    parts =[]
    for line in result ["message"].splitlines():
        fields =line.split(":")
        if len(fields) == 3 and fields [1] in ("wifi","ethernet"):
            parts.append(f"{fields[1]} is {fields[2]}")
    return {"status":"ok","message":",".join(parts) or "no network device found"}
def set_wifi(intent):
    state =intent.get("params",{}).get("state","on")
    if state not in ("on","off"):
        return {"status":"error","message":"Wi-Fi state must be on or off."}
    if state =="off" and not _confirmed(intent):
    
        return confirm_wifi_off(intent)
    return _run(["nmcli", "radio", "wifi", state], f"Wi-Fi turned {state}")


def confirm_wifi_off(intent):
    return {"status": "needs_confirmation", "message": "Are you sure you want to turn off Wi-Fi?"}


def set_bluetooth(intent):

    state = intent.get("params", {}).get("state", "on")
    if state not in ("on", "off"):
        return {"status": "error", "message": "Bluetooth state must be on or off."}
    if state == "off" and not _confirmed(intent):
        return {"status": "needs_confirmation", "message": "Are you sure you want to turn off Bluetooth?"}
    command = "unblock" if state == "on" else "block"
    return _run(["rfkill", command, "bluetooth"], f"Bluetooth set to {state}")

    state =intent.get("params",{}).get("state","on")
    if state not in ("on","off"):
        return {"status":"error","message":"Bluetooth state must be on or off."}
    if state == "off" and not _confirmed(intent):
        return {"status":"needs_confirmation","message":"are you sure you want to turn off bluetooth?"}
    command = "unblock" if state =="on" else "block"
    return _run(["rfkill",command,"bluetooth"],f"Bluetooth set to {state}")

