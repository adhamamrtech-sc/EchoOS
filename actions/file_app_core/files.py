"""File and folder operations.

* Every change goes through an open directory file descriptor (dir_fd) of the
  validated parent folder, so a swapped-in symlink cannot redirect it.
* Create is atomic and never overwrites (O_EXCL / mkdir).
* Rename uses renameat2(RENAME_NOREPLACE) when available; otherwise a
  check-then-rename fallback leaves a tiny race window (documented limit).
* Delete is two-step (see confirmation.py) and removes only regular files or the
  symlink itself, never a folder and never a symlink's target.
"""
from __future__ import annotations

import ctypes
import errno
import functools
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from . import config, confirmation
from .results import ActionError, Result, guarded, needs_confirmation, ok
from .safety import (
    allowed_roots,
    guard_mutation,
    label_for,
    match_key,
    resolve_directory,
    validate_name,
)


@contextmanager
def _open_dir(path: Path) -> Iterator[int]:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        yield fd
    finally:
        os.close(fd)


def _lstat(fd: int, name: str) -> os.stat_result:
    return os.stat(name, dir_fd=fd, follow_symlinks=False)


def _identity(st: os.stat_result) -> tuple[int, int, int, int, int]:
    return (st.st_mode, st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)


@functools.lru_cache(maxsize=1)
def _renameat2() -> Any:
    try:
        func = ctypes.CDLL(None, use_errno=True).renameat2
    except (OSError, AttributeError):
        return None
    func.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    func.restype = ctypes.c_int
    return func


def _rename_noreplace(fd: int, old: str, new: str) -> None:
    func = _renameat2()
    if func is not None:
        if func(fd, os.fsencode(old), fd, os.fsencode(new), 1) == 0:  # RENAME_NOREPLACE
            return
        err = ctypes.get_errno()
        if err not in (errno.ENOSYS, errno.EINVAL, errno.ENOTSUP):
            raise OSError(err, os.strerror(err), new)
    try:
        _lstat(fd, new)
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), new)
    os.rename(old, new, src_dir_fd=fd, dst_dir_fd=fd)


def _find_entry(parent: Path, name: str) -> str | None:
    """Actual name of an existing entry, or None.

    The NLU lower-cases speech and folds Arabic letters ("Report.PDF" arrives as
    "report.pdf"), so if the exact name is missing we accept ONE entry whose
    normalised name is equal. Several equal candidates are refused, not guessed.
    """
    try:
        os.lstat(parent / name)
        return name
    except OSError:
        pass
    wanted = match_key(name)
    try:
        candidates = [e.name for e in os.scandir(parent) if match_key(e.name) == wanted]
    except OSError:
        return None
    if len(candidates) > 1:
        raise ActionError(f"Several items in {label_for(parent)} look like {name}.", "ambiguous")
    return candidates[0] if candidates else None


def _locate_existing(directory: object, name: str) -> tuple[Path, str]:
    """Folder and real name of an existing item.

    The NLU does not say which folder a file is in ("delete report.pdf"), so when no
    folder is given we look in each writable safe folder (Documents, Downloads).
    Exactly one match is used; zero or several are reported instead of guessing.
    """
    if directory not in (None, ""):
        parent = resolve_directory(directory, write=True)
        actual = _find_entry(parent, name)
        if actual is None:
            raise ActionError(f"I could not find {name} in {label_for(parent)}.", "not_found")
        return parent, actual
    matches = []
    for root in allowed_roots(write=True):
        actual = _find_entry(root, name)
        if actual is not None:
            matches.append((root, actual))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ActionError(f"I could not find {name} in Documents or Downloads.", "not_found")
    names = " and ".join(label_for(root) for root, _ in matches)
    raise ActionError(f"{name} exists in {names}. Please say which folder.", "ambiguous")


@guarded
def list_files(directory: object = None, show_hidden: bool = False) -> Result:
    """List a folder (Documents by default). Hidden entries are skipped."""
    parent = resolve_directory(directory, write=False)
    entries: list[dict[str, str]] = []
    with os.scandir(parent) as it:
        for entry in it:
            if not show_hidden and entry.name.startswith("."):
                continue
            try:
                if entry.is_symlink():
                    kind = "link"
                elif entry.is_dir(follow_symlinks=False):
                    kind = "folder"
                else:
                    kind = "file"
            except OSError:
                kind = "file"
            entries.append({"name": entry.name, "type": kind})
    entries.sort(key=lambda e: e["name"].casefold())

    label = label_for(parent)
    if not entries:
        return ok(f"{label} is empty.", items=[], path=str(parent))
    shown = [e["name"] for e in entries[: config.MAX_SPOKEN_ITEMS]]
    extra = len(entries) - len(shown)
    noun = "item" if len(entries) == 1 else "items"
    message = f"{label} has {len(entries)} {noun}: " + ", ".join(shown)
    if extra > 0:
        message += f" and {extra} more"
    return ok(message + ".", items=entries, path=str(parent))


