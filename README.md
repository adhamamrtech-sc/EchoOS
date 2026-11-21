# EchoOS

EchoOS is a Python-based, voice-controlled Ubuntu assistant. It listens for a wake phrase, turns speech into an intent, validates the requested operation, executes an allowed system action, and responds with spoken feedback.

> **Important:** This README describes the implementation currently on `main`. The fully local Decision Engine and the next Speech-to-Text / wake-word changes are planned work, not yet integrated into the default branch.

## Current runtime pipeline

1. **Audio capture — `audio.py`:** records speech using WebRTC VAD and can optionally apply noise reduction.
2. **Speech-to-text — `asr.py`:** transcribes the audio with Faster-Whisper. The current default is `large-v3-turbo`, running on CPU with INT8 compute.
3. **Wake phrase — `main.py`:** currently detects `Hi Echo` by matching the transcribed text. It is not yet a separate always-on keyword-spotting model.
4. **Intent understanding — `nlu/`:** builds a candidate from the local command catalog using rules, fuzzy matching, and semantic matching.
5. **Decision Engine — `nlu/llm_engine.py`:** validates high-confidence candidates and resolves uncertain requests through a provider. The current provider is Gemini, loaded lazily by `main.py`.
6. **Action execution — `actions/`:** executes only supported, allowlisted operations and applies confirmation requirements.
7. **Feedback — `feedback.py`:** speaks the result to the user.

### Offline status

Audio capture and the current Faster-Whisper transcription run locally after their required model assets are available. However, uncertain intent resolution currently uses the Gemini API. **The current `main` branch is therefore not a fully offline AI system.** The planned local Decision Engine is tracked in [the roadmap](docs/ROADMAP.md).

## Quick start (Ubuntu)

```bash
bash setup.sh
source .venv/bin/activate
cp .env.example .env
```

Edit `.env` and set `GEMINI_API_KEY` for the current Decision Engine provider, then run:

```bash
python main.py
```

Never commit `.env`, API keys, or other credentials. The repository's `.gitignore` excludes the local environment file.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `ECHOOS_MIC` | Microphone device number or name | System default |
| `ECHOOS_WHISPER` | Faster-Whisper model name | `large-v3-turbo` |
| `ECHOOS_LANG` | Transcription language (for example `en`, `ar`, or `auto`) | `auto` |
| `ECHOOS_DENOISE` | Set to `1` to enable optional noise reduction | Disabled |
| `GEMINI_API_KEY` | API key for the current remote intent provider | No default |
| `GEMINI_MODEL` | Gemini model used by the current provider | Provider default |
| `GEMINI_TIMEOUT_SECONDS` | Request timeout for the current provider | Provider default |

The Gemini settings describe the current implementation only. They will be revised when the local provider is integrated.

## Run the tests

```bash
pytest -rs
```

GitHub Actions runs the lightweight test suite on pushes and pull requests. Tests that need a physical microphone or an installed speech model may skip when those optional runtime dependencies are absent.

## Repository map

| Path | What belongs here |
| --- | --- |
| `main.py` | Application orchestration and the standby / active-session loop |
| `audio.py` | Microphone capture, VAD, denoising, and wake-phrase text matching |
| `asr.py` | Speech-to-text adapter |
| `nlu/` | Command catalog, normalization, matching, Decision Engine, and provider adapters |
| `actions/` | Allowlisted operating-system actions and safety checks |
| `feedback.py` | Spoken responses |
| `tests/` | Automated tests for modules and end-to-end flows |
| `benchmark.py` | ASR WER and latency benchmark; verify that the audio paths in its test cases exist before running |
| `docs/` | Architecture and development guidance |
| `INTERFACES.md` | Contracts exchanged between modules |
| `SECURITY.md` | Rules for safe action execution |
| `DECISIONS.md` | Team-level technical decisions |
| `CONTRIBUTING.md` | Branch, review, and testing workflow |

## Legacy / reference material

- **`project_os_full/`:** an earlier standalone Decision Engine / NLU snapshot. The active application imports from the root-level `nlu/` package; the top-level pytest configuration runs `tests/`, not `project_os_full/tests/`. Do not add new production features there. Review and port any still-useful regression tests before removing this snapshot.
- **`model/`:** an older Vosk US-English model. The current `asr.py` uses Faster-Whisper and does not load this directory. Keep it until the team confirms whether it is still needed for the offline speech-recognition direction.
- **Root-level WAV recordings:** benchmark/sample data, not application code. Treat recordings as personal data and do not add new recordings to the public repository without the speakers' permission.

For a deeper explanation of module boundaries and the planned local migration, read [Architecture](docs/ARCHITECTURE.md) and [Roadmap](docs/ROADMAP.md).
