"""Whisper ends sentences with a full stop. It must not change the meaning."""
import pytest

pytest.importorskip("rapidfuzz")

from nlu import understand
from nlu.normalize import normalize


@pytest.mark.parametrize("text, action, params", [
    ("Turn on Wi-Fi.", "set_wifi", {"state": "on"}),
    ("Turn off Bluetooth.", "set_bluetooth", {"state": "off"}),
    ("Set volume to 40.", "set_volume", {"value": 40}),
    ("Set brightness to 60.", "set_brightness", {"value": 60}),
    ("Make it louder.", "volume_up", {}),
    ("Lock my computer.", "lock_screen", {}),
    ("Turn on the Wi-Fi, please.", "set_wifi", {"state": "on"}),
])
def test_trailing_period_is_ignored(text, action, params):
    intent = understand(text)
    assert intent["action"] == action, intent
    assert intent["params"] == params
    assert intent["confidence"] >= 0.9


def test_filenames_keep_their_dots():
    assert normalize("open report.pdf.") == "open report.pdf"
    assert normalize("create file notes.txt") == "create file notes.txt"
