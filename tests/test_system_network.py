
"""Unit tests for system and network actions."""

import subprocess
from unittest.mock import patch

import pytest

import actions.system_network as system_network


def successful_result(stdout=""):
    return subprocess.CompletedProcess([], 0, stdout, "")


# ------------------- PERCENT VALIDATION -------------------

@pytest.mark.parametrize("value", [0, 40, 100, "40", " 75 "])
def test_valid_volume_values(value):
    with patch.object(
        system_network.subprocess,
        "run",
        return_value=successful_result(),
    ) as mock_run:
        result = system_network.set_volume({
            "params": {"value": value}
        })

    assert result["status"] == "ok"
    assert mock_run.called


@pytest.mark.parametrize(
    "value",
    [-1, 101, 40.8, True, False, None, "abc", "", "40.5"],
)
def test_invalid_volume_values(value):
    with patch.object(system_network.subprocess, "run") as mock_run:
        result = system_network.set_volume({
            "params": {"value": value}
        })

    assert result["status"] == "error"
    mock_run.assert_not_called()


def test_invalid_brightness_value():
    with patch.object(system_network.subprocess, "run") as mock_run:
        result = system_network.set_brightness({
            "params": {"value": 150}
        })

    assert result["status"] == "error"
    mock_run.assert_not_called()


# ------------------- COMMAND EXECUTION -------------------

def test_set_volume_runs_correct_command():
    with patch.object(
        system_network.subprocess,
        "run",
        return_value=successful_result(),
    ) as mock_run:
        result = system_network.set_volume({
            "params": {"value": 40}
        })

    assert result["status"] == "ok"
    assert mock_run.call_args.args[0] == [
        "pactl",
        "set-sink-volume",
        "@DEFAULT_SINK@",
        "40%",
    ]
    assert mock_run.call_args.kwargs["timeout"] == 10
    assert mock_run.call_args.kwargs["check"] is True


@pytest.mark.parametrize(
    "exception",
    [
        FileNotFoundError(),
        PermissionError(),
        subprocess.TimeoutExpired("pactl", 10),
        subprocess.CalledProcessError(1, "pactl", stderr="internal error"),
        OSError("system error"),
    ],
)
def test_command_errors_are_handled(exception):
    with patch.object(
        system_network.subprocess,
        "run",
        side_effect=exception,
    ):
        result = system_network.volume_up({})

    assert result["status"] == "error"
    assert isinstance(result["message"], str)
    assert result["message"]


def test_command_error_does_not_expose_stderr():
    error = subprocess.CalledProcessError(
        1,
        "pactl",
        stderr="sensitive internal details",
    )

    with patch.object(
        system_network.subprocess,
        "run",
        side_effect=error,
    ):
        result = system_network.volume_up({})

    assert result["status"] == "error"
    assert "sensitive internal details" not in result["message"]


# ------------------- WI-FI -------------------

def test_wifi_off_requires_confirmation():
    with patch.object(system_network.subprocess, "run") as mock_run:
        result = system_network.set_wifi({
            "params": {"state": "off"}
        })

    assert result["status"] == "needs_confirmation"
    mock_run.assert_not_called()


def test_wifi_off_after_confirmation():
    with patch.object(
        system_network.subprocess,
        "run",
        return_value=successful_result(),
    ) as mock_run:
        result = system_network.set_wifi({
            "params": {"state": "off", "confirmed": True}
        })

    assert result["status"] == "ok"
    assert mock_run.call_args.args[0] == [
        "nmcli", "radio", "wifi", "off"
    ]


def test_wifi_on_does_not_require_confirmation():
    with patch.object(
        system_network.subprocess,
        "run",
        return_value=successful_result(),
    ) as mock_run:
        result = system_network.set_wifi({
            "params": {"state": "on"}
        })

    assert result["status"] == "ok"
    assert mock_run.call_args.args[0] == [
        "nmcli", "radio", "wifi", "on"
    ]


def test_invalid_wifi_state_is_rejected():
    with patch.object(system_network.subprocess, "run") as mock_run:
        result = system_network.set_wifi({
            "params": {"state": "disabled"}
        })

    assert result["status"] == "error"
    mock_run.assert_not_called()


# ------------------- BLUETOOTH -------------------

def test_bluetooth_off_requires_confirmation():
    with patch.object(system_network.subprocess, "run") as mock_run:
        result = system_network.set_bluetooth({
            "params": {"state": "off"}
        })

    assert result["status"] == "needs_confirmation"
    mock_run.assert_not_called()


def test_bluetooth_off_after_confirmation():
    with patch.object(
        system_network.subprocess,
        "run",
        return_value=successful_result(),
    ) as mock_run:
        result = system_network.set_bluetooth({
            "params": {"state": "off", "confirmed": True}
        })

    assert result["status"] == "ok"
    assert mock_run.call_args.args[0] == [
        "rfkill", "block", "bluetooth"
    ]


def test_bluetooth_on_does_not_require_confirmation():
    with patch.object(
        system_network.subprocess,
        "run",
        return_value=successful_result(),
    ) as mock_run:
        result = system_network.set_bluetooth({
            "params": {"state": "on"}
        })

    assert result["status"] == "ok"
    assert mock_run.call_args.args[0] == [
        "rfkill", "unblock", "bluetooth"
    ]


# ------------------- SYSTEM INFO INPUT VALIDATION -------------------

@pytest.mark.parametrize(
    "metrics",
    [
        "cpu",
        123,
        [],
        ["unknown"],
        ["cpu", 123],
    ],
)
def test_invalid_metrics_are_rejected(metrics):
    with patch.dict("sys.modules", {"psutil": None}):
        result = system_network.get_system_info({
            "params": {"metrics": metrics}
        })

    assert result["status"] == "error"


def test_invalid_params_do_not_crash():
    result = system_network.set_volume({
        "params": None
    })

    assert result["status"] == "error"
