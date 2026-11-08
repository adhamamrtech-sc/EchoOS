
"""End-to-end flow of main() with fake microphone and speaker."""

import sys
import types
from pathlib import Path
from unittest import mock

import pytest

pytest.importorskip("rapidfuzz")

from audio import strip_wake_word as real_strip_wake_word


def load_main(heard):
    """Import main with fake audio and feedback modules."""
    said = []
    answers = iter(heard)

    fake_audio = types.ModuleType("audio")
    fake_audio.listen_once = lambda **kwargs: next(answers, "")
    fake_audio.strip_wake_word = real_strip_wake_word

    fake_feedback = types.ModuleType("feedback")
    fake_feedback.speak = said.append

    fakes = {
        "audio": fake_audio,
        "feedback": fake_feedback,
    }

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


def run_flow(heard, max_commands=1):
    loaded, said = load_main(heard)

    with mock.patch("subprocess.run") as sub:
        sub.return_value = mock.Mock(stdout="", stderr="")
        loaded.main(
            max_commands=max_commands,
            max_listens=len(heard),
        )

    return said, sub


def test_main_is_runnable_as_a_script():
    source = Path("main.py").read_text(encoding="utf-8")

    assert 'if __name__ == "__main__"' in source
    assert "from audio import listen_once, strip_wake_word" in source


@pytest.mark.parametrize("answer, expected", [
    ("Yes.", True),
    ("yes, please", True),
    ("Yeah!", True),
    ("yes yes", True),
    ("do it", True),
    ("Go ahead.", True),
    ("ok", True),
    ("sure, thanks", True),
    ("أيوه", True),
    ("نعم", True),
    ("تمام", True),
    ("نفذ", True),
    ("آه", True),
    ("موافق", True),
    ("أيوه تمام", True),
    ("نفّذ", True),
    ("yesterday", False),
    ("not sure", False),
    ("No.", False),
    ("لا", False),
    ("maybe", False),
    ("I didn't say yes", False),
    ("I said yes yesterday", False),
    ("yes but wait", False),
    ("yes, cancel it", False),
    ("do not do it", False),
    ("yes turn it off", False),
    ("أيوه بس استنى", False),
    ("", False),
    (None, False),
])
def test_is_yes(answer, expected):
    loaded, _ = load_main(["x"])
    assert loaded.is_yes(answer) is expected


def test_wake_word_and_command_in_same_phrase():
    said, sub = run_flow(["Hi Echo, make it louder"])

    assert sub.call_args[0][0] == [
        "pactl",
        "set-sink-volume",
        "@DEFAULT_SINK@",
        "+10%",
    ]
    assert said == ["Volume increased"]


def test_wake_word_alone_activates_session():
    said, sub = run_flow(
        ["Hi Echo", "make it louder"],
        max_commands=1,
    )

    assert sub.call_args[0][0] == [
        "pactl",
        "set-sink-volume",
        "@DEFAULT_SINK@",
        "+10%",
    ]
    assert said == ["Volume increased"]


def test_commands_inside_session_do_not_need_wake_word():
    loaded, said = load_main([
        "Hi Echo",
        "make it louder",
        "make it louder",
    ])

    with mock.patch("subprocess.run") as sub:
        sub.return_value = mock.Mock(stdout="", stderr="")
        loaded.main(max_commands=2, max_listens=3)

    assert sub.call_count == 2
    assert said == ["Volume increased", "Volume increased"]


def test_command_without_wake_word_is_ignored():
    said, sub = run_flow(["make it louder"])

    sub.assert_not_called()
    assert said == []


def test_session_ends_after_inactivity():
    loaded, said = load_main([
        "Hi Echo",
        "make it louder",
        "",
        "make it louder",
    ])

    with mock.patch("subprocess.run") as sub:
        sub.return_value = mock.Mock(stdout="", stderr="")
        loaded.main(max_commands=2, max_listens=4)

    # The command after the timeout must not execute without a new wake word.
    assert sub.call_count == 1
    assert said == ["Volume increased"]


def test_unknown_command_gets_a_clear_message():
    said, sub = run_flow(["Hi Echo, tell me a joke about cats"])

    assert said == ["Sorry, I didn't understand that."]
    sub.assert_not_called()


def test_wifi_off_runs_only_after_a_clear_yes():
    said, sub = run_flow(["Hi Echo, turn off wifi", "Yes."])

    assert sub.call_args[0][0] == [
        "nmcli",
        "radio",
        "wifi",
        "off",
    ]
    assert said[-1] == "Wi-Fi turned off"


@pytest.mark.parametrize("answer", [
    "no",
    "No, cancel",
    "yesterday",
    "I am not sure",
    "maybe",
    "I didn't say yes",
    "",
    "لا",
    "بلاش",
])
def test_wifi_off_is_cancelled_without_a_clear_yes(answer):
    said, sub = run_flow(["Hi Echo, turn off wifi", answer])

    sub.assert_not_called()
    assert said[-1] == "Cancelled."


def test_bluetooth_off_also_needs_confirmation():
    said, sub = run_flow(["Hi Echo, turn off bluetooth", "yeah"])

    assert sub.call_args[0][0] == [
        "rfkill",
        "block",
        "bluetooth",
    ]


def test_nlu_cannot_fake_user_confirmation():
    loaded, said = load_main(["Hi Echo, turn off wifi", "no"])

    fake_intent = {
        "action": "set_wifi",
        "target": "wifi",
        "score": 1.0,
        "params": {
            "state": "off",
            "confirmed": True,
        },
    }
    with mock.patch.object(
        loaded, "understand", return_value=fake_intent
    ):
        with mock.patch("subprocess.run") as sub:
            loaded.main(max_commands=1, max_listens=2)

    sub.assert_not_called()
    assert said[-1] == "Cancelled."


@pytest.mark.parametrize("bad_params", [None, []])
def test_invalid_params_are_rejected(bad_params):
    loaded, said = load_main(["Hi Echo, turn off wifi"])

    fake_intent = {
        "action": "set_wifi",
        "target": "wifi",
        "score": 1.0,
        "params": bad_params,
    }
    with mock.patch.object(
        loaded, "understand", return_value=fake_intent
    ):
        with mock.patch("subprocess.run") as sub:
            loaded.main(max_commands=1, max_listens=1)

    sub.assert_not_called()
    assert said == ["Sorry, I couldn't process that command."]
