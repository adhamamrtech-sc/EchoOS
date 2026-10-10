"""Entity and parameter extraction."""

import re

from .catalog import APPS, FOLDERS
from .normalize import normalize


FILE_PATTERN = re.compile(
    r"(?<![\w.])"
    r"[\w\-]+\."
    r"(?:txt|pdf|docx?|xlsx?|pptx?|csv|png|jpe?g|mp3|mp4|zip|py)"
    r"(?![\w.])",
    re.IGNORECASE,
)

NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d+(?![\w.])")

TARGET_FILLERS = {
    "the",
    "app",
    "ال",
    "برنامج",
    "تطبيق",
}


def build_alias_table(mapping: dict) -> list[tuple[str, str]]:
    pairs = [
        (normalize(alias), name)
        for name, aliases in mapping.items()
        for alias in aliases
    ]

    return sorted(pairs, key=lambda pair: len(pair[0]), reverse=True)


APP_ALIASES = build_alias_table(APPS)
FOLDER_ALIASES = build_alias_table(FOLDERS)
APP_NAMES = {
    normalize(alias): app
    for app, names in APPS.items()
    for alias in names
}


def find_names(text: str, alias_table: list[tuple[str, str]]) -> list[str]:
    """Find known names in order of appearance."""
    remaining = f" {text} "
    found = []

    for alias, name in alias_table:
        if not alias:
            continue

        pattern = re.compile(rf"(?<![\w.]){re.escape(alias)}(?![\w.])")

        for match in pattern.finditer(remaining):
            found.append((match.start(), name))

        remaining = pattern.sub(
            lambda match: " " * len(match.group()),
            remaining,
        )

    names = []

    for _, name in sorted(found):
        if name not in names:
            names.append(name)

    return names


def find_app(name: str):
    """
    Convert an app mention into a canonical name.

    Unknown names are preserved so actions can decide what to do.
    """
    words = [
        word
        for word in name.split()
        if word not in TARGET_FILLERS
    ]
    name = " ".join(words).strip()

    if not name:
        return None

    if name in APP_NAMES:
        return APP_NAMES[name]

    if name.startswith("ال"):
        without_al = name[2:]
        if without_al in APP_NAMES:
            return APP_NAMES[without_al]

    from rapidfuzz import fuzz

    closest = max(APP_NAMES, key=lambda alias: fuzz.ratio(name, alias))
    similarity = fuzz.ratio(name, closest)
    # "chorme" → chrome is ~83; keep unknown names like "banana" unmatched.
    limit = 80 if len(name) >= 5 else 90

    if similarity >= limit:
        return APP_NAMES[closest]

    return name


def extract_entities(text: str) -> dict:
    """Extract known entities from normalized text."""
    entities = {}

    apps = find_names(text, APP_ALIASES)

    if len(apps) == 1:
        entities["app"] = apps[0]
    elif len(apps) > 1:
        entities["apps"] = apps

    folders = find_names(text, FOLDER_ALIASES)

    if folders:
        entities["folder"] = folders[0]

    filename = FILE_PATTERN.search(text)

    if filename:
        entities["filename"] = filename.group()

    number = NUMBER_PATTERN.search(text)

    if number:
        entities["number"] = int(number.group())

    return entities


def extract_params(command, entities: dict, rest: str = "") -> dict:
    """Extract parameters required by the command."""
    if command.needs == "number":
        if "number" in entities:
            return {"value": entities["number"]}
        return {}

    if command.needs == "filename":
        if "filename" in entities:
            return {"filename": entities["filename"]}
        return {}

    if command.action == "list_files" and "folder" in entities:
        return {"folder": entities["folder"]}

    if command.needs == "folder" and rest and "folder" not in entities:
        return {}

    return {}


def resolve_target(command, entities: dict, rest: str = ""):
    """Resolve the user-visible target field."""
    if command.needs == "app":
        if "app" in entities:
            return entities["app"]
        if rest:
            return find_app(rest)
        return None

    if command.needs == "folder":
        if "folder" in entities:
            return entities["folder"]
        return rest or None

    return command.target


def validate_params(command, params: dict, target=None) -> str:
    """
    Validate parameters using the command's needs field.

    Returns a status string: ok, missing_target, missing_number,
    invalid_number, or missing_filename.
    """
    if command.needs == "app" and not target:
        return "missing_target"

    if command.needs == "folder" and not target:
        return "missing_target"

    if command.needs == "number":
        if "value" not in params:
            return "missing_number"

        value = params["value"]

        if command.action == "set_volume" and not (0 <= value <= 100):
            return "invalid_number"

        return "ok"

    if command.needs == "filename":
        return "ok" if params.get("filename") else "missing_filename"

    return "ok"
