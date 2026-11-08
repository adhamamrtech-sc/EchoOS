from nlu.llm_engine import DecisionEngine
from nlu.llm_provider import MockLLMProvider
from nlu.understand import understand


def test_deterministic_nlu_handles_english_and_arabic_app_commands():
    english = understand("open firefox")
    arabic = understand("افتح كروم")

    assert english["action"] == "open_app"
    assert english["target"] == "firefox"
    assert english["status"] == "ok"
    assert english["text"] == "open firefox"
    assert arabic["action"] == "open_app"
    assert arabic["target"] == "chrome"
    assert arabic["status"] == "ok"


def test_deterministic_nlu_extracts_validated_parameters():
    volume = understand("set volume to 50")
    deletion = understand("delete report.pdf")

    assert volume["action"] == "set_volume"
    assert volume["params"] == {"value": 50}
    assert deletion["action"] == "delete_file"
    assert deletion["params"] == {"filename": "report.pdf"}


def test_dangerous_command_requires_confirmation_before_acceptance():
    engine = DecisionEngine(llm_provider=MockLLMProvider())
    candidate = understand("shutdown")

    pending = engine.decide(candidate)
    accepted = engine.decide(
        {"text": "yes", "action": "unknown", "score": 0.0}
    )

    assert pending["status"] == "needs_confirmation"
    assert accepted["status"] == "accepted"
    assert accepted["action"] == "shutdown"
