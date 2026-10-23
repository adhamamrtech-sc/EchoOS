"""Spoken replies. Owner: Interface, Docs and QA Engineer."""
import shutil
import subprocess


def speak(text):
    """Say the text out loud (and always print it)."""
    print(f"[EchoOS] {text}")

    for tool in ("espeak-ng", "espeak"):
        if shutil.which(tool):
            subprocess.run([tool, text], check=False, timeout=15)
            return