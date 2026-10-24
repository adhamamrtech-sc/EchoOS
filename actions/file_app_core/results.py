"""Result helpers. The agreed format (INTERFACES.md) is {"status", "message"}.

Extra keys ("data", "error_code") are optional and ignored by main.py.
"""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable

logger = logging.getLogger("echoos.apps_files")

Result = dict[str, Any]


class ActionError(Exception):
    """A user-facing failure with a stable machine-readable code."""

    def __init__(self, message: str, code: str = "error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def ok(message: str, **data: Any) -> Result:
    return {"status": "ok", "message": message, "data": data}


def error(message: str, code: str = "error", **data: Any) -> Result:
    return {"status": "error", "message": message, "error_code": code, "data": data}


def needs_confirmation(message: str, **data: Any) -> Result:
    return {"status": "needs_confirmation", "message": message, "data": data}


def guarded(func: Callable[..., Result]) -> Callable[..., Result]:
    """Turn any exception into an error result (and never leak internal details)."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Result:
        try:
            return func(*args, **kwargs)
        except ActionError as exc:
            return error(exc.message, exc.code)
        except PermissionError:
            return error("Permission denied.", "permission_denied")
        except FileNotFoundError:
            return error("That item does not exist.", "not_found")
        except FileExistsError:
            return error("That name already exists.", "already_exists")
        except OSError as exc:
            logger.warning("OS error in %s: %s", func.__name__, exc)
            return error(f"The operation failed: {exc.strerror or 'system error'}.", "os_error")
        except Exception:  # noqa: BLE001 - last line of defence
            logger.exception("Unexpected error in %s", func.__name__)
            return error("Something went wrong while running that command.", "internal_error")

    return wrapper
