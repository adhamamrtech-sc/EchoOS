# EchoOS GUI — Ubuntu Installation

This guide installs and launches the GUI in `gui/` together with the EchoOS
Python dependencies it needs. Run all commands from the repository root unless
stated otherwise.

## Requirements

- Ubuntu or an apt-based Ubuntu derivative.
- Python 3.10 or newer.
- Internet access during installation and the first speech-model download.
- A microphone supported by ALSA, PulseAudio, or PipeWire for voice input.

The GUI is a local Flask application shown in an app window. On Ubuntu the
window uses the system WebKitGTK packages, which the installer adds.

## Install

From the EchoOS repository root:

```bash
bash gui/setup.sh
```

The installer:

1. Installs the Ubuntu system packages used by audio capture and EchoOS system
   actions (PortAudio, ALSA/PulseAudio tools, FFmpeg, NetworkManager, rfkill,
   brightnessctl, and espeak-ng).
2. Creates or reuses the repository virtual environment at `.venv/` without
   deleting or replacing an existing environment.
3. Installs the repository-root `requirements.txt` and `gui/requirements.txt`
   into that virtual environment. The GUI requirements explicitly include
   NumPy, sounddevice, faster-whisper, and Flask.
4. Checks the imports required by the GUI/audio path and performs a non-serving
   import smoke test of the GUI and EchoOS command bridge.

The installer uses `sudo` only for Ubuntu package installation. Python packages
are installed inside `.venv/`; it does not use `sudo pip` or write to Ubuntu's
system Python environment.

## Run

After `bash gui/setup.sh`, EchoOS is in the Ubuntu applications menu and on the
desktop (right-click the desktop icon and choose "Allow Launching" if Ubuntu
asks). Click it: EchoOS opens as a normal app window, hands-free is on, and
saying "Hi Echo" followed by a command runs it. Closing the window closes EchoOS.

Start it at login too:

```bash
bash gui/install_launcher.sh --autostart
```

Remove the menu entry, desktop icon and autostart: `bash gui/install_launcher.sh --remove`.

From a terminal: `bash gui/run.sh`. Only one copy runs at a time when started
from the icon.

The app window shows a page served by a small local server. It binds to
`127.0.0.1` only (it is not reachable from the network), and you never need to
type the address. If the app window cannot start (no desktop, for example WSL),
open `http://127.0.0.1:5050` in a browser, or start browser-only mode with:

```bash
.venv/bin/python gui/app.py --server
```

## Audio checks

List the audio devices visible to the current user:

```bash
.venv/bin/python -c "import sounddevice as sd; print(sd.query_devices())"
```

If no input device is listed, check the Ubuntu microphone permissions and the
active ALSA/PulseAudio/PipeWire session. `ECHOOS_MIC` can select a specific
microphone by its device index or name.

The voice path uses `sounddevice`, `webrtcvad`, and `faster-whisper`. The first
voice command may need to download the configured Whisper model; that first
run therefore requires internet access. `ECHOOS_WHISPER` selects the model
(`tiny`, `base`, `small`, or `medium`).

## Optional settings

```bash
export ECHOOS_MIC="0"          # microphone index or device name
export ECHOOS_WHISPER="small" # tiny, base, small, or medium
export ECHOOS_GUI_SPEAK="1"   # also speak server replies with espeak-ng
```

Only set `ECHOOS_MIC` when you need to override the system default device.
The current `asr.py` implementation pins Whisper to English, so setting
`ECHOOS_LANG` to `ar` or `auto` does not currently switch the recognition
language. Fixing that requires a change outside the permitted `gui/` scope.

## Tests

From the repository root, with the virtual environment active:

```bash
source .venv/bin/activate
python -m pytest -rs
```

A passing import/setup check does not prove that a physical microphone works or
that a full live voice interaction succeeds. Those checks must be performed on
the target Ubuntu machine.

## Installation verification status

See [INSTALLATION_REPORT.md](INSTALLATION_REPORT.md) for the exact PASS,
FAIL, and NOT TESTED results. A fresh Ubuntu VM installation has not yet been
verified as part of this change.
