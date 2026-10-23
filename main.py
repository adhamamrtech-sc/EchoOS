"""Connects all the stages. Owner: Deputy Leader."""
import re

from audio import record
from asr import transcribe
from nlu import understand
from nlu.normalize import normalize
from actions import run
from feedback import speak

# A confirmation counts only when the WHOLE answer is a clear yes
# (after normalize). "yesterday", "I didn't say yes", "yes but wait" and
# anything unclear all cancel the action.
YES_WORDS = {
    normalize(word)
    for word in (
        "yes", "yeah", "yep", "sure", "ok", "okay", "confirm",
        "نعم", "ايوه", "أيوه", "اه", "تمام", "اكيد", "نفذ",
    )
}
YES_FILLERS = {
    normalize(word)
    for word in (
        "please", "thanks", "thank", "you", "do", "it", "go", "ahead",
        "من", "فضلك", "لو", "سمحت", "ياريت",
    )
}
YES_PHRASES = {"do it", "go ahead", "go for it"}


def is_yes(answer):
    """True only for a clear yes. Anything else is a no."""
    # \w+ drops punctuation: Whisper writes "Yes." with a full stop.
    words = re.findall(r"\w+", normalize(answer or ""))

    if not words:
        return False

    if " ".join(words) in YES_PHRASES:
        return True

    has_yes = any(word in YES_WORDS for word in words)
    only_yes_words = all(word in YES_WORDS | YES_FILLERS for word in words)

    return has_yes and only_yes_words


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