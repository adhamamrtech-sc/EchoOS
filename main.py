"""Connects all the stages. Owner: Deputy Leader."""
import re

from audio import record
from asr import transcribe
from nlu import understand
from nlu.normalize import normalize
from actions import run
from feedback import speak

# Whole words only (compared after normalize), never parts of other words:
# "yesterday" must not count as "yes".
YES_WORDS = {
    normalize(word)
    for word in (
        "yes", "yeah", "yep", "sure", "ok", "okay", "confirm", "do it",
        "نعم", "ايوه", "أيوه", "اه", "تمام", "اكيد", "نفذ",
    )
}
NO_WORDS = {
    normalize(word)
    for word in (
        "no", "nope", "not", "don", "never", "cancel", "stop",
        "لا", "الغي", "الغاء", "وقف", "بلاش",
    )
}


def is_yes(answer):
    """True only for a clear yes. Anything unclear or negative is a no."""
    # \w+ drops punctuation: Whisper writes "Yes." with a full stop.
    words = re.findall(r"\w+", normalize(answer or ""))

    if any(word in NO_WORDS for word in words):
        return False

    return any(word in YES_WORDS for word in words)


def main():
    print("[EchoOS] Listening... (speak now)")
    text = transcribe(record(5))
    print(f"[heard] {text!r}")

    if not text:
        speak("I didn't hear anything.")
        return

    intent = understand(text)

    if intent["action"] == "unknown":
        speak("Sorry, I didn't understand that.")
        return

    result = run(intent)

    if result["status"] == "needs_confirmation":
        speak(result["message"])

        if is_yes(transcribe(record(3))):
            intent["params"]["confirmed"] = True
            result = run(intent)
        else:
            result = {"status": "ok", "message": "Cancelled."}

    speak(result["message"])


if __name__ == "__main__":
    main()