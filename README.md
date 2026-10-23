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

## Tests

    pytest -rs

Tests that need a microphone or a speech model skip themselves when the
library is missing. They also run on every push (GitHub Actions).
