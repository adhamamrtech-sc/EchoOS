"""get_system_info reports real usage, not just the kernel name."""
import pytest

pytest.importorskip("psutil")

import actions


def test_all_metrics_by_default():
    result = actions.run({"action": "get_system_info", "params": {}})
    assert result["status"] == "ok"
    for word in ("CPU", "RAM", "Disk"):
        assert word in result["message"]


def test_only_the_asked_metric():
    result = actions.run({"action": "get_system_info", "params": {"metrics": ["ram"]}})
    assert result["status"] == "ok"
    assert "RAM" in result["message"]
    assert "CPU" not in result["message"]
