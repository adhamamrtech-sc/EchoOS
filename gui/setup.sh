#!/usr/bin/env bash
# Install EchoOS core + GUI dependencies on Ubuntu, without touching system Python.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

log() {
    printf '[EchoOS GUI Setup] %s\n' "$*"
}

fail() {
    printf '[EchoOS GUI Setup] ERROR: %s\n' "$*" >&2
    exit 1
}

on_error() {
    local status=$?
    printf '[EchoOS GUI Setup] ERROR: command failed (exit %s) at line %s: %s\n' \
        "$status" "$LINENO" "$BASH_COMMAND" >&2
    exit "$status"
}
trap on_error ERR

[[ "$(uname -s)" == "Linux" ]] || fail 'This installer supports Ubuntu/Linux only.'
command -v apt-get >/dev/null 2>&1 || fail 'apt-get was not found. Run this script on Ubuntu or an apt-based Ubuntu derivative.'
command -v "$PYTHON_BIN" >/dev/null 2>&1 || fail "${PYTHON_BIN} was not found. Install Python 3 and try again."

[[ -f "${PROJECT_ROOT}/requirements.txt" ]] || fail 'The repository root requirements.txt is missing.'
[[ -f "${SCRIPT_DIR}/requirements.txt" ]] || fail 'gui/requirements.txt is missing.'

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(
        f"Python 3.10 or newer is required; found {sys.version.split()[0]}."
    )
print(f"[EchoOS GUI Setup] Using Python {sys.version.split()[0]}")
PY

if [[ "$EUID" -eq 0 ]]; then
    SUDO=()
else
    command -v sudo >/dev/null 2>&1 || fail 'sudo is required to install Ubuntu system packages.'
    SUDO=(sudo)
fi

log 'Installing Ubuntu system dependencies (sudo may ask for your password)...'
"${SUDO[@]}" apt-get update
"${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git \
    python3-venv \
    python3-pip \
    ffmpeg \
    libportaudio2 \
    portaudio19-dev \
    alsa-utils \
    pulseaudio-utils \
    brightnessctl \
    espeak-ng \
    network-manager \
    rfkill \
    python3-gi \
    gir1.2-webkit2-4.1

if [[ -e "$VENV_DIR" && ! -x "${VENV_DIR}/bin/python" ]]; then
    fail "${VENV_DIR} already exists but is not a usable virtual environment. It was left untouched; inspect or rename it manually, then rerun this script."
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    log "Creating virtual environment at ${VENV_DIR}..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    log "Reusing existing virtual environment at ${VENV_DIR}."
fi

# The app window uses the system GTK/WebKit bindings, so the venv must see
# system packages. Edited in place so an existing venv keeps working.
if grep -q '^include-system-site-packages = false' "${VENV_DIR}/pyvenv.cfg" 2>/dev/null; then
    sed -i 's/^include-system-site-packages = false/include-system-site-packages = true/' "${VENV_DIR}/pyvenv.cfg"
fi

VENV_PYTHON="${VENV_DIR}/bin/python"
"$VENV_PYTHON" -m pip --version >/dev/null 2>&1 || fail 'The project virtual environment has no working pip. It was not deleted or recreated.'

log 'Upgrading pip inside the project virtual environment...'
"$VENV_PYTHON" -m pip install --disable-pip-version-check --upgrade pip

log 'Installing EchoOS core dependencies...'
"$VENV_PYTHON" -m pip install --disable-pip-version-check -r "${PROJECT_ROOT}/requirements.txt"

log 'Installing GUI and explicit audio/ASR dependencies...'
"$VENV_PYTHON" -m pip install --disable-pip-version-check -r "${SCRIPT_DIR}/requirements.txt"

log 'Checking the imports required to start the GUI and capture voice...'
"$VENV_PYTHON" - <<'PY'
import importlib
modules = (
    "flask",
    "numpy",
    "sounddevice",
    "faster_whisper",
    "webrtcvad",
)
missing = []
for module in modules:
    try:
        importlib.import_module(module)
    except Exception as exc:
        missing.append(f"{module}: {exc}")
if missing:
    raise SystemExit("Dependency import check failed:\n- " + "\n- ".join(missing))
print("[EchoOS GUI Setup] Required GUI/audio imports: OK")
PY

log 'Checking that the GUI can import the EchoOS core bridge...'
PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" \
    "$VENV_PYTHON" -c \
    "import runpy; runpy.run_path('${SCRIPT_DIR}/app.py', run_name='echoos_gui_setup_smoke')" \
    || fail 'The GUI or EchoOS core could not be imported. Review the error above; no source files were changed.'

log 'Adding EchoOS to the applications menu and desktop...'
bash "${SCRIPT_DIR}/install_launcher.sh" || log 'Launcher not installed; start EchoOS with: bash gui/run.sh'

log 'Installation completed. Open EchoOS from the applications menu, or run: bash gui/run.sh'
log 'The first voice command may download the configured faster-whisper model.'
log ''
log 'NOTE (Windows/WSL users): to create Desktop and Start Menu shortcuts run:'
log '  .venv\Scripts\python.exe gui\create_shortcut.py'
