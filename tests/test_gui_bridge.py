"""The GUI bridge (command_processor.py) must behave like the voice pipeline."""

import sys
import types

import pytest

pytest.importorskip("rapidfuzz")

from audio import strip_wake_word as real_strip_wake_word


def load_bridge():
    """Import command_processor (and main) with a fake microphone and speaker."""
    fake_audio = types.ModuleType("audio")
    fake_audio.listen_once = lambda **kwargs: ""
    fake_audio.strip_wake_word = real_strip_wake_word

    fake_feedback = types.ModuleType("feedback")
    fake_feedback.speak = lambda text: None

    fakes = {"audio": fake_audio, "feedback": fake_feedback}
    saved = {name: sys.modules.get(name) for name in fakes}
    sys.modules.update(fakes)
    sys.modules.pop("main", None)
    sys.modules.pop("command_processor", None)

    try:
        import command_processor as loaded
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

        sys.modules.pop("main", None)
        sys.modules.pop("command_processor", None)

    return loaded


class FakeEngine:
    """Accepts whatever the NLU found, like the real engine does for clear commands."""

    def decide(self, candidate, text=None):
        return {"status": "accepted", **candidate}


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make_processor(intent, runner_results, clock=None):
    bridge = load_bridge()
    bridge.pipeline.understand = lambda text: {
        "action": intent["action"],
        "params": dict(intent.get("params", {})),
    }

    calls = []
    results = iter(runner_results)

    def runner(decision):
        calls.append({"action": decision["action"], "params": dict(decision["params"])})
        return next(results)

    processor = bridge.CommandProcessor(
        engine=FakeEngine(),
        action_runner=runner,
        pending_ttl=60,
        clock=clock or FakeClock(),
    )
    return processor, calls


DANGEROUS = {"action": "set_wifi", "params": {"state": "off"}}
ASK = {"status": "needs_confirmation", "message": "Turn Wi-Fi off?"}
DONE = {"status": "ok", "message": "Wi-Fi is off."}


def test_plain_command_runs_once_and_returns_the_message():
    processor, calls = make_processor(
        {"action": "get_system_info"},
        [{"status": "ok", "message": "CPU 5%"}],
    )

    reply = processor.handle("show system info")

    assert reply == {"status": "ok", "message": "CPU 5%"}
    assert len(calls) == 1


def test_empty_message_is_an_error():
    processor, calls = make_processor({"action": "get_system_info"}, [])

    assert processor.handle("   ")["status"] == "error"
    assert processor.handle(None)["status"] == "error"
    assert calls == []


def test_risky_command_pauses_and_nothing_is_confirmed_yet():
    processor, calls = make_processor(DANGEROUS, [ASK])

    reply = processor.handle("turn off wifi")

    assert reply == {"status": "needs_confirmation", "message": "Turn Wi-Fi off?"}
    assert processor.has_pending()
    assert len(calls) == 1
    assert "confirmed" not in calls[0]["params"]


def test_yes_confirms_and_runs_the_command():
    processor, calls = make_processor(DANGEROUS, [ASK, ASK, DONE])

    processor.handle("turn off wifi")
    reply = processor.handle("yes")

    assert reply == {"status": "ok", "message": "Wi-Fi is off."}
    assert calls[-1]["params"].get("confirmed") is True
    assert not processor.has_pending()


def test_no_cancels_and_never_confirms():
    processor, calls = make_processor(DANGEROUS, [ASK])

    processor.handle("turn off wifi")
    reply = processor.handle("no")

    assert reply["status"] == "rejected"
    assert reply["message"] == "Cancelled."
    assert len(calls) == 1
    assert all(call["params"].get("confirmed") is not True for call in calls)
    assert not processor.has_pending()


@pytest.mark.parametrize("answer", ["maybe", "yes but not now", "open firefox", "ok do not"])
def test_anything_that_is_not_a_clear_yes_cancels(answer):
    processor, calls = make_processor(DANGEROUS, [ASK])

    processor.handle("turn off wifi")
    reply = processor.handle(answer)

    assert reply["status"] == "rejected"
    assert all(call["params"].get("confirmed") is not True for call in calls)


def test_old_confirmation_expires():
    clock = FakeClock()
    processor, calls = make_processor(DANGEROUS, [ASK, ASK], clock=clock)

    processor.handle("turn off wifi")
    clock.now = 61.0

    assert not processor.has_pending()

    # "yes" is now a fresh command, so it must not confirm the old one.
    processor.handle("yes")
    assert all(call["params"].get("confirmed") is not True for call in calls)


def test_confirmed_flag_from_the_nlu_is_ignored():
    processor, calls = make_processor(
        {"action": "set_wifi", "params": {"state": "off", "confirmed": True}},
        [ASK],
    )

    reply = processor.handle("turn off wifi")

    assert reply["status"] == "needs_confirmation"
    assert "confirmed" not in calls[0]["params"]


def test_a_crash_in_the_pipeline_becomes_an_error_reply():
    bridge = load_bridge()
    bridge.pipeline.understand = lambda text: {"action": "get_system_info", "params": {}}

    class BrokenEngine:
        def decide(self, candidate, text=None):
            raise RuntimeError("boom")

    processor = bridge.CommandProcessor(engine=BrokenEngine(), action_runner=lambda d: {})

    assert processor.handle("show system info")["status"] == "error"


def test_failed_and_unavailable_llm_results_are_mapped_for_the_page():
    bridge = load_bridge()
    shape = bridge.CommandProcessor._shape

    assert shape({"status": "failed", "reason": "llm_unavailable"}, [])["status"] == "unknown"
    assert shape({"status": "failed"}, [])["status"] == "error"
    assert shape({"status": "rejected", "reason": "not_allowed"}, [])["status"] == "error"
    assert shape({"status": "rejected", "reason": "user_cancelled", "message": "Cancelled."}, [])["status"] == "rejected"
    assert shape({"status": "needs_clarification", "message": "Which one?"}, [])["message"] == "Which one?"
    assert shape("nonsense", [])["status"] == "error"
