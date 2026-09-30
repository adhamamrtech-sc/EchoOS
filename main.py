"""Connects all the stages. Owner: Deputy Leader."""
from audio import record
from asr import transcribe
from nlu import understand
from actions import run
from feedback import speak


def main():
    audio = record(5)
    text = transcribe(audio)
    intent = understand(text)
    result = run(intent)
    speak(result["message"])


if __name__ == "__main__":
    main()
