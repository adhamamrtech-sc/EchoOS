YES_WORDS = ("yes", "yeah", "yep", "sure", "ok", "okay", "confirm",
             "نعم", "ايوه", "أيوه", "اه", "تمام", "اكيد")


def main():
    text = transcribe(record(5))
    intent = understand(text)
    result = run(intent)

    if result["status"] == "needs_confirmation":
        speak(result["message"])
        answer = transcribe(record(3)).lower()

        if any(word in answer for word in YES_WORDS):
            intent["params"]["confirmed"] = True
            result = run(intent)
        else:
            result = {"status": "ok", "message": "Cancelled."}

    speak(result["message"])