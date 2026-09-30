# EchoOS: Voice-Controlled Ubuntu

A voice-controlled Ubuntu system built in Python: speech replaces mouse clicks,
and AI turns spoken commands into system actions.

Pipeline: microphone -> speech-to-text -> intent understanding -> action -> spoken feedback.

## Files and owners

| File | Owner |
| --- | --- |
| audio.py | Audio Engineer |
| asr.py | ASR Engineer |
| nlu.py | AI and Intent Engineer |
| actions.py | Actions Engineers 1 and 2 |
| feedback.py | Interface, Docs and QA Engineer |
| main.py | Deputy Leader |
| setup.sh, requirements.txt | Team Leader and Deputy Leader |

## Setup (Ubuntu)

    bash setup.sh
    source .venv/bin/activate
    python main.py
