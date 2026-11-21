# EchoOS roadmap

This roadmap separates the working implementation from the changes the team has said it intends to make. A roadmap item is not complete until its implementation is merged into `main` with tests.

## Current baseline on main

| Subsystem | Current implementation | Status |
| --- | --- | --- |
| Audio capture | 16 kHz microphone capture with WebRTC VAD and optional denoising | Implemented |
| Speech-to-text | Faster-Whisper `large-v3-turbo`, CPU / INT8 | Implemented; under evaluation |
| Wake phrase | Text matching for `Hi Echo` after transcription | Implemented; redesign planned |
| Local intent matching | Catalog, rules, fuzzy matching, semantic embeddings | Implemented |
| Uncertain-intent provider | Gemini API through `GeminiProvider` | Current; planned for replacement |
| Safe action execution | Allowlisted actions, validation, and confirmation rules | Implemented |

## Next work

### 1. Replace Gemini with a local Decision Engine provider

**Goal:** resolve uncertain commands without a cloud API or API key.

- Choose and document the local inference runtime and model after evaluating hardware, language coverage, latency, and memory requirements.
- Implement the local adapter behind the existing provider `generate(...)` contract.
- Preserve the Decision Engine's output validation, context handling, clarification behavior, and confirmation boundary.
- Add tests proving that the local path makes no network/API request and cannot bypass action validation.
- Only then remove Gemini-specific imports, dependencies, configuration, and obsolete provider tests.

### 2. Improve and stabilize Speech-to-Text

**Goal:** make transcription reliable for the team's real English and Arabic commands.

- Keep the `transcribe(audio, language=None) -> str` boundary stable.
- Evaluate model variants using the same held-out recordings.
- Track WER, latency, CPU/RAM usage, startup cost, and behavior on short commands.
- Keep downloaded model weights and private recordings outside the Git repository; store benchmark metadata and instructions in Git.
- Ensure the runtime dependencies and setup instructions match the chosen ASR implementation.

### 3. Redesign wake-word handling

**Goal:** make standby detection dependable without repeatedly transcribing unnecessary audio.

- Decide whether to keep transcript-based matching or adopt a dedicated local keyword detector.
- Measure false accepts, missed wake phrases, detection latency, and idle CPU/RAM use.
- Preserve the current interaction contract: wake phrase activates a session; commands inside the active session do not require repeating it.
- Add tests for spelling/transcription variants, false positives, timeouts, and session transitions.

### 4. Integrate and verify

- Test the complete microphone-to-action path on the target Ubuntu environment.
- Run unit, integration, and safety tests.
- Update `INTERFACES.md`, `SECURITY.md`, `.env.example`, `requirements.txt`, and the README whenever behavior or setup changes.
- Merge each subsystem through a focused pull request.

## Definition of done

A subsystem is ready to merge when its owner has added regression tests, its public interface is documented, its dependencies are declared, its safety implications are reviewed, and the relevant CI checks pass.
