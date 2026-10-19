"""Smoke test: every module can be imported."""
import pytest


def test_light_modules_import():
    pytest.importorskip("rapidfuzz")
    import nlu
    import actions


def test_audio_modules_import():
    pytest.importorskip("numpy")
    pytest.importorskip("sounddevice")
    pytest.importorskip("faster_whisper")
    import audio
    import asr
    import feedback
    import main