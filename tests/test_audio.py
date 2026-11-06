
"""Unit tests for audio recording, VAD, wake word and ASR integration."""

import sys
import types
from unittest import mock

import numpy as np
import pytest

import audio


# ---------------------------------------------------------------------
# Device configuration
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        ("", None),
        ("2", 2),
        ("0", 0),
        ("USB Microphone", "USB Microphone"),
    ],
)
def test_device_configuration(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("ECHOOS_MIC", raising=False)
    else:
        monkeypatch.setenv("ECHOOS_MIC", value)

    assert audio._device() == expected


# ---------------------------------------------------------------------
# Fixed-duration recording
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "seconds",
    [0, -1, -0.5, True, False, "5", None],
)
def test_record_rejects_invalid_duration(seconds):
    with pytest.raises(ValueError):
        audio.record(seconds)


def test_record_returns_flat_float32_audio(monkeypatch):
    fake_sd = types.ModuleType("sounddevice")
    fake_sd.rec = mock.Mock(
        return_value=np.array([[0.1], [0.2]], dtype=np.float32)
    )
    fake_sd.wait = mock.Mock()

    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)

    result = audio.record(2)

    assert result.shape == (2,)
    assert result.dtype == np.float32

    fake_sd.rec.assert_called_once_with(
        32000,
        samplerate=16000,
        channels=1,
        dtype="float32",
        device=None,
    )

    fake_sd.wait.assert_called_once()


# ---------------------------------------------------------------------
# Denoising
# ---------------------------------------------------------------------

def test_denoise_uses_noisereduce(monkeypatch):
    fake_nr = types.ModuleType("noisereduce")
    received = {}

    def fake_reduce_noise(y, sr):
        received["audio"] = y
        received["sample_rate"] = sr
        return y * 0.5

    fake_nr.reduce_noise = fake_reduce_noise
    monkeypatch.setitem(sys.modules, "noisereduce", fake_nr)

    source = np.array([[1.0], [0.5]], dtype=np.float64)
    result = audio.denoise(source)

    assert result.shape == (2,)
    assert result.dtype == np.float32

    np.testing.assert_allclose(result, [0.5, 0.25])

    assert received["sample_rate"] == 16000
    assert received["audio"].dtype == np.float32


# ---------------------------------------------------------------------
# Wake word
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hi Echo", (True, "")),
        ("Hi Echo, open Chrome", (True, "open Chrome")),
        ("Hey Echo, make it louder", (True, "make it louder")),
        ("Hai Echo open YouTube", (True, "open YouTube")),
        ("Hi Eco, open Chrome", (True, "open Chrome")),
        ("Hi Ecco, open Chrome", (True, "open Chrome")),
        ("HI ECHO, open Chrome", (True, "open Chrome")),
        ("  Hi Echo, open Chrome", (True, "open Chrome")),
        ("hello echo", (False, "hello echo")),
        ("open Chrome", (False, "open Chrome")),
        ("Echo, open Chrome", (False, "Echo, open Chrome")),
        ("", (False, "")),
        (None, (False, "")),
    ],
)
def test_strip_wake_word(text, expected):
    assert audio.strip_wake_word(text) == expected


# ---------------------------------------------------------------------
# VAD recording helpers
# ---------------------------------------------------------------------

class FakeStream:
    """Fake sounddevice stream returning predefined frames."""

    def __init__(self, frames):
        self.frames = iter(frames)
        self.read_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, frame_len):
        self.read_calls += 1
        return next(self.frames), False


class FakeVAD:
    """Fake WebRTC VAD with predefined speech decisions."""

    def __init__(self, decisions):
        self.decisions = iter(decisions)

    def is_speech(self, frame, sample_rate):
        assert sample_rate == 16000
        return next(self.decisions)


def install_fake_vad(monkeypatch, frames, decisions):
    fake_sd = types.ModuleType("sounddevice")
    fake_stream = FakeStream(frames)

    fake_sd.RawInputStream = mock.Mock(
        return_value=fake_stream
    )

    fake_webrtcvad = types.ModuleType("webrtcvad")
    fake_vad = FakeVAD(decisions)

    fake_webrtcvad.Vad = mock.Mock(
        return_value=fake_vad
    )

    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
    monkeypatch.setitem(sys.modules, "webrtcvad", fake_webrtcvad)

    return fake_sd, fake_stream, fake_vad


def make_frame(value):
    """Create one valid 30 ms, 16 kHz, mono int16 frame."""
    return np.full(480, value, dtype=np.int16).tobytes()


# ---------------------------------------------------------------------
# VAD validation
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_seconds": 0},
        {"max_seconds": -1},
        {"silence_ms": 0},
        {"silence_ms": -1},
        {"start_timeout": 0},
        {"start_timeout": -1},
        {"vad_mode": -1},
        {"vad_mode": 4},
        {"vad_mode": True},
    ],
)
def test_record_until_silence_rejects_invalid_arguments(kwargs):
    with pytest.raises(ValueError):
        audio.record_until_silence(**kwargs)


# ---------------------------------------------------------------------
# VAD recording behavior
# ---------------------------------------------------------------------

