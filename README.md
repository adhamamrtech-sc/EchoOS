# EchoOS: Voice-Controlled Ubuntu

A voice-controlled Ubuntu system built in Python: speech replaces mouse clicks,
and AI turns spoken commands into system actions.

Pipeline: microphone -> speech-to-text -> intent understanding -> action -> spoken feedback.

## Files and owners

| File                                                                         | Owner                                                  |
| ---------------------------------------------------------------------------- | ------------------------------------------------------ |
| `audio.py`                                                                   | Audio Engineer                                         |
| `asr.py`                                                                     | ASR Engineer                                           |
| `nlu/`                                                                       | AI and Intent Engineer                                 |
| `actions/__init__.py`                                                        | Team Leader (owns the allowlist)                       |
| `actions/system_network.py`, `actions/apps_files.py`                         | Actions Engineers 1 and 2                              |
| `feedback.py`                                                                | Interface, Docs and QA Engineer                        |
| `main.py`                                                                    | Deputy Leader                                          |
| `setup.sh`, `requirements.txt`                                               | Team Leader and Deputy Leader                          |

Formats between modules and which commands really work: see `INTERFACES.md`.
Safety rules: see `SECURITY.md`. Team decisions: see `DECISIONS.md`.

## Setup (Ubuntu)

    bash setup.sh
    source .venv/bin/activate
    python main.py

Optional settings (set before `python main.py`):

| Variable          | Values                                  | Default |
| ----------------- | --------------------------------------- | ------- |
| `ECHOOS_MIC`      | microphone number or name               | system default |
| `ECHOOS_WHISPER`  | `tiny`, `base`, `small`, `medium`       | `small` |
| `ECHOOS_LANG`     | `en`, `ar`, `auto`                      | `en`    |

## GUI

A small window/page to type or speak commands and see the reply. It uses the
same pipeline as the voice loop (`main.process_text`), so a command behaves the
same in both. The bridge is `command_processor.py`; the page is in `gui/`.

    source .venv/bin/activate
    pip install -r gui/requirements.txt
    python gui/app.py            # opens the EchoOS window

Windows: run `gui\run.bat`. If the window library is missing it falls back to
the browser at http://localhost:5050. Hands-free is on by default: say
"Hi Echo", then your commands; silence ends the session. Turn it off with the
button at the top, and use the round button to record one command instead. Risky commands ask for confirmation: answer yes or no.
The server only accepts connections from the same computer.
Set `ECHOOS_GUI_SPEAK=1` to also speak replies from the server (espeak).

## Tests

    pytest -rs

Tests that need a microphone or a speech model skip themselves when the
library is missing. They also run on every push (GitHub Actions).
