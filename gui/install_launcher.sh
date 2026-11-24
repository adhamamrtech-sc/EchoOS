#!/usr/bin/env bash
# Add EchoOS to the Ubuntu applications menu (and optionally the desktop and
# login autostart) so it opens like a normal app, with no terminal.
#
#   bash gui/install_launcher.sh              # menu entry + desktop icon
#   bash gui/install_launcher.sh --autostart  # also start EchoOS at login
#   bash gui/install_launcher.sh --remove     # remove all of the above
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
NAME="echoos.desktop"

if [[ "${1:-}" == "--remove" ]]; then
    rm -f "${APPS_DIR}/${NAME}" "${AUTOSTART_DIR}/${NAME}" "${DESKTOP_DIR}/${NAME}"
    echo "[EchoOS] Launcher removed."
    exit 0
fi

[[ -x "${PROJECT_ROOT}/.venv/bin/python" ]] || {
    echo "[EchoOS] Run 'bash gui/setup.sh' first." >&2
    exit 1
}

# flock -n: a second launch (for example autostart plus a click) does nothing,
# so two copies never fight over the microphone and the port.
ENTRY="[Desktop Entry]
Type=Application
Name=EchoOS
Comment=Voice-controlled Ubuntu. Say \"Hi Echo\".
Exec=flock -n /tmp/echoos.lock \"${PROJECT_ROOT}/gui/run.sh\"
Path=${PROJECT_ROOT}
Icon=${PROJECT_ROOT}/gui/static/echoos.svg
Terminal=false
Categories=Utility;
StartupWMClass=EchoOS
"

mkdir -p "$APPS_DIR"
printf '%s' "$ENTRY" > "${APPS_DIR}/${NAME}"
chmod +x "${APPS_DIR}/${NAME}"
echo "[EchoOS] Added to the applications menu."

if [[ -d "$DESKTOP_DIR" ]]; then
    cp "${APPS_DIR}/${NAME}" "${DESKTOP_DIR}/${NAME}"
    chmod +x "${DESKTOP_DIR}/${NAME}"
    gio set "${DESKTOP_DIR}/${NAME}" metadata::trusted true 2>/dev/null || true
    echo "[EchoOS] Desktop icon added (right-click it, then 'Allow Launching', if Ubuntu asks)."
fi

if [[ "${1:-}" == "--autostart" ]]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "${APPS_DIR}/${NAME}" "${AUTOSTART_DIR}/${NAME}"
    echo "[EchoOS] EchoOS will start when you log in."
fi
