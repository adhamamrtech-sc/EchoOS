"""Microphone capture. Owner: Audio Engineer."""
import os
import re
import time
from collections import deque

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000

# Whisper may spell the wake word differently ("High equal", "Hai Eiko"),
# so the pattern accepts the common variants. Only matches at the start.
_WAKE_RE = re.compile(
    r"^\W*(?:hi|hey|high|hai)[\s,]+"
    r"(?:echo|eco|ecco|ekko|eko|ecko|equal|eiko|iko)\b[\s,.!?:;-]*",
    re.IGNORECASE,
)


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


def denoise(audio):
    """Reduce background noise. Needs the noisereduce package."""
    import noisereduce as nr

    return nr.reduce_noise(y=audio, sr=SAMPLE_RATE).astype(np.float32)


def record_until_silence(max_seconds=15, silence_ms=800, start_timeout=8,
                         vad_mode=2, apply_denoise=None):
    """Record one sentence: start when speech begins, stop after silence.

    Returns a 1-D float32 array at 16 kHz, or an empty array if nobody spoke.
    Noise reduction is off by default; turn it on with apply_denoise=True
    or by setting ECHOOS_DENOISE=1. Needs the webrtcvad-wheels package.
    """
    import webrtcvad

    if apply_denoise is None:
        apply_denoise = os.environ.get("ECHOOS_DENOISE") == "1"

    frame_ms = 30
    frame_len = int(SAMPLE_RATE * frame_ms / 1000)
    vad = webrtcvad.Vad(vad_mode)

    pre_roll = deque(maxlen=10)  # ~300 ms kept so the first word is not cut
    frames = []
    triggered = False
    silence = 0
    started_at = time.time()

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=frame_len,
                           channels=1, dtype="int16",
                           device=_device()) as stream:
        while True:
            data, _ = stream.read(frame_len)
            data = bytes(data)
            is_speech = vad.is_speech(data, SAMPLE_RATE)

            if not triggered:
                pre_roll.append(data)
                if is_speech:
                    triggered = True
                    frames.extend(pre_roll)
                    silence = 0
                elif time.time() - started_at > start_timeout:
                    return np.zeros(0, dtype=np.float32)
            else:
                frames.append(data)
                silence = 0 if is_speech else silence + frame_ms
                too_long = len(frames) * frame_ms >= max_seconds * 1000
                if silence >= silence_ms or too_long:
                    break

    audio = np.frombuffer(b"".join(frames), dtype=np.int16)
    audio = audio.astype(np.float32) / 32768.0

    return denoise(audio) if apply_denoise else audio


def strip_wake_word(text):
    """Check for the wake word 'Hi Echo' at the start of a sentence.

    Returns (heard, command): heard is True if the wake word was found,
    and command is the rest of the sentence with its original spelling.
    """
    match = _WAKE_RE.match(text or "")

    if match:
        return True, text[match.end():].strip()

    return False, (text or "").strip()


def listen_once(require_wake_word=True, language=None, apply_denoise=None):
    """Record one sentence and return its text, or '' if nothing usable.

    With require_wake_word=True the sentence must start with 'Hi Echo';
    the wake word is removed and only the command is returned.
    Uses asr.transcribe, so it follows the same contract: a text string.
    """
    from asr import transcribe

    audio = record_until_silence(apply_denoise=apply_denoise)

    if audio.size == 0:
        return ""

    text = transcribe(audio, language=language)
    heard, command = strip_wake_word(text)

    if require_wake_word:
        return command if heard else ""

    return text
