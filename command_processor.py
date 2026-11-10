"""Shared command processing for EchoOS Voice and GUI."""

import re

from nlu import understand
from nlu.normalize import normalize
from actions import run


YES_WORDS = {
    normalize(word)
    for word in (
        "yes", "yeah", "yep", "sure", "ok", "okay", "confirm",
        "نعم", "أيوه", "ايوه", "أيوة", "أيوه تمام",
        "تمام", "موافق", "أكد", "نفذ", "نفّذ",
        "اه", "آه", "أه",
    )
}

YES_FILLERS = {
    normalize(word)
    for word in (
        "please", "thanks", "thank", "you", "do", "it", "go", "ahead",
        "من فضلك", "لو سمحت", "يا ريت", "من", "فضلك",
    )
}

YES_PHRASES = {"do it", "go ahead", "go for it"}


def is_yes(answer):
    """Accept only a clear affirmative answer."""
    words = re.findall(r"\w+", normalize(answer or ""))

    if not words:
        return False

    if " ".join(words) in YES_PHRASES:
        return True

    has_yes = any(word in YES_WORDS for word in words)
    only_yes_words = all(
        word in YES_WORDS | YES_FILLERS
        for word in words
    )

    return has_yes and only_yes_words


def _valid_result(result):
    return (
        isinstance(result, dict)
        and "status" in result
        and "message" in result
    )


def process_command(
    text,
    understand_fn=None,
    run_fn=None,
):
    """Understand and execute a command, without handling user confirmation."""

    understand_fn = understand_fn or understand
    run_fn = run_fn or run

    try:
        intent = understand_fn(text)
    except Exception:
        return {
            "status": "error",
            "message": "Sorry, I couldn't process that command.",
        }

    if not isinstance(intent, dict):
        return {
            "status": "error",
            "message": "Sorry, I couldn't process that command.",
        }

    if intent.get("action") == "unknown":
        return {
            "status": "unknown",
            "message": "Sorry, I didn't understand that.",
        }

    params = intent.get("params")

    if params is None:
        params = {}
        intent["params"] = params
    elif not isinstance(params, dict):
        return {
            "status": "error",
            "message": "Sorry, I couldn't process that command.",
        }

    # Never trust confirmation supplied by the NLU or caller.
    params.pop("confirmed", None)

    try:
        result = run_fn(intent)
    except Exception:
        return {
            "status": "error",
            "message": "Something went wrong while executing the command.",
        }

    if not _valid_result(result):
        return {
            "status": "error",
            "message": "Something went wrong while executing the command.",
        }

    # Keep the intent server-side for the confirmation step.
    return {
        **result,
        "_pending_intent": intent if result["status"] == "needs_confirmation" else None,
    }


def confirm_command(
    intent,
    answer,
    run_fn=None,
):
    """Confirm or cancel a previously pending command."""

    from actions.file_app_core import confirmation

    run_fn = run_fn or run

    if not isinstance(intent, dict):
        confirmation.clear()
        return {
            "status": "error",
            "message": "Invalid pending confirmation.",
        }

    params = intent.get("params")

    if not isinstance(params, dict):
        confirmation.clear()
        return {
            "status": "error",
            "message": "Invalid pending confirmation.",
        }

    if not is_yes(answer):
        confirmation.clear()
        return {
            "status": "ok",
            "message": "Cancelled.",
        }

    params["confirmed"] = True

    try:
        result = run_fn(intent)
    except Exception:
        return {
            "status": "error",
            "message": "Something went wrong while confirming the command.",
        }

    if not _valid_result(result):
        return {
            "status": "error",
            "message": "Something went wrong while confirming the command.",
        }

    return result
