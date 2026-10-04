
"""Run commands on Ubuntu. Owners: Actions Engineers 1 and 2."""
import subprocess


def run(intent):
    """Return a dict: status (ok, error or needs_confirmation) and message."""
    action=intent.get("action")
    value=intent.get("value")
    try:
        if action =="set_volume":
            subprocess.run(["pamixer","--set-volume", str(value)], check=True)
            return{"status":"ok","message": f"volume set to{value}%"}
        elif action =="set_brightness":
            subprocess.run(["sudo","brightnessctl","set",f"{value}%"],check=True)
            return{"status":"ok","message":f"Brightness set to{value}%"}
        elif action =="lock_screen":
            subprocess.run(["loginctl","lock-session"], check=True) 
            return {"status":"ok","message":"Screen locked successfully"}
        elif action =="get_network_status":
            res= subprocess.run(["nmcli","device","status"],capture_output=True, text=True, check=True)
            return {"status":"ok","message":res.stdout}
        else:
            return {"status":"error","message":f"Unknown action: {action}"}
    except Exception as e:
        return {"status":"error","message":str(e)}

 
