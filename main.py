from nlu import understand
from nlu.llm_engine import DecisionEngine
from nlu.gemini_provider import GeminiProvider
from actions import run
from feedback import speak


def listen_for_confirmation():
    """Record and transcribe one confirmation response."""
    from audio import record
    from asr import transcribe
    audio = record(5)
    return transcribe(audio)


def _run_action(action_runner, decision):
    """Execute an action safely and normalize unexpected results."""
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
    confirmation_listener=listen_for_confirmation,
):
    """Process one user command through NLU and Decision Engine."""

    # Stage 1: Understand the user's command.
    candidate = understand(text)

    # Stage 2: Make a validated decision.
    decision = engine.decide(candidate, text=text)

    if not isinstance(decision, dict):
        return {
            "status": "failed",
            "reason": "invalid_decision",
        }

    status = decision.get("status")

    # Stage 3: Execute accepted commands.
    if status == "accepted":

        params = decision.get("params")

        if not isinstance(params, dict):
            params = {}
            decision["params"] = params

        # Never trust confirmation supplied by NLU or the LLM.
        params.pop("confirmed", None)

        result = _run_action(action_runner, decision)

        # Stage 4: Handle confirmation requested by the action layer.
        if result.get("status") == "needs_confirmation":

            speaker(
                result.get(
                    "message",
                    "Please confirm this operation.",
                )
            )

            answer = confirmation_listener()

            if engine._confirmation_decision(answer) is True:

                # Only an explicit spoken YES authorizes confirmation.
                params["confirmed"] = True

                result = _run_action(action_runner, decision)

                # Do not allow repeated confirmation loops.
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

    # Stage 5: Handle Decision Engine confirmation or clarification.
    if status in {"needs_confirmation", "needs_clarification"}:
        speaker(
            decision.get(
                "message",
                "Please repeat your request.",
            )
        )
        return decision

    # Stage 6: Handle rejected or failed decisions.
    if status in {"rejected", "failed"}:
        speaker("I couldn't process your request.")
        return decision

    return {
        "status": "failed",
        "reason": "unknown_decision_status",
    }


def main():
    from audio import record
    from asr import transcribe

    engine = DecisionEngine(
        llm_provider=GeminiProvider()
    )

    while True:
        audio = record(5)
        text = transcribe(audio)

        if not text:
            continue

        result = process_text(text, engine)

        # Continue listening when the Decision Engine needs an answer.
        if result.get("status") not in {
            "needs_confirmation",
            "needs_clarification",
        }:
            break


if __name__ == "__main__":
    main()
