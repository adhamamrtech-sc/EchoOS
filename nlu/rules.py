"""Fast deterministic rule-based matching."""

from typing import Optional

from .catalog import (
    CLOSE_VERBS,
    COMMAND_BY_ACTION,
    KEYWORDS,
    OPEN_VERBS,
    Command,
)
from .normalize import contains_phrase, starts_with_phrase


def match_rule(text: str, entities: dict) -> Optional[tuple[Command, str, float]]:
    """
    Return the strongest deterministic command match.

    Result:
        (command, rest, score)
    """
    for keyword, command in KEYWORDS:
        if starts_with_phrase(text, keyword):
            rest = text[len(keyword):].strip()
            return command, rest, 1.0

    for keyword, command in KEYWORDS:
        if command.needs or command.dangerous:
            continue

        if contains_phrase(text, [keyword]):
            return command, "", 0.95

    app = entities.get("app")

    if app:
        if contains_phrase(text, OPEN_VERBS):
            return COMMAND_BY_ACTION["open_app"], "", 0.95

        if contains_phrase(text, CLOSE_VERBS):
            return COMMAND_BY_ACTION["close_app"], "", 0.95

    return None


def is_verb_only(text: str) -> bool:
    """Detect incomplete commands such as 'open' or 'اقفل'."""
    if not text:
        return False

    verbs = set(OPEN_VERBS + CLOSE_VERBS)
    tokens = text.split()

    return bool(tokens) and all(token in verbs for token in tokens)
