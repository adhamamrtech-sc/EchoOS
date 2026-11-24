#!/usr/bin/env bash
# Launch the EchoOS GUI using the repository's isolated virtual environment.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    printf '[EchoOS GUI] ERROR: project virtual environment not found.\n' >&2
    printf 'Install the GUI first: bash gui/setup.sh\n' >&2
    exit 1
fi

if ! "$PYTHON" - <<'PY'
import importlib.util
required = ("flask", "numpy", "sounddevice", "faster_whisper", "webrtcvad")
missing = [name for name in required if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit("Missing Python modules: " + ", ".join(missing))
PY
then
    printf '[EchoOS GUI] ERROR: one or more GUI/audio dependencies are missing.\n' >&2
    printf 'Repair the environment with: bash gui/setup.sh\n' >&2
    exit 1
fi

printf '\n[EchoOS GUI] Starting EchoOS...\n'
exec "$PYTHON" "${SCRIPT_DIR}/app.py" "$@"
