"""End-to-end flow of main() with fake microphone, ASR and speaker."""
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

pytest.importorskip("rapidfuzz")


def load_main(heard):
    """Import main with fake audio/asr/feedback. heard = what ASR returns, in order."""
    said = []
    answers = iter(heard)

    fake_audio = types.ModuleType("audio")
    fake_audio.record = lambda seconds=5: [0.0]
    fake_asr = types.ModuleType("asr")
    fake_asr.transcribe = lambda audio: next(answers)
    fake_feedback = types.ModuleType("feedback")
    fake_feedback.speak = said.append

    fakes = {"audio": fake_audio, "asr": fake_asr, "feedback": fake_feedback}

    # Swap only our three fakes. (patch.dict would also unload numpy and
    # other C modules imported meanwhile, which breaks later tests.)
    saved = {name: sys.modules.get(name) for name in fakes}
    sys.modules.update(fakes)
    sys.modules.pop("main", None)

    try:
        import main as loaded
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

        sys.modules.pop("main", None)

    return loaded, said


def run_flow(heard):
    loaded, said = load_main(heard)

    with mock.patch("subprocess.run") as sub:
        sub.return_value = mock.Mock(stdout="", stderr="")
        loaded.main()

    return said, sub


def test_main_is_runnable_as_a_script():
    source = Path("main.py").read_text(encoding="utf-8")
    assert 'if __name__ == "__main__"' in source
    assert "from audio import record" in source


@pytest.mark.parametrize("answer, expected", [
    ("Yes.", True), ("yes, please", True), ("Yeah!", True), ("ايوه", True), ("أيوه", True),
    ("yesterday", False), ("not sure", False), ("No.", False), ("maybe", False),
    ("", False), (None, False), ("لا", False),
])
def test_is_yes(answer, expected):
    loaded, _ = load_main(["x"])
    assert loaded.is_yes(answer) is expected


def test_known_command_runs():
    said, sub = run_flow(["make it louder"])
    assert sub.call_args[0][0] == ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"]
    assert said == ["Volume increased"]


def test_unknown_command_gets_a_clear_message():
    said, sub = run_flow(["tell me a joke about cats"])
    assert said == ["Sorry, I didn't understand that."]
    sub.assert_not_called()


def test_silence_gets_a_clear_message():
    said, sub = run_flow([""])
    assert said == ["I didn't hear anything."]
    sub.assert_not_called()


def test_wifi_off_runs_only_after_a_clear_yes():
    said, sub = run_flow(["turn off wifi", "Yes."])
    assert sub.call_args[0][0] == ["nmcli", "radio", "wifi", "off"]
    assert said[-1] == "Wi-Fi turned off"


@pytest.mark.parametrize("answer", [
    "no", "No, cancel", "yesterday", "I am not sure", "maybe", "", "لا", "بلاش",
])
def test_wifi_off_is_cancelled_without_a_clear_yes(answer):
    said, sub = run_flow(["turn off wifi", answer])
    sub.assert_not_called()
    assert said[-1] == "Cancelled."


def test_bluetooth_off_also_needs_confirmation():
    said, sub = run_flow(["turn off bluetooth", "yeah"])
    assert sub.call_args[0][0] == ["rfkill", "block", "bluetooth"]
