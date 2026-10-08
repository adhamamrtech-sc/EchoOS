"""Entry point for all actions."""
from . import system_network
ALLOWED_ACTIONS={ "volume_up":system_network.volume_up, "set_volume":system_network.set_volume, "set_brightness":system_network.set_brightness, "lock_screen":system_network.lock_screen, "get_network_status":system_network.get_network_status, "set_wifi":system_network.set_wifi, "confirm_wifi_off":system_network.confirm_wifi_off, "set_bluetooth":system_network.set_bluetooth, "get_system_info":system_network.get_system_info,}
                                                                                                                                                                         
def run(intent):
    action=intent.get("action")
    handler=ALLOWED_ACTIONS.get(action)
    if handler is None:
        return {"status":"error","message":f"Unknown action:{action}"}
    try:
        return handler(intent)
    except Exception as e:
        return {"status":"error","message":str(e)}
