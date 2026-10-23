"""INTERFACES.md must list every command the NLU or Actions know."""
from pathlib import Path

import pytest

pytest.importorskip("rapidfuzz")

import actions
from nlu.catalog import COMMANDS


def test_every_action_is_documented():
    text = Path("INTERFACES.md").read_text(encoding="utf-8")
    known = {command.action for command in COMMANDS} | set(actions.ALLOWED_ACTIONS)
    missing = [name for name in sorted(known) if f"`{name}`" not in text]
    assert not missing, f"Add these actions to INTERFACES.md: {missing}"
