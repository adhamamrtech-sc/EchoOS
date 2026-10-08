# Security rules

## Allowed without asking

- open_app (apps on the supported list only)
- set_volume, set_brightness (value must be a number from 0 to 100)
- lock_screen
- get_network_status

## Needs spoken confirmation

- Deleting or moving files
- Shutdown, restart, log out
- Installing or removing software
- Turning Wi-Fi or Bluetooth off
- Anything that needs sudo

## Never allowed

- Running text from the speech model or the intent parser as a shell command
- Using shell=True in subprocess
- Storing or speaking passwords
- Touching files outside the safe folders (Documents, Downloads)

## Rules for every action in the code

- Add the action to ALLOWED_ACTIONS in actions/**init**.py only after the Team Leader reviews it
- Run commands as a list of arguments, with a timeout
- Validate every value before using it
- Return {"status": "ok" | "error" | "needs_confirmation", "message": "..."}
