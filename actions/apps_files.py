"""Apps and files actions. Owner: Actions Engineer 1 (Dana)."""
import shutil
import subprocess

# Safe allowlist: spoken app name -> command (a list, never a shell string).
# The first command found on this machine is used.
APP_COMMANDS = {
    "chrome": [["google-chrome"], ["chromium"], ["chromium-browser"]],
    "firefox": [["firefox"]],
    "vscode": [["code"]],
    "terminal": [["gnome-terminal"], ["x-terminal-emulator"]],
    "spotify": [["spotify"]],
    "vlc": [["vlc"]],
    "calculator": [["gnome-calculator"], ["galculator"]],
    "files": [["nautilus"], ["xdg-open", "."]],
    "settings": [["gnome-control-center"]],
}


def open_app(intent):
    """Open an app from the supported list. Return an action result dict."""
    name = intent.get("target")

    if name not in APP_COMMANDS:
        return {"status": "error", "message": f"I can't open {name}."}

    for command in APP_COMMANDS[name]:
        if shutil.which(command[0]) is None:
            continue

        try:
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as error:
            return {"status": "error", "message": f"Could not open {name}: {error}"}

        return {"status": "ok", "message": f"Opening {name}"}

    return {"status": "error", "message": f"{name} is not installed."}
