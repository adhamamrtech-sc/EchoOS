"""Record a short clip and inspect the audio and ASR output.

Run from the repository root:
    python -m tools.manual.check_audio_asr
"""

import numpy as np

from audio import record
from asr import transcribe


def main() -> None:
    print("Recording for 3 seconds...")
    audio_data = record(3)

    print(f"Audio type: {type(audio_data)}")
    print(f"NumPy array: {isinstance(audio_data, np.ndarray)}")
    print(f"Audio dtype: {audio_data.dtype}")
    print(f"Audio samples: {audio_data.size}")

    text = transcribe(audio_data)
    print(f"Transcription type: {type(text)}")
    print(f"Transcription: {text!r}")


if __name__ == "__main__":
    main()
