
"""Connects all the stages. Owner: Deputy Leader."""

import re

from audio import record
from asr import transcribe
from nlu import understand
from nlu.normalize import normalize
from actions import run
from feedback import speak


# A confirmation counts only when the WHOLE answer is a clear yes.
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
    """Return True only for a clear affirmative answer."""
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


def main():
    print("[EchoOS] Listening... (speak now)")

    text = transcribe(record(5))
    print(f"[heard] {text!r}")

    if not text:
        speak("I didn't hear anything.")
        return

    intent = understand(text)

    if not isinstance(intent, dict):
        speak("Sorry, I couldn't process that command.")
        return

    if intent.get("action") == "unknown":
        speak("Sorry, I didn't understand that.")
        return

    # Validate params before using them.
    if "params" not in intent:
        params = {}
        intent["params"] = params

    elif not isinstance(intent["params"], dict):
        speak("Sorry, I couldn't process that command.")
        return

    else:
        params = intent["params"]

    # Never trust confirmation supplied by the NLU.
    params.pop("confirmed", None)

    result = run(intent)

    if not isinstance(result, dict):
        speak("Sorry, something went wrong while executing the command.")
        return

    if "status" not in result or "message" not in result:
        speak("Sorry, something went wrong while executing the command.")
        return

    if result["status"] == "needs_confirmation":
        speak(result["message"])

        answer = transcribe(record(3))

        if is_yes(answer):
            params["confirmed"] = True
            result = run(intent)

            if (
                not isinstance(result, dict)
                or "status" not in result
                or "message" not in result
            ):
                speak("Sorry, something went wrong while executing the command.")
                return

        else:
            result = {
                "status": "ok",
                "message": "Cancelled.",
            }

    speak(result["message"])


if __name__ == "__main__":
    main()
