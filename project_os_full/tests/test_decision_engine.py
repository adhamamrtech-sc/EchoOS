from nlu.llm_engine import DecisionEngine


class FakeProvider:

    def __init__(self, result=None, error=None):

        self.result = result
        self.error = error
        self.called = False

    def generate(self, text):

        self.called = True

        if self.error:
            raise RuntimeError(self.error)

        return self.result


def create_engine(
    primary_result=None,
    primary_error=None,
    fallback_result=None,
    fallback_error=None,
):

    primary = FakeProvider(
        result=primary_result,
        error=primary_error,
    )

    fallback = FakeProvider(
        result=fallback_result,
        error=fallback_error,
    )

    engine = DecisionEngine(
        llm_provider=primary,
        fallback_provider=fallback,
    )

    return engine, primary, fallback


def test_high_score_accepts_without_llm():

    engine, primary, fallback = create_engine()

    candidate = {
        "text": "open firefox",
        "action": "open_app",
        "target": "firefox",
        "score": 0.95,
    }

    result = engine.decide(candidate)

    assert result["status"] == "accepted"
    assert result["action"] == "open_app"
    assert result["target"] == "firefox"

    assert primary.called is False
    assert fallback.called is False


def test_low_score_calls_llm():

    engine, primary, fallback = create_engine(
        primary_result={
            "status": "accepted",
            "action": "open_app",
            "target": "firefox",
            "confidence": 0.95,
        }
    )

    candidate = {
        "text": "launch firefox",
        "action": "open_app",
        "target": "firefox",
        "score": 0.55,
    }

    result = engine.decide(candidate)

    assert primary.called is True
    assert result["status"] == "accepted"
    assert result["action"] == "open_app"
    assert result["target"] == "firefox"


def test_llm_can_request_clarification():

    engine, primary, fallback = create_engine(
        primary_result={
            "status": "needs_clarification",
            "message": "Which browser do you want to open?",
        }
    )

    candidate = {
        "text": "open my browser",
        "action": "open_app",
        "target": "unknown",
        "score": 0.40,
    }

    result = engine.decide(candidate)

    assert primary.called is True
    assert result["status"] == "needs_clarification"
    assert (
        result["message"]
        == "Which browser do you want to open?"
    )


def test_llm_can_reject():

    engine, primary, fallback = create_engine(
        primary_result={
            "status": "rejected",
            "reason": "unsupported_command",
        }
    )

    candidate = {
        "text": "delete all files",
        "action": "open_app",
        "target": None,
        "score": 0.30,
    }

    result = engine.decide(candidate)

    assert result["status"] == "rejected"
    assert result["reason"] == "unsupported_command"


def test_primary_failure_uses_fallback():

    engine, primary, fallback = create_engine(
        primary_error="Primary provider unavailable",

        fallback_result={
            "status": "accepted",
            "action": "open_app",
            "target": "firefox",
            "confidence": 0.90,
        },
    )

    candidate = {
        "text": "open firefox",
        "action": "open_app",
        "target": "firefox",
        "score": 0.50,
    }

    result = engine.decide(candidate)

    assert primary.called is True
    assert fallback.called is True

    assert result["status"] == "accepted"
    assert result["action"] == "open_app"


def test_both_providers_failure():

    engine, primary, fallback = create_engine(
        primary_error="Primary provider unavailable",
        fallback_error="Fallback provider unavailable",
    )

    candidate = {
        "text": "open firefox",
        "action": "open_app",
        "target": "firefox",
        "score": 0.50,
    }

    result = engine.decide(candidate)

    assert result["status"] == "failed"
    assert result["reason"] == "llm_unavailable"


def test_unsupported_action_is_rejected_without_llm():

    engine, primary, fallback = create_engine()

    candidate = {
        "text": "hack computer",
        "action": "hack_computer",
        "target": None,
        "score": 0.99,
    }

    result = engine.decide(candidate)

    assert result["status"] == "rejected"
    assert result["reason"] == "unsupported_action"

    assert primary.called is False
    assert fallback.called is False
def test_clarification_creates_context():

    engine, primary, fallback = create_engine(
        primary_result={
            "status": "needs_clarification",
            "message": "Which browser do you want to open?",
        }
    )

    candidate = {
        "text": "open my browser",
        "action": "open_app",
        "target": "unknown",
        "score": 0.40,
    }

    result = engine.decide(candidate)

    assert result["status"] == "needs_clarification"

    context = engine.context_manager.get_context()

    assert context["pending_action"] == "open_app"

    assert context["pending_target"] == "unknown"

    assert (
        context["last_command"]
        == "open my browser"
    )


def test_accepted_command_clears_context():

    engine, primary, fallback = create_engine(
        primary_result={
            "status": "accepted",
            "action": "open_app",
            "target": "firefox",
            "confidence": 0.95,
        }
    )

    engine.context_manager.set_pending(
        action="open_app",
        target="unknown",
        command="open my browser",
    )

    candidate = {
        "text": "open firefox",
        "action": "open_app",
        "target": "firefox",
        "score": 0.50,
    }

    result = engine.decide(candidate)

    assert result["status"] == "accepted"

    assert engine.context_manager.has_pending() is False
def test_follow_up_resolves_using_context():

    engine, primary, fallback = create_engine()

    # --------------------------------
    # Step 1
    # User asks to open browser
    # --------------------------------

    primary.result = {
        "status": "needs_clarification",
        "message": "Which browser do you want to open?",
    }

    first_candidate = {
        "text": "open my browser",
        "action": "open_app",
        "target": "unknown",
        "score": 0.40,
    }

    first_result = engine.decide(
        first_candidate
    )

    assert (
        first_result["status"]
        == "needs_clarification"
    )

    # Context should now exist

    assert (
        engine.context_manager.has_pending()
        is True
    )


