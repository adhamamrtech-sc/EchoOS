"""RapidFuzz candidate generation."""

from rapidfuzz import fuzz, process

from .catalog import EXAMPLE_OWNERS, EXAMPLE_TEXTS, Command


def generate_candidates(text: str, top_n: int = 5) -> list[tuple[Command, float]]:
    """
    Return the best fuzzy candidates.

    Dangerous commands are never included in EXAMPLE_TEXTS.
    """
    if not text or not EXAMPLE_TEXTS:
        return []

    matches = process.extract(
        text,
        EXAMPLE_TEXTS,
        scorer=fuzz.token_sort_ratio,
        limit=40,
    )

    best_per_command = {}

    for _example, score, index in matches:
        command = EXAMPLE_OWNERS[index]

        if command.dangerous:
            continue

        if command.key not in best_per_command:
            best_per_command[command.key] = (command, score / 100.0)

    candidates = list(best_per_command.values())
    candidates.sort(key=lambda item: item[1], reverse=True)

    return candidates[:top_n]
