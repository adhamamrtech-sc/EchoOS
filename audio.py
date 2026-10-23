"""Microphone capture. Owner: Audio Engineer."""
import os

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


def _device():
    """Default microphone, or the one named in ECHOOS_MIC (number or name)."""
    value = os.environ.get("ECHOOS_MIC")

    if not value:
        return None

    return int(value) if value.isdigit() else value


def record(seconds=5):
    """Record mono audio at 16 kHz and return a 1-D float32 array."""
    if seconds <= 0:
        raise ValueError("seconds must be greater than zero")

    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=_device(),
    )
    sd.wait()

    return np.asarray(audio, dtype=np.float32).reshape(-1)