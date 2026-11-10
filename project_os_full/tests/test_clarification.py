
from nlu.llm_engine import DecisionEngine


class ClarificationProvider:

    def __init__(self):
        self.calls = []

    def generate(self, input_data):
        self.calls.append(input_data)

        # First request:
        # User says "open my browser"
        # The LLM asks which browser.
        if len(self.calls) == 1:
            return {
                "status": "needs_clarification",
                "message": "Which browser do you want to open?",
            }

        # Follow-up:
        # User answers "Firefox"
        return {
            "status": "accepted",
            "action": "open_app",
            "target": "firefox",
            "params": {},
            "confidence": 0.97,
        }


def test_clarification_flow():

    provider = ClarificationProvider()

    engine = DecisionEngine(
        llm_provider=provider,
        fallback_provider=None,
        threshold=0.90,
    )

    # -----------------------------------------
    # First request
    # -----------------------------------------

    text = "open my browser"

    candidate = {
        "text": text,
        "action": "open_app",
        "target": "unknown",
        "params": {},
        "score": 0.40,
    }

    result = engine.decide(
        candidate,
        text=text,
    )

    # The system should ask for clarification.
    assert result["status"] == "needs_clarification"

    assert result["message"] == (
        "Which browser do you want to open?"
    )

    # Context should remember that
    # the system is waiting for the user's answer.
    assert engine.context_manager.has_pending() is True

    # -----------------------------------------
    # Follow-up answer
    # -----------------------------------------

    follow_up_text = "Firefox"

    follow_up = {
        "text": follow_up_text,
        "action": None,
        "target": None,
        "params": {},
        "score": 0.10,
    }

    result = engine.decide(
        follow_up,
        text=follow_up_text,
    )

    # The clarification should now be resolved.
    assert result["status"] == "accepted"

    assert result["action"] == "open_app"

    assert result["target"] == "firefox"

    # Context should be cleared after successful resolution.
    assert engine.context_manager.has_pending() is False

    # The provider should have been called twice:
    # 1. Original request
    # 2. Follow-up answer
    assert len(provider.calls) == 2

