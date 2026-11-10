from nlu.llm_engine import DecisionEngine
from nlu.llm_provider import MockLLMProvider

class UnavailableProvider:
    """Simulates Gemini being temporarily unavailable."""

    def generate(self, input_data):
        raise RuntimeError("503 UNAVAILABLE")

def test_fallback_works_when_gemini_fails():
    engine = DecisionEngine(
        llm_provider=UnavailableProvider(),
        fallback_provider=MockLLMProvider(),
        threshold=0.90,
    )

    candidate = {
        "text": "open firefox",
        "action": "open_app",
        "target": "firefox",
        "params": {},
        "score": 0.40,
    }

    result = engine.decide(candidate)

    assert result["status"] == "accepted"
    assert result["action"] == "open_app"
    assert result["target"] == "firefox"
    assert result["candidate_score"] == 0.40
    assert result["llm_confidence"] == 0.95