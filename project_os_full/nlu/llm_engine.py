
"""Decision Engine for EchoOS.

Responsibilities:
- Accept a clear, valid NLU candidate from Person 1.
- Ask an LLM to resolve unclear or incomplete requests.
- Validate every proposed intent before returning it.
- Keep context for clarification and confirmation turns.
- Require explicit confirmation before dangerous actions.

This module does not execute operating-system commands.
"""

from __future__ import annotations

import logging
from math import isfinite
from typing import Any

from nlu.context_builder import ContextBuilder
from nlu.context_manager import ContextManager
from nlu.llm_validator import (
    ALLOWED_ACTIONS,
    DANGEROUS_ACTIONS,
    validate_llm_result,
)
from nlu.normalize import normalize, strip_fillers

logger = logging.getLogger(__name__)

YES_WORDS = {
    "yes", "yeah", "yep", "yes do it", "yes proceed",
    "go ahead", "do it", "confirm", "confirmed", "proceed",
    "نعم", "ايوه", "اه", "موافق", "تمام", "اكيد",
    "نفذ", "نفذها", "ايوه نفذ", "اه نفذ", "تمام نفذ", "اكد",
}

NO_WORDS = {
    "no", "nope", "no cancel", "cancel", "cancel it",
    "do not do it", "لا", "الغاء", "الغي", "بلاش",
    "مش موافق", "مش عايز", "لا تنفذ", "متنفذش", "الغيه",
}

class ProviderOutputError(ValueError):
    """Raised when a provider returns an unusable intent result."""

def safe_score(candidate: dict[str, Any]) -> float:
    """Return a finite score in [0, 1]; treat malformed scores as 0."""
    if not isinstance(candidate, dict):
        return 0.0

    value = candidate.get("score")
    if value is None:
        value = candidate.get("candidate_score", 0.0)

    if isinstance(value, bool):
        return 0.0

    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0

    if not isfinite(value) or not 0.0 <= value <= 1.0:
        return 0.0

    return value

def build_final_result(
    result: dict[str, Any],
    candidate_score: float,
) -> dict[str, Any]:
    """Expose a stable, small output schema to the rest of EchoOS."""
    status = result.get("status")

    if status == "accepted":
        params = result.get("params", {})
        if not isinstance(params, dict):
            return {"status": "failed", "reason": "invalid_params"}

        return {
            "status": "accepted",
            "action": result.get("action"),
            "target": result.get("target"),
            "params": dict(params),
            "candidate_score": candidate_score,
            "llm_confidence": result.get("confidence"),
        }

    if status == "needs_clarification":
        return {
            "status": "needs_clarification",
            "message": result.get(
                "message",
                "Could you clarify what you want me to do?",
            ),
        }

    if status == "rejected":
        return {
            "status": "rejected",
            "reason": result.get("reason", "unsupported_request"),
        }

    if status == "failed":
        return {
            "status": "failed",
            "reason": result.get("reason", "invalid_result"),
        }

    return {
        "status": "failed",
        "reason": "invalid_result_status",
    }