def test_record_until_silence_returns_empty_when_no_speech(
    monkeypatch,
):
    frames = [make_frame(100)] * 3

    install_fake_vad(
        monkeypatch,
        frames,
        [False, False, False],
    )

    with mock.patch.object(
        audio.time,
        "monotonic",
        side_effect=[0, 10],
    ):
        result = audio.record_until_silence(
            start_timeout=1,
            apply_denoise=False,
        )

    assert result.shape == (0,)
    assert result.dtype == np.float32


def test_record_until_silence_keeps_preroll_and_stops_after_silence(
    monkeypatch,
):
    frames = [
        make_frame(100),
        make_frame(200),
        make_frame(300),
        make_frame(400),
    ]

    install_fake_vad(
        monkeypatch,
        frames,
        [False, True, False, False],
    )

    result = audio.record_until_silence(
        silence_ms=60,
        apply_denoise=False,
    )

    expected = np.frombuffer(
        b"".join(frames),
        dtype=np.int16,
    ).astype(np.float32) / 32768.0

    np.testing.assert_allclose(result, expected)
    assert result.dtype == np.float32


def test_record_until_silence_applies_denoising(monkeypatch):
    frames = [
        make_frame(100),
        make_frame(200),
    ]

    install_fake_vad(
        monkeypatch,
        frames,
        [True, False],
    )

    denoised = np.array([0.25, 0.5], dtype=np.float32)

    with mock.patch.object(
        audio,
        "denoise",
        return_value=denoised,
    ) as denoise_mock:
        result = audio.record_until_silence(
            silence_ms=30,
            apply_denoise=True,
        )

    denoise_mock.assert_called_once()
    np.testing.assert_array_equal(result, denoised)


def test_record_until_silence_uses_environment_denoise_setting(
    monkeypatch,
):
    frames = [
        make_frame(100),
        make_frame(200),
    ]

    install_fake_vad(
        monkeypatch,
        frames,
        [True, False],
    )

    monkeypatch.setenv("ECHOOS_DENOISE", "1")

    with mock.patch.object(
        audio,
        "denoise",
        return_value=np.array([0.5], dtype=np.float32),
    ) as denoise_mock:
        result = audio.record_until_silence(
            silence_ms=30,
        )

    denoise_mock.assert_called_once()

    np.testing.assert_array_equal(
        result,
        np.array([0.5], dtype=np.float32),
    )


# ---------------------------------------------------------------------
# listen_once and ASR integration
# ---------------------------------------------------------------------

def install_fake_asr(monkeypatch, text):
    fake_asr = types.ModuleType("asr")
    fake_asr.transcribe = mock.Mock(return_value=text)

    monkeypatch.setitem(sys.modules, "asr", fake_asr)

    return fake_asr


def test_listen_once_returns_empty_when_no_audio(monkeypatch):
    install_fake_asr(monkeypatch, "Hi Echo")

    with mock.patch.object(
        audio,
        "record_until_silence",
        return_value=np.zeros(0, dtype=np.float32),
    ):
        result = audio.listen_once()

    assert result == ""


def test_listen_once_transcribes_and_requires_wake_word(
    monkeypatch,
):
    fake_asr = install_fake_asr(
        monkeypatch,
        "Hi Echo, make it louder",
    )

    recorded = np.array([0.1, 0.2], dtype=np.float32)

    with mock.patch.object(
        audio,
        "record_until_silence",
        return_value=recorded,
    ):
        result = audio.listen_once()

    assert result == "make it louder"

    fake_asr.transcribe.assert_called_once()

    np.testing.assert_array_equal(
        fake_asr.transcribe.call_args.args[0],
        recorded,
    )


def test_listen_once_returns_text_without_wake_word_when_not_required(
    monkeypatch,
):
    fake_asr = install_fake_asr(
        monkeypatch,
        "make it louder",
    )

    with mock.patch.object(
        audio,
        "record_until_silence",
        return_value=np.array([0.1], dtype=np.float32),
    ):
        result = audio.listen_once(require_wake_word=False)

    assert result == "make it louder"
    fake_asr.transcribe.assert_called_once()


def test_listen_once_rejects_text_without_wake_word(monkeypatch):
    install_fake_asr(monkeypatch, "open Chrome")

    with mock.patch.object(
        audio,
        "record_until_silence",
        return_value=np.array([0.1], dtype=np.float32),
    ):
        result = audio.listen_once(require_wake_word=True)

    assert result == ""


def test_listen_once_passes_recording_options(monkeypatch):
    fake_asr = install_fake_asr(monkeypatch, "Hi Echo")

    with mock.patch.object(
        audio,
        "record_until_silence",
        return_value=np.array([0.1], dtype=np.float32),
    ) as record_mock:
        audio.listen_once(
            language="en",
            apply_denoise=True,
            start_timeout=5,
            max_seconds=10,
            silence_ms=500,
            vad_mode=3,
        )

    record_mock.assert_called_once_with(
        max_seconds=10,
        silence_ms=500,
        start_timeout=5,
        vad_mode=3,
        apply_denoise=True,
    )

    assert fake_asr.transcribe.call_args.kwargs == {
        "language": "en"
    }
