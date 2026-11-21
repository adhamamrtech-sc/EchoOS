# EchoOS architecture

This document describes the code currently on `main` and identifies the seams intended for the next local-AI changes.

## Runtime flow

```text
Microphone
   |
   v
audio.listen_once()
   |
   +--> audio.record_until_silence()  [WebRTC VAD, optional denoising]
   |
   v
asr.transcribe()                     [Faster-Whisper]
   |
   v
main.py: wake phrase / session loop
   |
   v
nlu.understand()                     [local catalog + rules/fuzzy/semantic]
   |
   v
nlu.llm_engine.DecisionEngine
   |
   +--> high-confidence candidate --> validation
   |
   +--> uncertain candidate -------> provider.generate(...)
                                     [Gemini provider on current main]
   |
   v
actions.run()                        [allowlist + safety checks]
   |
   v
feedback.speak()
```

## Component responsibilities

### Application integration — `main.py`

Owns the application loop, standby and active-session behavior, the call into the Decision Engine, and the final handoff to actions and spoken feedback. It currently wraps Gemini in `LazyGeminiProvider` so the SDK and API key are needed only when the provider is actually called.

### Audio capture and wake phrase — `audio.py`

- Captures mono audio at 16 kHz.
- Uses WebRTC VAD to detect speech start and silence-based end-of-utterance.
- Can apply noise reduction when `ECHOOS_DENOISE=1`.
- Provides `strip_wake_word()`, which matches variations of the phrase at the start of recognized text.

**Current limitation:** wake-phrase detection happens after ASR has produced text. It is not a separate always-on keyword-spotting model. The main loop uses the recognized phrase to activate a session; subsequent commands in the active session do not need the phrase again.

### Speech-to-text — `asr.py`

Uses Faster-Whisper with `large-v3-turbo` by default, CPU execution, and INT8 compute. The public boundary is `transcribe(audio, language=None) -> str`; audio is expected as a mono 16 kHz NumPy array. Keep this boundary stable when evaluating or replacing the ASR model.

### Intent and Decision Engine — `nlu/`

- `catalog.py` defines known commands, applications, folders, and examples.
- `normalize.py`, `rules.py`, `fuzzy.py`, `entities.py`, `ranking.py`, and `semantic.py` help create and rank local intent candidates.
- `understand.py` exposes the NLU entry point.
- `llm_engine.py` coordinates candidate confidence, context, provider calls, and validation.
- `llm_validator.py` validates provider output against the allowed action set and safety rules.
- `gemini_provider.py` is the current remote provider adapter.
- `llm_provider.py` contains a mock provider used for controlled/test scenarios.

The Decision Engine accepts a provider object with a `generate(...)` method. That is the primary integration boundary for replacing Gemini with an on-device model.

### Actions and feedback

`actions/` owns real operating-system operations. It must remain the only layer that executes them. Risky operations must preserve explicit confirmation, safe-path checks, and the rules in [SECURITY.md](../SECURITY.md). `feedback.py` speaks the result back to the user.

## Local-AI migration boundaries

The planned migration should be done in isolated steps:

1. Add a local provider adapter behind the existing provider interface; do not mix model-runtime code into `main.py` or the action layer.
2. Keep provider output structured and pass it through the existing validator. A local model must not be trusted to authorize or execute an operation.
3. Add tests for provider-unavailable behavior, malformed output, ambiguous commands, context/clarification turns, and dangerous-action confirmation.
4. Remove Gemini-specific dependencies and environment variables only after the local provider is the active, tested path.
5. Measure startup time, inference latency, RAM/VRAM usage, and accuracy on the team's representative Arabic and English commands.

The current main branch still contains and uses the Gemini adapter for uncertain intent resolution. Do not remove it as an isolated cleanup task before the local replacement is integrated.

## Where to read next

- Module contracts: [INTERFACES.md](../INTERFACES.md)
- Action safety: [SECURITY.md](../SECURITY.md)
- Planned work: [ROADMAP.md](ROADMAP.md)
- Team workflow: [CONTRIBUTING.md](../CONTRIBUTING.md)
