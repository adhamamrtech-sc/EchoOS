"""Pending-delete memory that makes main.py's "confirmed" flag trustworthy.

main.py confirms by running the SAME intent again with params["confirmed"] = True.
A bare flag proves nothing (any caller can set it), so a delete only happens if
this module remembers that THIS exact file (folder + name) was asked about a
moment ago and that it has not changed since.

  * one slot only; a new request replaces the old one;
  * expires after config.CONFIRMATION_TTL_SECONDS;
  * single use (consumed even if the delete later fails);
  * bound to the file's identity (type, device, inode, size, mtime).
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

from . import config

_now: Callable[[], float] = time.monotonic  # replaceable in tests
_lock = threading.Lock()
_pending: tuple[Any, Any, float] | None = None  # (key, identity, expires_at)


def request(key: Any, identity: Any) -> None:
    global _pending
    with _lock:
        _pending = (key, identity, _now() + config.CONFIRMATION_TTL_SECONDS)


def take(key: Any) -> Any | None:
    """Return the remembered identity if ``key`` is the live pending request, else None.

    A matching request is consumed (single use). A request for a different key is
    left alone.
    """
    global _pending
    with _lock:
        if _pending is None or _pending[0] != key:
            return None
        _, identity, expires_at = _pending
        _pending = None
        return identity if _now() <= expires_at else None


def clear() -> None:
    global _pending
    with _lock:
        _pending = None


def has_pending() -> bool:
    with _lock:
        return _pending is not None
