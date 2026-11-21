# Manual development tools

These scripts are for developer checks and are **not** part of the automated test suite.

Run commands from the repository root:

| Command | Purpose |
| --- | --- |
| `python -m tools.manual.check_nlu_commands` | Print NLU results for a short Arabic / English command list |
| `python -m tools.manual.check_audio_asr` | Record 3 seconds and inspect the audio array and transcription |
| `python -m tools.manual.check_live_pipeline` | Run a fixed-duration microphone-to-ASR check |
| `python -m tools.manual.record_samples` | Record a 10-second WAV sample into `recordings/` |

The audio tools require a working microphone and the relevant audio / ASR dependencies. The ASR model may need to be downloaded on first use.

Recordings are private data. The `recordings/` output directory is git-ignored. Obtain the speaker's permission before collecting or sharing voice samples.