@guarded
def create_file(directory: object, name: object) -> Result:
    """Create an empty file (Documents by default); never overwrites."""
    parent = resolve_directory(directory, write=True)
    name = validate_name(name, "file name")
    guard_mutation(parent, name)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    with _open_dir(parent) as fd:
        try:
            os.close(os.open(name, flags, 0o644, dir_fd=fd))
        except FileExistsError:
            raise ActionError(f"{name} already exists.", "already_exists") from None
    return ok(f"Created file {name} in {label_for(parent)}.", path=str(parent / name))


@guarded
def create_folder(directory: object, name: object) -> Result:
    """Create one folder (Documents by default); never overwrites."""
    parent = resolve_directory(directory, write=True)
    name = validate_name(name, "folder name")
    guard_mutation(parent, name)
    with _open_dir(parent) as fd:
        try:
            os.mkdir(name, 0o755, dir_fd=fd)
        except FileExistsError:
            raise ActionError(f"{name} already exists.", "already_exists") from None
    return ok(f"Created folder {name} in {label_for(parent)}.", path=str(parent / name))


@guarded
def rename_item(directory: object, old_name: object, new_name: object) -> Result:
    """Rename inside one folder; never replaces an existing entry."""
    old = validate_name(old_name, "current name")
    new = validate_name(new_name, "new name")
    if old == new:
        raise ActionError("The new name is the same as the old one.", "invalid_name")
    parent, old = _locate_existing(directory, old)
    if old == new:
        raise ActionError("The new name is the same as the old one.", "invalid_name")
    guard_mutation(parent, old)
    guard_mutation(parent, new)
    with _open_dir(parent) as fd:
        try:
            _lstat(fd, old)
        except FileNotFoundError:
            raise ActionError(f"{old} does not exist.", "not_found") from None
        try:
            _rename_noreplace(fd, old, new)
        except FileExistsError:
            raise ActionError(f"{new} already exists.", "already_exists") from None
        try:
            _lstat(fd, new)
        except FileNotFoundError:
            raise ActionError("The rename did not complete.", "os_error") from None
    return ok(f"Renamed {old} to {new}.", path=str(parent / new))


@guarded
def delete_file(directory: object, name: object, confirmed: bool = False) -> Result:
    """Delete a file, only after a confirmed second call.

    First call (or any call the module cannot match to a pending request):
    nothing is deleted and ``needs_confirmation`` is returned. main.py then runs
    the same intent again with confirmed=True, which deletes only if this exact
    file was just asked about and is unchanged.
    """
    name = validate_name(name, "file name")
    parent, name = _locate_existing(directory, name)
    guard_mutation(parent, name)
    key = (str(parent), name)

    with _open_dir(parent) as fd:
        try:
            st = _lstat(fd, name)
        except FileNotFoundError:
            raise ActionError(f"I could not find {name}.", "not_found") from None
        if stat.S_ISDIR(st.st_mode):
            raise ActionError(f"{name} is a folder. I can only delete files.", "is_directory")
        if not (stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)):
            raise ActionError(f"{name} is not a regular file.", "unsupported_type")

        if confirmed is True:
            remembered = confirmation.take(key)
            if remembered is not None:
                if remembered != _identity(st):
                    raise ActionError(
                        f"{name} changed since you asked. Nothing was deleted.", "changed"
                    )
                os.unlink(name, dir_fd=fd)
                try:
                    _lstat(fd, name)
                except FileNotFoundError:
                    return ok(f"Deleted {name}.", path=str(parent / name))
                raise ActionError(f"I could not delete {name}.", "os_error")
            # confirmed=True but nothing pending: fall through and ask properly.

        confirmation.request(key, _identity(st))

    return needs_confirmation(
        f"Delete {name} from {label_for(parent)}? Say yes to confirm.",
        target=name,
        path=str(parent / name),
    )
