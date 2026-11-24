"""The Gemini/LLM validator and the Actions layer must agree.

What an LLM may *accept* (nlu.llm_validator.LLM_ALLOWED_ACTIONS) must be exactly what actions.ALLOWED_ACTIONS can run.
Catalog actions that Actions cannot run yet are listed in UNIMPLEMENTED_ACTIONS and are rejected.
"""
import importlib
import sys
import types
from unittest import mock

import pytest

import actions
from nlu import llm_validator as V
from nlu.catalog import APPS, COMMAND_BY_ACTION, FOLDERS
from nlu.llm_engine import DecisionEngine
from nlu.llm_validator import validate_llm_result

# Handlers inside actions.ALLOWED_ACTIONS that are NOT user/LLM actions (they are internal confirmation helpers).
INTERNAL_ACTIONS = {"confirm_wifi_off"}

CATALOG = set(COMMAND_BY_ACTION)
EXECUTABLE = set(actions.ALLOWED_ACTIONS) - INTERNAL_ACTIONS

# Minimal valid accepted result per executable action. A NEW action must get an entry here (the test below fails otherwise).
SAMPLES = {
    "open_app": {"target": next(iter(APPS)), "params": {}},
    "close_app": {"target": next(iter(APPS)), "params": {}},
    "open_folder": {"target": next(iter(FOLDERS)), "params": {}},
    "list_files": {"params": {}},
    "create_file": {"params": {"filename": "a.txt"}},
    "create_folder": {"params": {"name": "docs"}},
    "rename_file": {"params": {"old": "a.txt", "new": "b.txt"}},
    "delete_file": {"params": {"filename": "a.txt"}},
    "set_volume": {"params": {"value": 50}},
    "set_brightness": {"params": {"value": 50}},
    "volume_up": {"params": {}},
    "lock_screen": {"params": {}},
    "get_network_status": {"params": {}},
    "set_wifi": {"params": {"state": "on"}},
    "set_bluetooth": {"params": {"state": "on"}},
    "get_system_info": {"params": {"metrics": ["cpu"]}},
}


def accepted(action, **extra):
    return {"status": "accepted", "action": action, **extra}


# ----------------------------------------------------------------------------- consistency
def test_llm_accepted_actions_equal_executable_actions():
    only_validator = V.LLM_ALLOWED_ACTIONS - EXECUTABLE
    only_actions = EXECUTABLE - V.LLM_ALLOWED_ACTIONS
    assert not only_validator, f"Validator accepts actions that Actions cannot run: {sorted(only_validator)}"
    assert not only_actions, (
        f"Actions can run actions the validator does not accept: {sorted(only_actions)}. "
        "Add them to the NLU catalog, or to INTERNAL_ACTIONS here if they are not user actions.")


def test_unimplemented_set_is_exactly_catalog_minus_actions():
    assert V.UNIMPLEMENTED_ACTIONS == CATALOG - set(actions.ALLOWED_ACTIONS), (
        "UNIMPLEMENTED_ACTIONS is stale: update it when an action is implemented or added to the catalog "
        f"(catalog-not-in-actions = {sorted(CATALOG - set(actions.ALLOWED_ACTIONS))}, "
        f"UNIMPLEMENTED_ACTIONS = {sorted(V.UNIMPLEMENTED_ACTIONS)})")


def test_validator_sets_are_internally_consistent():
    assert V.LLM_ALLOWED_ACTIONS <= V.ALLOWED_ACTIONS == CATALOG
    assert V.LLM_ALLOWED_ACTIONS.isdisjoint(V.UNIMPLEMENTED_ACTIONS)
    assert V.LLM_ALLOWED_ACTIONS | V.UNIMPLEMENTED_ACTIONS == CATALOG


def test_internal_actions_are_real_handlers_and_not_catalog_actions():
    for name in INTERNAL_ACTIONS:
        assert name in actions.ALLOWED_ACTIONS and name not in CATALOG


def test_every_executable_action_has_a_catalog_command():
    assert not (EXECUTABLE - CATALOG), f"Actions without an NLU catalog command: {sorted(EXECUTABLE - CATALOG)}"


# ----------------------------------------------------------------------------- acceptance / rejection
@pytest.mark.parametrize("action", sorted(EXECUTABLE))
def test_every_executable_action_has_a_sample_and_is_accepted(action):
    assert action in SAMPLES, f"Add a minimal valid sample for the new action {action!r} to SAMPLES"
    result = validate_llm_result(accepted(action, **SAMPLES[action]))
    assert result["status"] == "accepted" and result["action"] == action


@pytest.mark.parametrize("action", sorted(V.UNIMPLEMENTED_ACTIONS))
def test_unimplemented_actions_are_rejected(action):
    result = validate_llm_result(accepted(action, params={}))
    assert result == {"status": "rejected", "reason": "unsupported_action"}


@pytest.mark.parametrize("action", ["rm -rf /", "hack", "", "SHUTDOWN", "Open_App", "confirm_wifi_off", None, 5, ["open_app"], {"a": 1}])
def test_unknown_internal_or_malformed_actions_are_rejected(action):
    result = validate_llm_result(accepted(action, params={}))
    assert result == {"status": "rejected", "reason": "unsupported_action"}


def test_parameter_validation_is_not_weakened():
    assert validate_llm_result(accepted("open_app", target="nope", params={}))["reason"] == "invalid_app_target"
    assert validate_llm_result(accepted("open_folder", target="nope", params={}))["reason"] == "invalid_folder_target"
    assert validate_llm_result(accepted("set_volume", params={"value": 101}))["reason"] == "invalid_volume"
    assert validate_llm_result(accepted("set_volume", params={"value": True}))["reason"] == "invalid_volume"
    assert validate_llm_result(accepted("delete_file", params={}))["reason"] == "missing_filename"
    assert validate_llm_result(accepted("list_files", params={"folder": "nope"}))["reason"] == "invalid_folder"
    assert validate_llm_result(accepted("volume_up", params={}, confidence=2))["reason"] == "invalid_confidence"


