
"""Connects all the stages. Owner: Deputy Leader."""

import re

from audio import listen_once, strip_wake_word
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


def _valid_result(result):
    """Check that an action returned the expected result structure."""
    return (
        isinstance(result, dict)
        and "status" in result
        and "message" in result
    )


def _process_command(text, listen_for_confirmation):
    """Understand and execute one command."""
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

    if not _valid_result(result):
        speak("Sorry, something went wrong while executing the command.")
        return

    if result["status"] == "needs_confirmation":
        speak(result["message"])

        answer = listen_for_confirmation()

        if answer is not None and is_yes(answer):
            params["confirmed"] = True
            result = run(intent)

            if not _valid_result(result):
                speak("Sorry, something went wrong while executing the command.")
                return

        else:
            result = {
                "status": "ok",
                "message": "Cancelled.",
            }

    speak(result["message"])


def main(max_commands=None, max_listens=None):
    """Run EchoOS with a session activated by the 'Hi Echo' wake word.

    Commands inside an active session do not need the wake word again.
    The session ends after 30 seconds without detected speech.

    max_commands and max_listens are optional limits for automated tests.
    """

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

        # Handle "Hi Echo, make it louder" immediately.
        if command:
            _process_command(command, listen_for_confirmation)
            command_count += 1

            if max_commands is not None and command_count >= max_commands:
                return

        # Active session: commands no longer need the wake word.
        while True:
            if max_commands is not None and command_count >= max_commands:
                return

            text = listen(start_timeout=30)

            if text is None:
                return

            # No speech within 30 seconds: close the session.
            if not text:
                print("[EchoOS] Session ended. Waiting for wake word...")
                break

            _process_command(text, listen_for_confirmation)
            command_count += 1


if __name__ == "__main__":
    main()