class DecisionEngine:
    """Coordinate NLU candidates, LLM providers, validation, and context."""

    def __init__(
        self,
        llm_provider,
        fallback_provider=None,
        context_manager: ContextManager | None = None,
        threshold: float = 0.90,
    ) -> None:
        if isinstance(threshold, bool):
            raise ValueError("threshold must be a number between 0 and 1")

        try:
            threshold = float(threshold)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                "threshold must be a number between 0 and 1"
            ) from error

        if not isfinite(threshold) or not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be a number between 0 and 1")

        if not callable(getattr(llm_provider, "generate", None)):
            raise TypeError(
                "llm_provider must provide a callable generate() method"
            )

        if fallback_provider is not None and not callable(
            getattr(fallback_provider, "generate", None)
        ):
            raise TypeError(
                "fallback_provider must provide a callable generate() method"
            )

        self.llm_provider = llm_provider
        self.fallback_provider = fallback_provider
        self.context_manager = (
            context_manager
            if context_manager is not None
            else ContextManager()
        )
        self.context_builder = ContextBuilder(self.context_manager)
        self.threshold = threshold

    def decide(
        self,
        candidate: dict[str, Any],
        text: str | None = None,
    ) -> dict[str, Any]:
        """Return a validated decision for one user turn."""
        if not isinstance(candidate, dict):
            return {
                "status": "failed",
                "reason": "invalid_candidate_format",
            }

        current_text = text if isinstance(text, str) else candidate.get("text", "")
        if not isinstance(current_text, str):
            current_text = ""

        candidate_score = safe_score(candidate)

        # Handle missing speech locally; do not call an LLM for empty input.
        if not current_text.strip():
            if self.context_manager.has_pending():
                state = self.context_manager.get_pending_state()

                if state.get("pending_kind") == "confirmation":
                    return {
                        "status": "needs_confirmation",
                        "message": (
                            "I didn't catch that. "
                            "Please say yes to confirm or no to cancel."
                        ),
                    }

                return {
                    "status": "needs_clarification",
                    "message": (
                        "I didn't catch that. "
                        "Please repeat your answer."
                    ),
                }

            return {
                "status": "rejected",
                "reason": "empty_input",
            }

        # A pending interaction takes priority over a new command.
        if self.context_manager.has_pending():
            state = self.context_manager.get_pending_state()

            if state.get("pending_kind") == "confirmation":
                return self._handle_confirmation(current_text)

            return self._resolve_with_llm(
                current_text=current_text,
                candidate=candidate,
                candidate_score=candidate_score,
            )

        action = candidate.get("action")
        nlu_status = candidate.get("status")

        if nlu_status is not None and nlu_status != "ok":
            return self._resolve_with_llm(
                current_text=current_text,
                candidate=candidate,
                candidate_score=candidate_score,
            )

        if action is None or (
            isinstance(action, str) and action == "unknown"
        ):
            return self._resolve_with_llm(
                current_text=current_text,
                candidate=candidate,
                candidate_score=candidate_score,
            )

        if not isinstance(action, str):
            return {
                "status": "rejected",
                "reason": "invalid_candidate_action",
            }

        # Do not ask the LLM to bless an action outside the catalog.
        if action not in ALLOWED_ACTIONS:
            return {
                "status": "rejected",
                "reason": "unsupported_action",
            }

        # Similarity scores are not calibrated probabilities.
        if candidate_score < self.threshold:
            return self._resolve_with_llm(
                current_text=current_text,
                candidate=candidate,
                candidate_score=candidate_score,
            )

        proposed_result = {
            "status": "accepted",
            "action": action,
            "target": candidate.get("target"),
            "params": candidate.get("params", {}),
            "confidence": None,
        }

        validated_result = validate_llm_result(proposed_result)

        return self._finalize_result(
            validated_result=validated_result,
            candidate=candidate,
            candidate_score=candidate_score,
            current_text=current_text,
        )

    def _resolve_with_llm(
        self,
        current_text: str,
        candidate: dict[str, Any],
        candidate_score: float,
    ) -> dict[str, Any]:
        llm_input = self.context_builder.build(
            current_text=current_text,
            candidate=candidate,
        )

        providers = [("primary", self.llm_provider)]
        if self.fallback_provider is not None:
            providers.append(("fallback", self.fallback_provider))

        for provider_name, provider in providers:
            try:
                raw_result = provider.generate(llm_input)
                validated_result = validate_llm_result(raw_result)

                if validated_result.get("status") == "failed":
                    raise ProviderOutputError(
                        validated_result.get(
                            "reason",
                            "invalid_provider_output",
                        )
                    )

            except Exception as error:
                logger.warning(
                    "%s LLM provider failed: %s",
                    provider_name.capitalize(),
                    error,
                )
                continue

            try:
                return self._finalize_result(
                    validated_result=validated_result,
                    candidate=candidate,
                    candidate_score=candidate_score,
                    current_text=current_text,
                )
            except Exception:
                logger.exception("Failed to finalize an LLM decision")
                return {
                    "status": "failed",
                    "reason": "decision_finalization_failed",
                }

        return {
            "status": "failed",
            "reason": "llm_unavailable",
        }

    def _finalize_result(
        self,
        validated_result: dict[str, Any],
        candidate: dict[str, Any],
        candidate_score: float,
        current_text: str,
    ) -> dict[str, Any]:
        status = validated_result.get("status")

        if status == "accepted":
            action = validated_result.get("action")

            if action in DANGEROUS_ACTIONS:
                return self._request_confirmation(
                    result=validated_result,
                    candidate_score=candidate_score,
                    current_text=current_text,
                )

            self.context_manager.clear()
            return build_final_result(validated_result, candidate_score)

        if status == "needs_clarification":
            action = validated_result.get("action") or candidate.get("action")
            if not isinstance(action, str) or action not in ALLOWED_ACTIONS:
                action = None

            target = validated_result.get("target")
            if target is None or target == "" or target == "unknown":
                target = candidate.get("target")

            if not isinstance(target, str):
                target = None
            elif target == "":
                target = None

            candidate_params = candidate.get("params", {})
            model_params = validated_result.get("params", {})

            if not isinstance(candidate_params, dict):
                candidate_params = {}
            if not isinstance(model_params, dict):
                model_params = {}

            pending_params = {**candidate_params, **model_params}

            self.context_manager.set_pending(
                action=action,
                target=target,
                command=current_text,
                params=pending_params,
                kind="clarification",
                score=candidate_score,
            )

            return build_final_result(validated_result, candidate_score)

        if status == "rejected":
            self.context_manager.clear()
            return build_final_result(validated_result, candidate_score)

        # Preserve pending context after a provider/validation failure.
        return build_final_result(validated_result, candidate_score)

    def _request_confirmation(
        self,
        result: dict[str, Any],
        candidate_score: float,
        current_text: str,
    ) -> dict[str, Any]:
        action = result["action"]
        target = result.get("target")
        params = result.get("params", {})

        if not isinstance(params, dict):
            params = {}

        if action == "shutdown":
            message = (
                "Are you sure you want to shut down the computer? "
                "Say yes to confirm or no to cancel."
            )
        elif action == "restart":
            message = (
                "Are you sure you want to restart the computer? "
                "Say yes to confirm or no to cancel."
            )
        elif action == "delete_file":
            filename = params.get("filename", "the requested file")
            message = (
                f"Are you sure you want to delete {filename}? "
                "Say yes to confirm or no to cancel."
            )
        else:
            message = (
                "This operation may affect your system. "
                "Say yes to confirm or no to cancel."
            )

        self.context_manager.set_pending(
            action=action,
            target=target,
            command=current_text,
            params=params,
            kind="confirmation",
            score=candidate_score,
        )

        return {
            "status": "needs_confirmation",
            "message": message,
        }

    def _handle_confirmation(self, current_text: str) -> dict[str, Any]:
        decision = self._confirmation_decision(current_text)

        if decision is None:
            return {
                "status": "needs_confirmation",
                "message": "Please say yes to confirm or no to cancel.",
            }

        state = self.context_manager.get_pending_state()

        if decision is False:
            self.context_manager.clear()
            return {
                "status": "rejected",
                "reason": "user_cancelled",
            }

        proposed_result = {
            "status": "accepted",
            "action": state.get("pending_action"),
            "target": state.get("pending_target"),
            "params": state.get("pending_params", {}),
            "confidence": None,
        }

        validated_result = validate_llm_result(proposed_result)
        candidate_score = safe_score({
            "score": state.get("pending_score", 0.0)
        })

        # Confirmation is single-use, even if validation fails.
        self.context_manager.clear()

        return build_final_result(validated_result, candidate_score)

    @staticmethod
    def _confirmation_decision(text: str) -> bool | None:
        normalized_text = strip_fillers(normalize(text))

        if normalized_text in YES_WORDS:
            return True
        if normalized_text in NO_WORDS:
            return False

        return None

if __name__ == "__main__":
    # Use a mock provider by default so running this module does not
    # unexpectedly make a real API request.
    from nlu.llm_provider import MockLLMProvider

    logging.basicConfig(level=logging.INFO)

    engine = DecisionEngine(
        llm_provider=MockLLMProvider(),
    )

    examples = [
        {
            "text": "open firefox",
            "action": "open_app",
            "target": "firefox",
            "params": {},
            "score": 0.95,
            "status": "ok",
        },
        {
            "text": "open firefox",
            "action": "open_app",
            "target": "firefox",
            "params": {},
            "score": 0.55,
            "status": "ok",
        },
        {
            "text": "hack computer",
            "action": "hack_computer",
            "target": None,
            "params": {},
            "score": 0.95,
            "status": "ok",
        },
    ]

    for example in examples:
        print(engine.decide(example, text=example["text"]))