# EchoOS GUI Ubuntu Installation — Test Report

Target branch: `gui-integration`  
Scope: `gui/` only  
Status: static and repository-side preparation; no clean Ubuntu VM was available
for this run.

## Results

| Step | Status | Evidence / limitation |
|---|---|---|
| Inspect GUI entry point and its direct imports | PASS | `gui/app.py` imports Flask, `command_processor`, `main`, and `audio`. |
| Trace GUI-to-core dependency path | PASS | `command_processor.py` imports `main.py`; `main.py` imports `audio.py` and NLU/actions. |
| Check direct audio/ASR imports | PASS | `audio.py` imports NumPy at module load and uses sounddevice/webrtcvad; `listen_once()` imports `asr.py`, which imports NumPy and faster-whisper. |
| Check Flask dependency | PASS | Flask was already listed in `gui/requirements.txt`; it remains explicit. |
| Provide missing direct Python dependencies in GUI scope | PASS | `gui/requirements.txt` now declares NumPy, sounddevice, and faster-whisper. Root-level requirements were intentionally not changed. |
| Handle Ubuntu system audio/action packages | PASS | `gui/setup.sh` installs PortAudio, ALSA/PulseAudio tools, FFmpeg, NetworkManager, rfkill, brightnessctl, and espeak-ng. |
| Avoid Ubuntu system-Python pip installation | PASS | `gui/setup.sh` creates/reuses the project `.venv`; `gui/run.sh` refuses to fall back to system Python. |
| Useful setup/launcher errors | PASS | Both scripts report the failed step and the corrective command. |
| Shell syntax (`bash -n`) | PASS | Both new/updated shell scripts passed syntax validation in the available Linux tooling container. |
| GUI requirements syntax | PASS | All requirement lines parsed successfully with Python Packaging's requirement parser. |
| Launcher missing-environment handling | PASS | `gui/run.sh` exited cleanly with the exact `bash gui/setup.sh` remediation when `.venv/` was absent. |
| Fresh Ubuntu VM: apt installation | NOT TESTED | No clean Ubuntu VM was available in this execution environment. |
| Fresh Ubuntu VM: pip installation | NOT TESTED | No package installation was run on a clean Ubuntu VM. |
| Real microphone capture | NOT TESTED | Requires an Ubuntu desktop/session with a working microphone. |
| First Whisper model download and transcription | NOT TESTED | Requires network access and a live audio test on the target machine. |
| Browser GUI in an Ubuntu desktop session | NOT TESTED | The server launch path is documented, but no real desktop/browser session was exercised. |
| Optional Linux native WebView window | NOT TESTED | Browser mode is the documented default; WebKitGTK/pywebview native mode is not installed by this setup. |
| Full end-to-end OS actions | NOT TESTED | Requires a target Ubuntu machine and deliberate validation of system actions. |

## Confirmed issues found in the pre-change GUI setup

1. `gui/run.sh` could fall back to the system `python3` and run `pip install` there.
   On Ubuntu releases enforcing externally-managed Python environments, that
   can fail; it also bypassed the core dependencies in the repository-root
   requirements file.
2. The repository-root `requirements.txt` does not directly declare NumPy,
   sounddevice, or faster-whisper, although the GUI's shared core/audio path
   uses them. NumPy may arrive transitively in some environments, but that is
   not a reliable direct dependency declaration.
3. `gui/requirements.txt` already declared Flask, so Flask was not missing from
   the GUI-specific dependency file.
4. The shared `asr.py` currently passes a hard-coded `language="en"` to
   faster-whisper. Consequently, `ECHOOS_LANG=ar` or `auto` does not currently
   change recognition language. This is outside the permitted `gui/` scope and
   was not modified.

## Remaining limitation

The repository-root `requirements.txt`, `setup.sh`, and `README.md` were left
unchanged to respect the requested `gui/`-only scope. The new
`gui/setup.sh` compensates for the GUI installation by installing both the
root and GUI requirement files, with the GUI-specific file explicitly adding
the missing direct audio/ASR dependencies. The root-level CLI installation
path has therefore not been repaired or certified by this GUI-scoped task.