def test_non_accepted_statuses_are_unchanged():
    assert validate_llm_result({"status": "needs_clarification", "message": "which one?"})["status"] == "needs_clarification"
    assert validate_llm_result({"status": "rejected", "reason": "out of scope"})["status"] == "rejected"
    assert validate_llm_result({"status": "needs_confirmation"})["reason"] == "invalid_status"


# ----------------------------------------------------------------------------- dangerous actions keep their confirmation flow
class StubProvider:
    def __init__(self, result): self.result, self.calls = result, 0
    def generate(self, llm_input): self.calls += 1; return self.result


LOW_SCORE_CANDIDATE = {"action": "unknown", "target": None, "params": {}, "score": 0.1, "status": "unknown"}


def decide_via_llm(result):
    return DecisionEngine(llm_provider=StubProvider(result)).decide(dict(LOW_SCORE_CANDIDATE), text="do it")


def test_dangerous_flags_come_from_the_catalog_and_include_delete():
    assert V.DANGEROUS_ACTIONS == {a for a, c in COMMAND_BY_ACTION.items() if c.dangerous}
    assert "delete_file" in V.DANGEROUS_ACTIONS


def test_executable_dangerous_actions_still_need_engine_confirmation():
    # Loop is empty today (shutdown/restart are unimplemented). It becomes active as soon as one is implemented.
    for action in sorted(V.DANGEROUS_ACTIONS & V.LLM_ALLOWED_ACTIONS - {"delete_file"}):
        decision = decide_via_llm(accepted(action, **SAMPLES.get(action, {"params": {}})))
        assert decision["status"] == "needs_confirmation", action


@pytest.mark.parametrize("action", sorted(V.DANGEROUS_ACTIONS & V.UNIMPLEMENTED_ACTIONS))
def test_unimplemented_dangerous_actions_never_get_through_the_llm(action):
    decision = decide_via_llm(accepted(action, params={}))
    assert decision["status"] not in {"accepted", "needs_confirmation"}


def test_delete_file_from_llm_is_accepted_but_actions_layer_still_asks(monkeypatch):
    decision = decide_via_llm(accepted("delete_file", params={"filename": "report.txt"}))
    assert decision["status"] == "accepted" and decision["action"] == "delete_file"
    calls = []
    monkeypatch.setattr(actions.apps_files.files, "delete_file",
                        lambda directory, name, confirmed=False: calls.append(confirmed) or {"status": "needs_confirmation", "message": "sure?"})
    result = actions.run({"action": "delete_file", "params": dict(decision["params"])})
    assert result["status"] == "needs_confirmation" and calls == [False]


@pytest.mark.parametrize("action", ["set_wifi", "set_bluetooth"])
def test_turning_wifi_or_bluetooth_off_still_needs_confirmation_and_runs_nothing(action):
    decision = decide_via_llm(accepted(action, params={"state": "off"}))
    assert decision["status"] == "accepted"
    with mock.patch("subprocess.run", side_effect=AssertionError("must not run before confirmation")):
        result = actions.run({"action": action, "params": dict(decision["params"])})
    assert result["status"] == "needs_confirmation"


def test_unsupported_action_from_llm_is_not_executable_by_engine():
    decision = decide_via_llm(accepted("screenshot", params={}))
    assert decision["status"] not in {"accepted", "needs_confirmation"}
    assert actions.run({"action": "screenshot", "params": {}})["status"] == "error"


# ----------------------------------------------------------------------------- Gemini prompt offers only what can run
def _import_gemini_provider():
    """nlu.gemini_provider needs google-genai and python-dotenv; stub them only if they are not installed (no network is used)."""
    saved = {k: sys.modules.get(k) for k in ("google", "google.genai", "google.genai.types", "dotenv", "nlu.gemini_provider")}
    try:
        try:
            return importlib.import_module("nlu.gemini_provider"), saved, False
        except ImportError:
            pass
        genai, types_mod = types.ModuleType("google.genai"), types.ModuleType("google.genai.types")
        google = types.ModuleType("google"); google.genai = genai; genai.types = types_mod
        dotenv = types.ModuleType("dotenv"); dotenv.load_dotenv = lambda *a, **k: None
        sys.modules.update({"google": google, "google.genai": genai, "google.genai.types": types_mod, "dotenv": dotenv})
        sys.modules.pop("nlu.gemini_provider", None)
        return importlib.import_module("nlu.gemini_provider"), saved, True
    except Exception:
        _restore(saved); raise


def _restore(saved):
    for k, v in saved.items():
        if v is None: sys.modules.pop(k, None)
        else: sys.modules[k] = v


def test_gemini_prompt_lists_exactly_the_llm_allowed_actions():
    gp, saved, stubbed = _import_gemini_provider()
    try:
        provider = gp.GeminiProvider.__new__(gp.GeminiProvider)
        prompt = provider._build_prompt({"current_text": "x", "candidate": {"action": "unknown"}, "context": None})
    finally:
        if stubbed: _restore(saved)
    import json
    section = prompt.split("ALLOWED ACTIONS:\n", 1)[1]
    specs, _ = json.JSONDecoder().raw_decode(section)
    offered = {s["action"] for s in specs}
    assert offered == set(V.LLM_ALLOWED_ACTIONS), (sorted(offered ^ V.LLM_ALLOWED_ACTIONS))
    assert not offered & V.UNIMPLEMENTED_ACTIONS
