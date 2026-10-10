"""Candidate ranking and confidence scoring."""

from .catalog import Command
from .normalize import contains_phrase


FUZZY_WEIGHT = 0.45
SEMANTIC_WEIGHT = 0.55

FUZZY_CONFIDENT = 0.90

HIGH_THRESHOLD = 0.80
MEDIUM_THRESHOLD = 0.55


def keyword_score(text: str, command: Command) -> float:
    """Return 1.0 when a command keyword is found."""
    return 1.0 if contains_phrase(text, command.keywords) else 0.0


def rank_candidates(
    text: str,
    fuzzy_candidates: list[tuple[Command, float]],
    semantic_scores: dict[str, float],
) -> list[tuple[Command, float]]:
    """Combine fuzzy and semantic evidence for generated candidates only."""
    ranked = []

    for command, fuzzy_score in fuzzy_candidates:
        semantic_score = semantic_scores.get(command.key, 0.0)
        keyword_bonus = keyword_score(text, command)
        final_score = (
            fuzzy_score * FUZZY_WEIGHT
            + semantic_score * SEMANTIC_WEIGHT
        )

        if keyword_bonus:
            final_score = min(final_score + 0.05, 1.0)

        ranked.append((command, final_score))

    return sorted(ranked, key=lambda item: item[1], reverse=True)


def confidence_label(score: float) -> str:
    """Convert score to a readable confidence label."""
    if score >= HIGH_THRESHOLD:
        return "high"

    if score >= MEDIUM_THRESHOLD:
        return "medium"

    return "low"
