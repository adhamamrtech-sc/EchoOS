"""Record a 10-second WAV sample for an approved benchmark.

Run from the repository root:
    python -m tools.manual.record_samples

Audio is written to recordings/, which is intentionally git-ignored.
Obtain the speaker's permission before recording or sharing their voice.
"""

from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np

from audio import record


def main() -> None:
    raw_name = input("Sample label (for example, speaker_01): ").strip()
    label = re.sub(r"[^A-Za-z0-9_-]+", "_", raw_name).strip("_") or "sample"
    output_dir = Path("recordings")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{label}.wav"

    print("Recording for 10 seconds. Speak now...")
    audio = record(10)
    pcm = np.clip(audio * 32767.0, -32768, 32767).astype("<i2")

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(pcm.tobytes())

    print(f"Sample saved to: {output_path}")


if __name__ == "__main__":
    main()
