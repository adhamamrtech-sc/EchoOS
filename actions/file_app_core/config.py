"""Settings for the apps and files actions."""
from __future__ import annotations

import os

# Optional overrides (os.pathsep-separated folders), mainly for tests / odd setups.
ENV_READ_ROOTS = "ECHOOS_READ_ROOTS"
ENV_WRITE_ROOTS = "ECHOOS_WRITE_ROOTS"


def roots_override(write: bool) -> list[str] | None:
    raw = os.environ.get(ENV_WRITE_ROOTS if write else ENV_READ_ROOTS, "")
    items = [p for p in raw.split(os.pathsep) if p.strip()]
    return items or None


# SECURITY.md: files may only be touched in Documents and Downloads.
WRITE_FOLDERS = ("documents", "downloads")
# Proposal (needs Team Leader approval): read-only access to the other folders the
# NLU can name, so "list files in desktop" / "open folder pictures" work.
READ_FOLDERS = ("documents", "downloads", "desktop", "pictures")
DEFAULT_FOLDER = "documents"

# main.py asks for the "yes", then records and transcribes again before it re-runs
# the intent, so this must cover speech + recording + recognition time.
CONFIRMATION_TTL_SECONDS = 60.0

MAX_NAME_BYTES = 255
MAX_SPOKEN_ITEMS = 5

LAUNCH_SETTLE_SECONDS = 0.5   # detect an app that crashes immediately
CLOSE_TIMEOUT_SECONDS = 5.0
GTK_LAUNCH_TIMEOUT_SECONDS = 10.0

# Entries (relative to $HOME) that no action may create, rename or delete.
PROTECTED_HOME_ENTRIES = (".ssh", ".gnupg", ".bashrc", ".profile", ".bash_history")
