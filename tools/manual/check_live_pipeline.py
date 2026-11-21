"""Manually test fixed-duration microphone recording and transcription.

Run from the repository root:
    python -m tools.manual.check_live_pipeline
"""

from audio import record
from asr import transcribe


def main() -> None:
    print("Speak now. The microphone will record for 5 seconds.")
    audio_array = record(5)

    if audio_array.size == 0:
        print("No audio was captured.")
        return

    print("Recording complete. Transcribing...")
    print(f"Transcription: {transcribe(audio_array)!r}")


if __name__ == "__main__":
    main()
