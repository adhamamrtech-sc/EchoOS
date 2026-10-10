"""Text normalization shared by every other NLU module."""

import re


DIACRITICS_AND_TATWEEL = re.compile(r"[\u064B-\u0652\u0640]")

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

ARABIC_LETTER_FIXES = str.maketrans({
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ى": "ي",
    "ة": "ه",
})

FILLERS = [
    "please",
    "can you",
    "could you",
    "ممكن",
    "عايز",
    "عاوز",
    "من فضلك",
    "لو سمحت",
]


def normalize(text: str) -> str:
    """
    Clean and normalize text coming from STT.

    The function:
    - lowercases English
    - removes Arabic diacritics and tatweel
    - converts Arabic digits to English digits
    - normalizes common Arabic letters
    - keeps dots for filenames
    - keeps '-' for negative numbers
    - removes duplicated consecutive words
    """
    if not isinstance(text, str):
        return ""

    text = text.lower().strip()

    if not text:
        return ""

    text = DIACRITICS_AND_TATWEEL.sub("", text)
    text = text.translate(ARABIC_DIGITS)
    text = text.translate(ARABIC_LETTER_FIXES)

    # Keep "." for filenames and "-" for numbers.
    text = re.sub(r"[^\w\s.\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    tokens = []

    for token in text.split():
        if "." not in token:
            token = token.strip(".")

        if token and token.strip("-"):
            tokens.append(token)

    return " ".join(remove_repeated_words(tokens))


def remove_repeated_words(tokens: list[str]) -> list[str]:
    """Collapse consecutive duplicate words."""
    result = []

    for token in tokens:
        if not result or result[-1] != token:
            result.append(token)

    return result


def contains_phrase(text: str, phrases: list[str]) -> bool:
    """Return True if one of the phrases appears as a complete phrase."""
    for phrase in phrases:
        phrase = normalize(phrase)

        if not phrase:
            continue

        pattern = rf"(?<![\w.]){re.escape(phrase)}(?![\w.])"

        if re.search(pattern, text):
            return True

    return False


def starts_with_phrase(text: str, phrase: str) -> bool:
    return text == phrase or text.startswith(phrase + " ")


FILLER_WORDS = sorted(
    (normalize(filler) for filler in FILLERS),
    key=len,
    reverse=True,
)


def strip_fillers(text: str) -> str:
    """Remove polite filler phrases from the start and end of a sentence."""
    changed = True

    while changed:
        changed = False

        for filler in FILLER_WORDS:
            if starts_with_phrase(text, filler) and text != filler:
                text = text[len(filler):].strip()
                changed = True
            elif text.endswith(" " + filler):
                text = text[: -len(filler)].strip()
                changed = True

    return text
