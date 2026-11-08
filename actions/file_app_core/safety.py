"""Name, folder and text validation for the apps and files actions."""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from . import config
from .results import ActionError

# --------------------------------------------------------------------------
# Text normalisation (app aliases, folder aliases)
# --------------------------------------------------------------------------
_ARABIC_MARKS = re.compile("[\u064B-\u065F\u0670\u0640]")
_ARABIC_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})


def normalize_key(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).casefold()
    value = _ARABIC_MARKS.sub("", value).translate(_ARABIC_MAP)
    value = re.sub(r"[^\w\s]", " ", value)
    return " ".join(value.split())


def match_key(name: str) -> str:
    """Compare names the way nlu/normalize.py rewrote them (lower case, folded Arabic letters)."""
    value = unicodedata.normalize("NFKC", name).casefold()
    value = _ARABIC_MARKS.sub("", value).translate(_ARABIC_MAP)
    return " ".join(value.split())


# --------------------------------------------------------------------------
# Names
# --------------------------------------------------------------------------
def validate_name(value: object, what: str = "name") -> str:
    """Return a safe single path component or raise ActionError."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ActionError(f"Please tell me the {what}.", "missing_parameter")
    if not isinstance(value, str):
        raise ActionError(f"That is not a valid {what}.", "invalid_name")
    name = value.strip()
    if (
        name in {".", ".."}
        or "/" in name
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in name)
    ):
        raise ActionError(f"That is not a valid {what}.", "invalid_name")
    if len(name.encode("utf-8", errors="surrogateescape")) > config.MAX_NAME_BYTES:
        raise ActionError(f"That {what} is too long.", "invalid_name")
    return name


# --------------------------------------------------------------------------
# Folders: names the NLU emits (nlu/catalog.py FOLDERS) -> real folders
# --------------------------------------------------------------------------
_FOLDERS = {
    # key: (XDG variable, default folder name, aliases)
    "documents": ("XDG_DOCUMENTS_DIR", "Documents", ("documents", "docs", "my documents", "المستندات", "مستندات")),
    "downloads": ("XDG_DOWNLOAD_DIR", "Downloads", ("downloads", "download", "التنزيلات", "التحميلات", "تنزيلات", "تحميلات")),
    "desktop": ("XDG_DESKTOP_DIR", "Desktop", ("desktop", "سطح المكتب")),
    "pictures": ("XDG_PICTURES_DIR", "Pictures", ("pictures", "photos", "الصور")),
}
_XDG_LINE = re.compile(r'^(XDG_[A-Z]+_DIR)="(.*)"\s*$')


def _xdg_dirs() -> dict[str, Path]:
    cfg_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    result: dict[str, Path] = {}
    try:
        text = (Path(cfg_home) / "user-dirs.dirs").read_text(encoding="utf-8")
    except OSError:
        return result
    for line in text.splitlines():
        match = _XDG_LINE.match(line.strip())
        if match:
            result[match.group(1)] = Path(match.group(2).replace("$HOME", str(Path.home())))
    return result


def folder_path(key: str) -> Path:
    """Real path of a known folder key ('documents', ...), honouring XDG settings."""
    xdg_var, default_name, _ = _FOLDERS[key]
    return _xdg_dirs().get(xdg_var) or Path.home() / default_name


def _alias_to_key(text: str) -> str | None:
    wanted = normalize_key(text)
    for key, (_, _, aliases) in _FOLDERS.items():
        if wanted in {normalize_key(a) for a in aliases}:
            return key
    return None


def allowed_roots(write: bool) -> list[Path]:
    """Folders actions may use: write=True for changes, False for read-only access."""
    override = config.roots_override(write)
    if override:
        return [Path(p).expanduser().resolve() for p in override]
    keys = config.WRITE_FOLDERS if write else config.READ_FOLDERS
    roots = []
    for key in keys:
        path = folder_path(key)
        if path.is_dir():
            roots.append(path.resolve())
    return roots


def default_directory() -> Path:
    return folder_path(config.DEFAULT_FOLDER)


def _ensure_within(path: Path, write: bool) -> None:
    for root in allowed_roots(write):
        if path == root or root in path.parents:
            return
    where = "Documents and Downloads" if write else "your Documents, Downloads, Desktop and Pictures"
    raise ActionError(f"I can only use {where}.", "outside_safe_folders")


def resolve_directory(value: object = None, write: bool = False) -> Path:
    """Turn a folder reference into a validated, resolved existing directory.

    None/empty -> Documents. "downloads" / "التنزيلات" -> that folder.
    "documents/projects" -> a sub-folder. Other relative paths are relative to
    Documents (never the process working directory). The resolved path (symlinks
    followed) must lie inside a safe folder.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        path = default_directory()
    elif isinstance(value, (str, os.PathLike)):
        text = os.fspath(value)
        if "\x00" in text:
            raise ActionError("That is not a valid folder.", "invalid_parameter")
        candidate = Path(text.strip()).expanduser()
        if candidate.is_absolute():
            path = candidate
        else:
            head, *rest = text.strip().split("/")
            key = _alias_to_key(head)
            path = folder_path(key).joinpath(*rest) if key else default_directory() / candidate
    else:
        raise ActionError("That is not a valid folder.", "invalid_parameter")

    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError):
        raise ActionError("I could not resolve that folder.", "invalid_parameter") from None
    _ensure_within(resolved, write)
    if not resolved.exists():
        raise ActionError("That folder does not exist.", "not_found")
    if not resolved.is_dir():
        raise ActionError("That is not a folder.", "not_a_directory")
    return resolved


def guard_mutation(parent: Path, name: str) -> None:
    """Refuse to create/rename/delete protected entries or anything inside them."""
    home = Path.home().resolve()
    candidate = parent / name
    for entry in config.PROTECTED_HOME_ENTRIES:
        protected = home / entry
        if candidate == protected or protected in candidate.parents:
            raise ActionError("That item is protected.", "protected")


def label_for(path: Path) -> str:
    return path.name or str(path)
