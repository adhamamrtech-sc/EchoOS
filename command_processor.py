"""Bridge between the GUI and the EchoOS pipeline.

The GUI does not have its own copy of the logic. It calls ``main.process_text``,
the same function the voice loop uses, so both go through the same steps:

    understand -> DecisionEngine (Gemini, optional) -> actions (allowlist) -> reply

The only difference is the confirmation step. The voice loop waits inside
``process_text`` for a spoken "yes". A web page cannot wait inside one request,
so this bridge pauses at that point, tells the page to ask the user, and when
the next message arrives it runs the same command again with the answer.
``main.is_yes`` decides whether the answer is a yes, so voice and GUI accept
exactly the same words.
"""

from __future__ import annotations

import logging
import threading
import time

import main as pipeline

logger = logging.getLogger(__name__)

PENDING_TTL_SECONDS = 60

ERROR_MESSAGE = "Sorry, something went wrong while processing that command."


class _AnswerNeeded(Exception):
    """Raised by the confirmation listener to pause until the user answers."""


def _reply(status, message, **extra):
    return {"status": status, "message": message, **extra}


class CommandProcessor:
    """One user, one conversation. Safe to call from several threads."""

    def __init__(
        self,
        engine=None,
        action_runner=None,
        speaker=None,
        pending_ttl=PENDING_TTL_SECONDS,
        clock=time.monotonic,
    ):
        self._engine = engine
        self._action_runner = action_runner or pipeline.run
        self._speaker = speaker
        self._pending_ttl = pending_ttl
        self._clock = clock
        self._lock = threading.RLock()
        self._pending = None  # (original_text, expires_at)

    # ── public ──────────────────────────────────────────────────────────────
    def handle(self, text):
        """Process one message from the user and return a GUI reply dict."""
        text = (text or "").strip() if isinstance(text, str) else ""

        if not text:
            return _reply("error", "No command provided.")

        with self._lock:
            pending = self._take_pending()

            if pending is not None:
                return self._answer_pending(pending, text)

            return self._run(text, answer=None)

    def has_pending(self):
        with self._lock:
            return self._take_pending(peek=True) is not None

    def cancel(self):
        with self._lock:
            self._pending = None

    # ── internals ───────────────────────────────────────────────────────────
    def _take_pending(self, peek=False):
        if self._pending is None:
            return None

        original_text, expires_at = self._pending

        if self._clock() > expires_at:
            self._pending = None
            return None

        if not peek:
            self._pending = None

        return original_text

    def _get_engine(self):
        if self._engine is None:
            from nlu.llm_engine import DecisionEngine

            self._engine = DecisionEngine(
                llm_provider=pipeline.LazyGeminiProvider()
            )

        return self._engine

    def _answer_pending(self, original_text, answer):
        if not pipeline.is_yes(answer):
            self._forget_action_confirmation()
            return _reply("rejected", "Cancelled.")

        # Same command again; this time the listener returns the user's answer.
        return self._run(original_text, answer=answer)

    @staticmethod
    def _forget_action_confirmation():
        """Drop the action layer's remembered "are you sure" request."""
        try:
            from actions.file_app_core import confirmation

            confirmation.clear()
        except Exception:  # pragma: no cover - best effort
            logger.debug("Could not clear action confirmation", exc_info=True)

    def _run(self, text, answer):
        spoken = []

        def speaker(message):
            spoken.append(message)

            if self._speaker is not None:
                try:
                    self._speaker(message)
                except Exception:  # pragma: no cover - audio is optional
                    logger.debug("Speaker failed", exc_info=True)

        def listener():
            if answer is None:
                raise _AnswerNeeded()

            return answer

        try:
            result = pipeline.process_text(
                text,
                self._get_engine(),
                action_runner=self._action_runner,
                speaker=speaker,
                confirmation_listener=listener,
            )

        except _AnswerNeeded:
            self._pending = (text, self._clock() + self._pending_ttl)
            message = spoken[-1] if spoken else "Please confirm. Say yes or no."
            return _reply("needs_confirmation", message)

        except Exception:
            logger.exception("Command failed")
            return _reply("error", ERROR_MESSAGE)

        return self._shape(result, spoken)

    @staticmethod
    def _shape(result, spoken):
        """Turn the pipeline result into the small dict the web page expects."""
        if not isinstance(result, dict):
            return _reply("error", ERROR_MESSAGE)

        status = result.get("status")
        message = result.get("message") or (spoken[-1] if spoken else "")

        if status == "failed" and result.get("reason") == "llm_unavailable":
            return _reply("unknown", message or "Sorry, I didn't understand that.")

        if status == "failed":
            return _reply("error", message or "I couldn't process your request.")

        if status == "rejected" and result.get("reason") != "user_cancelled":
            return _reply("error", message or "I couldn't process your request.")

        return _reply(status or "ok", message or "Done.")
