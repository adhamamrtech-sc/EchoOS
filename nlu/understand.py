"""Public NLU entry point."""

from .catalog import Command
from .entities import (
    extract_entities,
    extract_params,
    resolve_target,
    validate_params,
)
from .fuzzy import generate_candidates
from .normalize import normalize, strip_fillers
from .ranking import (
    FUZZY_CONFIDENT,
    MEDIUM_THRESHOLD,
    confidence_label,
    rank_candidates,
)
from .rules import is_verb_only, match_rule
from .semantic import semantic_search


def understand(text: str) -> dict:
    """
    Convert user text into a structured intent.

    Public API:
        understand(text)
    """
    normalized_text = strip_fillers(normalize(text))

    if not normalized_text or len(normalized_text) > 300:
        return unknown_result()

    entities = extract_entities(normalized_text)

    # Never guess when multiple applications are mentioned.
    if "apps" in entities:
        return unknown_result(status="ambiguous")

    command_match = match_rule(normalized_text, entities)

    if command_match:
        command, rest, score = command_match
        result = build_result(command, entities, score, rest)

        if result["action"] != "unknown":
            return result

        # Intent was recognized but required parameters are missing.
        return result

    if is_verb_only(normalized_text):
        return unknown_result(status="missing_target")

    return understand_with_fallback(normalized_text, entities)


def understand_with_fallback(text: str, entities: dict) -> dict:
    """
    Fallback pipeline:

        RapidFuzz
            ↓
        confident?
          yes → result
          no
            ↓
        Semantic Search
            ↓
        Ranking
            ↓
        Result
    """
    candidates = generate_candidates(text)

    if not candidates:
        return unknown_result()

    best_command, best_fuzzy_score = candidates[0]

    if best_fuzzy_score >= FUZZY_CONFIDENT:
        return build_result(best_command, entities, best_fuzzy_score)

    semantic_scores = semantic_search(text)

    if not semantic_scores:
        if best_fuzzy_score < MEDIUM_THRESHOLD:
            return unknown_result(best_fuzzy_score)

        return build_result(best_command, entities, best_fuzzy_score)

    ranked = rank_candidates(text, candidates, semantic_scores)

    if not ranked:
        return unknown_result()

    best_command, final_score = ranked[0]

    if final_score < MEDIUM_THRESHOLD:
        return unknown_result(final_score)

    return build_result(best_command, entities, final_score)


def build_result(
    command: Command,
    entities: dict,
    score: float,
    rest: str = "",
) -> dict:
    """Build the stable output consumed by the rest of EchoOS."""
    target = resolve_target(command, entities, rest)
    params = extract_params(command, entities, rest)
    status = validate_params(command, params, target)

    if status != "ok":
        return unknown_result(score, status)

    return {
        "action": command.action,
        "target": target,
        "params": params,
        "score": round(score, 2),
        "confidence": confidence_label(score),
        "status": status,
    }


def unknown_result(score: float = 0.0, status: str = "unknown") -> dict:
    """Return the stable unknown-intent result."""
    return {
        "action": "unknown",
        "target": None,
        "params": {},
        "score": round(score, 2),
        "confidence": "low",
        "status": status,
    }
