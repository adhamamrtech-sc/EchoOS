import os

from nlu import gemini_provider
from nlu.gemini_provider import GeminiProvider


def test_prompt_without_context():

    provider = object.__new__(
        GeminiProvider
    )

    input_data = {
        "current_text": "open firefox",
        "context": None,
    }

    prompt = provider._build_prompt(
        input_data
    )

    assert "open firefox" in prompt

    assert (
        "There is no previous conversation context"
        in prompt
    )


def test_prompt_with_context():

    provider = object.__new__(
        GeminiProvider
    )

    input_data = {
        "current_text": "Firefox",
        "context": {
            "pending_action": "open_app",
            "pending_target": None,
            "last_command": "open my browser",
        },
    }

    prompt = provider._build_prompt(
        input_data
    )

    assert "Firefox" in prompt

    assert "open_app" in prompt

    assert "open my browser" in prompt

    assert "Previous Context" in prompt


def test_json_parser_accepts_fenced_json_and_rejects_non_objects():
    parsed = GeminiProvider._parse_json(
        '```json\n{"status":"rejected","reason":"unsupported_command"}\n```'
    )

    assert parsed["status"] == "rejected"

    try:
        GeminiProvider._parse_json("[]")
    except ValueError as error:
        assert "JSON object" in str(error)
    else:
        raise AssertionError("Expected a non-object JSON response to be rejected")


def test_retry_options_are_bounded_when_supported():
    retry_options = GeminiProvider._build_retry_options()

    if retry_options is not None:
        assert retry_options.attempts == 3
        assert 504 in retry_options.http_status_codes


def test_default_model_is_responsive_flash_variant():
    assert gemini_provider.DEFAULT_MODEL == "gemini-3.6-flash"


def test_environment_model_override_is_preserved(monkeypatch):
    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "models/custom-model")
    monkeypatch.setattr(gemini_provider.genai, "Client", FakeClient)

    provider = GeminiProvider()

    assert provider.model == "custom-model"
    assert provider.timeout_seconds > 0
