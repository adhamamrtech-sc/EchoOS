"""Contract tests: check the agreed formats between modules."""
import actions


def test_run_returns_status_and_message():
    result = actions.run({"action": "no_such_action", "params": {}})
    assert result["status"] == "error"
    assert "message" in result


def test_run_rejects_a_missing_action():
    result = actions.run({})
    assert result["status"] == "error"


def test_allowlist_handlers_are_callable():
    for name, handler in actions.ALLOWED_ACTIONS.items():
        assert callable(handler), name


def test_bad_volume_value_is_rejected():
    result = actions.run({"action": "set_volume", "params": {"value": "abc"}})
    assert result["status"] == "error"


def test_brightness_out_of_range_is_rejected():
    result = actions.run({"action": "set_brightness", "params": {"value": 150}})
    assert result["status"] == "error"