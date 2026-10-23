"""NLU and Actions must agree: what NLU outputs, Actions must be able to run."""
import pytest

pytest.importorskip("rapidfuzz")

import actions
from nlu import understand
from nlu.catalog import COMMANDS

# Actions NLU can already output but nobody has implemented yet.
# Remove a name from this set as soon as its handler is in ALLOWED_ACTIONS.
PENDING = {
    "close_app", "open_folder",                        # Dana: actions/apps_files.py
    "create_file", "create_folder", "rename_file",
    "delete_file", "list_files",
    "shutdown", "restart", "exit",                     # unowned, dangerous or special
    "get_time", "screenshot", "show_processes",
}


def test_every_nlu_action_exists_in_actions():
    nlu_actions = {command.action for command in COMMANDS}
    missing = nlu_actions - set(actions.ALLOWED_ACTIONS) - PENDING
    assert not missing, f"NLU outputs actions Actions cannot run: {sorted(missing)}"


def test_pending_list_is_not_stale():
    stale = PENDING & set(actions.ALLOWED_ACTIONS)
    assert not stale, f"Remove from PENDING, already implemented: {sorted(stale)}"


@pytest.mark.parametrize("text, action, params", [
    ("turn off wifi", "set_wifi", {"state": "off"}),
    ("turn on wi-fi", "set_wifi", {"state": "on"}),
    ("please turn off the wifi", "set_wifi", {"state": "off"}),
    ("اقفل الواي فاي", "set_wifi", {"state": "off"}),
    ("شغل الواي فاي", "set_wifi", {"state": "on"}),
    ("turn on bluetooth", "set_bluetooth", {"state": "on"}),
    ("disable bluetooth", "set_bluetooth", {"state": "off"}),
    ("اقفل البلوتوث", "set_bluetooth", {"state": "off"}),
    ("شغل البلوتوث", "set_bluetooth", {"state": "on"}),
    ("make it louder", "volume_up", {}),
    ("ارفع الصوت", "volume_up", {}),
    ("set volume to 40", "set_volume", {"value": 40}),
    ("set brightness to 60", "set_brightness", {"value": 60}),
    ("lock my computer", "lock_screen", {}),
    ("اقفل الشاشه", "lock_screen", {}),
    ("network status", "get_network_status", {}),
    ("system info", "get_system_info", None),
])
def test_phrases_map_to_allowed_actions(text, action, params):
    intent = understand(text)
    assert intent["action"] == action, intent
    assert intent["action"] in actions.ALLOWED_ACTIONS
    if params is not None:
        assert intent["params"] == params


def test_unknown_words_are_not_treated_as_apps():
    assert understand("open the wifi")["action"] == "unknown"


def test_confidence_is_a_number_between_0_and_1():
    intent = understand("turn off wifi")
    assert isinstance(intent["confidence"], float)
    assert 0 <= intent["confidence"] <= 1


def test_open_app_works_end_to_end(monkeypatch=None):
    from unittest import mock
    with mock.patch("shutil.which", return_value="/usr/bin/firefox"), \
         mock.patch("subprocess.Popen") as popen:
        result = actions.run(understand("open firefox"))
    assert result["status"] == "ok"
    assert popen.call_args[0][0] == ["firefox"]
    assert "shell" not in popen.call_args[1]


def test_open_app_rejects_unknown_app():
    result = actions.run({"action": "open_app", "target": "rm -rf", "params": {}})
    assert result["status"] == "error"
