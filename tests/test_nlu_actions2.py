"""Confirmation flow: risky actions ask first, then run once confirmed."""
from unittest import mock

import pytest

pytest.importorskip("rapidfuzz")

import actions
from nlu import understand


def test_wifi_off_needs_confirmation_then_runs():
    intent = understand("turn off wifi")
    assert actions.run(intent)["status"] == "needs_confirmation"

    intent["params"]["confirmed"] = True

    with mock.patch("subprocess.run") as run:
        run.return_value = mock.Mock(stdout="", stderr="")
        assert actions.run(intent)["status"] == "ok"
        assert run.call_args[0][0] == ["nmcli", "radio", "wifi", "off"]
        