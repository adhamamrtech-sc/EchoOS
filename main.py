"""Connects all EchoOS stages. Owner: Deputy Leader."""

from audio import listen_once, strip_wake_word
from nlu import understand
from nlu.llm_engine import DecisionEngine
from nlu.gemini_provider import GeminiProvider
from nlu.normalize import normalize, strip_fillers
from actions import run
from feedback import speak


class LazyGeminiProvider:
    """Create Gemini only when an LLM request is needed."""

    def __init__(self):
        self._provider = None

    def generate(self, prompt):
        if self._provider is None:
            self._provider = GeminiProvider()
        return self._provider.generate(prompt)


def is_yes(answer):
    """Accept only clear, standalone confirmation responses."""
    if not isinstance(answer, str):
        return False

    normalized = strip_fillers(normalize(answer))

    accepted_answers = {
        "yes", "yes please", "yes yes",
        "yeah", "yep", "do it", "go ahead",
        "ok", "sure thanks",
        "ايوه", "نعم", "تمام", "نفذ",
        "اه", "موافق", "ايوه تمام", "نفذها",
    }

    return normalized in accepted_answers


def _run_action(action_runner, decision):
    """Execute an action safely."""
    try:
        result = action_runner(decision)

    except NotImplementedError:
        result = {
            "status": "error",
            "message": "Action execution is not implemented yet.",
        }

    except Exception:
        result = {
            "status": "error",
            "message": "An error occurred while executing the command.",
        }

    if not isinstance(result, dict):
        return {
            "status": "error",
            "message": "Invalid action result.",
        }

    return result


def process_text(
    text,
    engine,
    action_runner=run,
    speaker=speak,
    confirmation_listener=None,
):
    """Process one user utterance through the Decision Engine."""

    candidate = understand(text)

    if not isinstance(candidate, dict):
        speaker("Sorry, I couldn't process that command.")
        return {"status": "failed", "reason": "invalid_candidate"}

    if "params" in candidate and not isinstance(candidate["params"], dict):
        speaker("Sorry, I couldn't process that command.")
        return {"status": "failed", "reason": "invalid_params"}

    decision = engine.decide(candidate, text=text)

    if not isinstance(decision, dict):
        return {
            "status": "failed",
            "reason": "invalid_decision",
        }

    status = decision.get("status")

    # Execute an accepted decision.
    if status == "accepted":
        if "params" in decision and not isinstance(decision["params"], dict):
            speaker("Sorry, I couldn't process that command.")
            return {"status": "failed", "reason": "invalid_params"}

        params = decision.setdefault("params", {})

        # Never trust confirmation supplied by NLU or the LLM.
        params.pop("confirmed", None)

        result = _run_action(action_runner, decision)

        # Handle confirmation requested by the action layer.
        if result.get("status") == "needs_confirmation":
            speaker(
                result.get(
                    "message",
                    "Please confirm this operation.",
                )
            )

            answer = (
                confirmation_listener()
                if confirmation_listener is not None
                else None
            )

            if is_yes(answer):
                params["confirmed"] = True
                result = _run_action(action_runner, decision)

                if result.get("status") == "needs_confirmation":
                    result = {
                        "status": "error",
                        "message": "Confirmation could not be completed.",
                    }

            else:
                result = {
                    "status": "rejected",
                    "reason": "user_cancelled",
                    "message": "Cancelled.",
                }

        speaker(
            result.get(
                "message",
                "Command processing finished.",
            )
        )

        return result

    # The engine handles these through its internal context manager.
    if status in {"needs_confirmation", "needs_clarification"}:
        speaker(
            decision.get(
                "message",
                "Please repeat your request.",
            )
        )
        return decision

    if status == "failed" and decision.get("reason") == "llm_unavailable":
        speaker("Sorry, I didn't understand that.")
        return decision

    if status in {"rejected", "failed"}:
        speaker("I couldn't process your request.")
        return decision

    return {
        "status": "failed",
        "reason": "unknown_decision_status",
    }


def main(max_commands=None, max_listens=None):
    """Run EchoOS using Wake Word and Active Session."""

    engine = DecisionEngine(
        llm_provider=LazyGeminiProvider()
    )

    listen_count = 0
    command_count = 0

    def listen(start_timeout):
        nonlocal listen_count

        if max_listens is not None and listen_count >= max_listens:
            return None

        listen_count += 1

        return listen_once(
            require_wake_word=False,
            start_timeout=start_timeout,
        )

    def listen_for_confirmation():
        return listen(start_timeout=3)

    def process_command(text):
        return process_text(
            text,
            engine,
            confirmation_listener=listen_for_confirmation,
        )

    print("[EchoOS] Waiting for 'Hi Echo'...")

    while True:
        # Standby: wait for the wake word.
        text = listen(start_timeout=8)

        if text is None:
            return

        if not text:
            continue

        heard_wake_word, command = strip_wake_word(text)

        if not heard_wake_word:
            continue

        print("[EchoOS] Session activated.")

        # Process the command that came with the wake word.
        if command:
            process_command(command)
            command_count += 1

            if max_commands is not None and command_count >= max_commands:
                return

        # Active session: commands don't need the wake word again.
        while True:
            if max_commands is not None and command_count >= max_commands:
                return

            text = listen(start_timeout=30)

            if text is None:
                return

            # Silence ends the active session.
            if not text:
                print("[EchoOS] Session ended. Waiting for wake word...")
                break

            process_command(text)
            command_count += 1


if __name__ == "__main__":
    main()