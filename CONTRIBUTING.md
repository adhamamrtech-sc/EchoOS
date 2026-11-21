# Contributing to EchoOS

Thanks for contributing. EchoOS is a team project with shared contracts between audio, ASR, NLU, actions, and application integration. Keep changes focused so one subsystem does not unexpectedly break another.

## Branch workflow

- Keep `main` as the stable integration branch.
- Create a short-lived branch from the latest `main` for each task.
- Use clear names such as `feature/local-decision-provider`, `fix/wake-word-boundary`, `docs/architecture-guide`, or `chore/dependency-cleanup`.
- Open a pull request into `main`; do not push unfinished work directly to `main`.
- Avoid force-pushing shared branches. Coordinate before changing a file owned by another subsystem.

## Ownership and module boundaries

| Area | Main location | Responsibility |
| --- | --- | --- |
| Application integration | `main.py` | Connects the pipeline and manages standby / active sessions |
| Audio capture and wake phrase | `audio.py` | Microphone input, VAD, optional denoising, wake-phrase handling |
| Speech-to-text | `asr.py` | Converts audio arrays into text |
| Intent / Decision Engine | `nlu/` | Candidate generation, decision logic, provider integration, validation |
| System actions | `actions/` | Executes allowlisted operations |
| Feedback | `feedback.py` | Spoken output |
| Quality | `tests/`, `benchmark.py` | Regression tests and ASR measurements |

The ownership table in the README identifies the team's current role assignments. Ask the relevant owner before changing a shared interface.

## Rules for changes

1. Keep the contracts in [INTERFACES.md](INTERFACES.md) accurate. Update them in the same pull request when a function's input or output changes.
2. Preserve the safety boundary: an AI or ASR component may propose an intent, but only the action layer may execute an allowlisted operation.
3. Update [SECURITY.md](SECURITY.md) and add tests when introducing or changing a system action, confirmation flow, or permission requirement.
4. Keep providers replaceable. A Decision Engine provider must return structured data that is independently validated before an action can run.
5. Add or update tests with each behavior change. Do not rely only on a successful manual run.
6. Keep model weights, virtual environments, caches, API keys, and personal recordings out of new commits. Use `.env.example` for safe configuration examples.

## Before opening a pull request

- Run `pytest -rs` and report the result.
- Include any manual microphone / hardware checks that were required.
- List changed modules, dependency changes, and any behavior or interface changes.
- Call out safety implications and known limitations.
- Keep unrelated formatting, cleanup, and feature work in separate pull requests.