def test_follow_up_with_invalid_candidate_action_uses_context():

    class FollowUpProvider:

        def __init__(self):

            self.calls = []

        def generate(self, input_data):

            self.calls.append(input_data)

            return {
                "status": "accepted",
                "action": "open_app",
                "target": "firefox",
                "confidence": 0.97,
            }

    provider = FollowUpProvider()

    engine = DecisionEngine(
        llm_provider=provider,
        fallback_provider=None,
    )

    # --------------------------------
    # Create pending context
    # --------------------------------

    engine.context_manager.set_pending(
        action="open_app",
        target=None,
        command="open my browser",
    )

    # --------------------------------
    # Simulate weak candidate
    # from Person 1
    # --------------------------------

    candidate = {
        "text": "Firefox",
        "action": None,
        "target": None,
        "score": 0.10,
    }

    result = engine.decide(candidate)

    # --------------------------------
    # Final result
    # --------------------------------

    assert result["status"] == "accepted"

    assert result["action"] == "open_app"

    assert result["target"] == "firefox"

    # --------------------------------
    # Make sure LLM was called
    # --------------------------------

    assert len(provider.calls) == 1

    sent_input = provider.calls[0]

    assert sent_input["current_text"] == "Firefox"

    assert (
        sent_input["context"]["pending_action"]
        == "open_app"
    )
def test_full_clarification_and_follow_up_flow():

    class FollowUpProvider:

        def __init__(self):

            self.calls = []

        def generate(self, input_data):

            self.calls.append(input_data)

            # First request
            if len(self.calls) == 1:

                return {
                    "status": "needs_clarification",
                    "message": (
                        "Which browser do you want to open?"
                    ),
                }

            # Follow-up answer
            return {
                "status": "accepted",
                "action": "open_app",
                "target": "firefox",
                "confidence": 0.97,
            }

    provider = FollowUpProvider()

    engine = DecisionEngine(
        llm_provider=provider,
        fallback_provider=None,
    )

    # --------------------------------
    # Step 1: Original command
    # --------------------------------

    first_candidate = {
        "text": "open my browser",
        "action": "open_app",
        "target": "unknown",
        "score": 0.40,
    }

    first_result = engine.decide(
        first_candidate
    )

    assert (
        first_result["status"]
        == "needs_clarification"
    )

    # Context must now exist

    assert (
        engine.context_manager.has_pending()
        is True
    )

    context = (
        engine.context_manager.get_context()
    )

    assert (
        context["pending_action"]
        == "open_app"
    )

    # --------------------------------
    # Step 2: User answers
    # --------------------------------

    second_candidate = {
        "text": "Firefox",
        "action": None,
        "target": None,
        "score": 0.10,
    }

    second_result = engine.decide(
        second_candidate
    )

    # --------------------------------
    # Final result
    # --------------------------------

    assert (
        second_result["status"]
        == "accepted"
    )

    assert (
        second_result["action"]
        == "open_app"
    )

    assert (
        second_result["target"]
        == "firefox"
    )

    # --------------------------------
    # Context should be cleared
    # --------------------------------

    assert (
        engine.context_manager.has_pending()
        is False
    )

    # --------------------------------
    # LLM must have been called twice
    # --------------------------------

    assert len(provider.calls) == 2

    # First call has no previous context

    assert (
        provider.calls[0]["context"]
        is None
    )

    # Second call contains previous context

    assert (
        provider.calls[1]["context"]
        is not None
    )

    assert (
        provider.calls[1]["context"]
        ["pending_action"]
        == "open_app"
    )   
def test_person1_to_person2_integration():
    """
    Simulates the contract between:
    Person 1 Intent Engine
    and
    Person 2 Decision Engine
    """

    class IntegrationProvider:

        def __init__(self):
            self.calls = []

        def generate(self, input_data):

            self.calls.append(input_data)

            # Low-confidence command:
            # LLM asks for clarification
            if len(self.calls) == 1:

                return {
                    "status": "needs_clarification",
                    "message": (
                        "Which browser do you want to open?"
                    ),
                }

            # Follow-up answer
            return {
                "status": "accepted",
                "action": "open_app",
                "target": "firefox",
                "confidence": 0.97,
            }

    provider = IntegrationProvider()

    engine = DecisionEngine(
        llm_provider=provider,
        fallback_provider=None,
    )

    # ==============================
    # Person 1 → Person 2
    # ==============================

    candidate = {
        "text": "open my browser",
        "action": "open_app",
        "target": "unknown",
        "params": {},
        "score": 0.40,
    }

    result = engine.decide(candidate)

    # Person 2 asks user for clarification
    assert result["status"] == "needs_clarification"

    # Context must now exist
    assert engine.context_manager.has_pending() is True

    # ==============================
    # User answers clarification
    # ==============================

    follow_up = {
        "text": "Firefox",
        "action": None,
        "target": None,
        "params": {},
        "score": 0.10,
    }

    result = engine.decide(follow_up)

    # Final decision
    assert result["status"] == "accepted"

    assert result["action"] == "open_app"

    assert result["target"] == "firefox"

    # Context should be cleared
    assert engine.context_manager.has_pending() is False

    # Gemini/LLM called twice
    assert len(provider.calls) == 2