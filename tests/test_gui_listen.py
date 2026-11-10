"""The GUI microphone route must follow the same rules as the voice loop."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("flask")
pytest.importorskip("rapidfuzz")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gui"))

import app as gui  # noqa: E402

HOST = "http://localhost:5050"


class FakeProcessor:
    def __init__(self):
        self.pending = False
        self.commands = []

    def handle(self, text):
        self.commands.append(text)
        return {"status": "ok", "message": "ran " + text}

    def has_pending(self):
        return self.pending

    def cancel(self):
        self.pending = False


@pytest.fixture
def client(monkeypatch):
    heard = []
    monkeypatch.setattr(gui, "PROCESSOR", FakeProcessor())
    monkeypatch.setattr(gui, "CORE_AVAILABLE", True)
    monkeypatch.setattr(gui, "AUDIO_AVAILABLE", True)
    monkeypatch.setattr(gui, "listen_once", lambda **kwargs: heard.pop(0))
    test_client = gui.app.test_client()
    test_client.heard = heard
    return test_client


def listen(client, mode, text):
    client.heard.append(text)
    return client.post("/api/listen", json={"mode": mode}, base_url=HOST).json


def test_standby_ignores_silence_and_speech_without_the_wake_word(client):
    assert listen(client, "standby", "")["status"] == "standby_idle"
    assert listen(client, "standby", "what a nice day")["status"] == "standby_idle"
    assert gui.PROCESSOR.commands == []


def test_wake_word_alone_starts_a_session(client):
    reply = listen(client, "standby", "Hi Echo")

    assert reply["status"] == "ok"
    assert gui.PROCESSOR.commands == []


def test_command_after_the_wake_word_runs_without_it(client):
    listen(client, "standby", "Hi Echo, show system info")

    assert gui.PROCESSOR.commands == ["show system info"]


def test_session_runs_commands_and_silence_ends_it(client):
    assert listen(client, "session", "turn up the volume")["status"] == "ok"
    assert listen(client, "session", "")["status"] == "session_end"


def test_silence_while_waiting_for_a_yes_cancels(client):
    gui.PROCESSOR.pending = True

    reply = listen(client, "session", "")

    assert reply["status"] == "rejected"
    assert not gui.PROCESSOR.pending


def test_other_hosts_are_refused(client):
    assert client.get("/status", base_url="http://evil.example.com").status_code == 403
    assert client.get("/status", base_url=HOST).status_code == 200
