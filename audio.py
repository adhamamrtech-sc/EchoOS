
"""Microphone capture. Owner: Audio Engineer."""

import os
import re
import time
from collections import deque

import numpy as np


SAMPLE_RATE = 16000

_WAKE_RE = re.compile(
    r"^\W*(?:hi|hey|high|hai)[\s,]+"
    r"(?:echo|eco|ecco|ekko|eko|ecko|equal|eiko|iko)\b[\s,.!?:;-]*",
    re.IGNORECASE,
)


def _device():
    """Default microphone, or the one named in ECHOOS_MIC."""
    value = os.environ.get("ECHOOS_MIC")

    if not value:
        return None

    return int(value) if value.isdigit() else value


def record(seconds=5):
    """Record mono audio at 16 kHz and return a 1-D float32 array."""
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("seconds must be a positive number")

    if seconds <= 0:
        raise ValueError("seconds must be greater than zero")

    import sounddevice as sd

    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=_device(),
    )
    sd.wait()

    return np.asarray(audio, dtype=np.float32).reshape(-1)


def denoise(audio):
    """Reduce background noise. Needs the noisereduce package."""
    import noisereduce as nr

    audio = np.asarray(audio, dtype=np.float32).reshape(-1)

    return nr.reduce_noise(
        y=audio,
        sr=SAMPLE_RATE,
    ).astype(np.float32)


def record_until_silence(
    max_seconds=15,
    silence_ms=800,
    start_timeout=8,
    vad_mode=2,
    apply_denoise=None,
):
    """Record one sentence, starting at speech and stopping after silence.

    Returns a 1-D float32 array at 16 kHz.
    Returns an empty array if no speech is detected before start_timeout.
    """

    if max_seconds <= 0:
        raise ValueError("max_seconds must be greater than zero")

    if silence_ms <= 0:
        raise ValueError("silence_ms must be greater than zero")

    if start_timeout <= 0:
        raise ValueError("start_timeout must be greater than zero")

    if isinstance(vad_mode, bool) or vad_mode not in (0, 1, 2, 3):
        raise ValueError("vad_mode must be between 0 and 3")

    if apply_denoise is None:
        apply_denoise = os.environ.get("ECHOOS_DENOISE") == "1"

    import sounddevice as sd
    import webrtcvad

    frame_ms = 30
    frame_len = int(SAMPLE_RATE * frame_ms / 1000)

    vad = webrtcvad.Vad(vad_mode)

    pre_roll = deque(maxlen=10)
    frames = []

    triggered = False
    silence = 0
    started_at = time.monotonic()

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=frame_len,
        channels=1,
        dtype="int16",
        device=_device(),
    ) as stream:

        while True:
            data, overflowed = stream.read(frame_len)
            data = bytes(data)

            is_speech = vad.is_speech(data, SAMPLE_RATE)

            if not triggered:
                pre_roll.append(data)

                if is_speech:
                    triggered = True
                    frames.extend(pre_roll)
                    silence = 0

                elif time.monotonic() - started_at >= start_timeout:
                    return np.zeros(0, dtype=np.float32)

            else:
                frames.append(data)

                silence = (
                    0 if is_speech else silence + frame_ms
                )

                too_long = (
                    len(frames) * frame_ms >= max_seconds * 1000
                )

                if silence >= silence_ms or too_long:
                    break

    audio = np.frombuffer(
        b"".join(frames),
        dtype=np.int16,
    )

    audio = audio.astype(np.float32) / 32768.0

    if apply_denoise:
        return denoise(audio)

    return audio


def strip_wake_word(text):
    """Detect 'Hi Echo' at the beginning and return the remaining command."""
    text = text or ""
    match = _WAKE_RE.match(text)

    if match:
        return True, text[match.end():].strip()

    return False, text.strip()


def listen_once(
    require_wake_word=True,
    language=None,
    apply_denoise=None,
    start_timeout=8,
    max_seconds=15,
    silence_ms=800,
    vad_mode=2,
):
    """Record one sentence and return its recognized text, or ''."""

    from asr import transcribe

    audio = record_until_silence(
        max_seconds=max_seconds,
        silence_ms=silence_ms,
        start_timeout=start_timeout,
        vad_mode=vad_mode,
        apply_denoise=apply_denoise,
    )

    if audio.size == 0:
        return ""

    text = transcribe(audio, language=language)

    if not require_wake_word:
        return text

    heard, command = strip_wake_word(text)

    return command if heard else ""
