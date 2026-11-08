"""Open and close applications, and open a folder in the file manager.

Keys match nlu/catalog.py APPS (chrome, firefox, vscode, terminal, spotify, vlc,
calculator, files, settings) so whatever the NLU emits can run.

Safety: only allowlisted apps; argv lists only (no shell string); closing matches
EXACT process names of the current user's processes, never this process or its
parents, sends SIGTERM only and never SIGKILL.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config
from .results import ActionError, Result, guarded, ok
from .safety import label_for, normalize_key, resolve_directory


@dataclass(frozen=True)
class AppSpec:
    key: str
    display_name: str
    commands: tuple[tuple[str, ...], ...]  # argv templates, tried in order; {home} is expanded
    desktop_ids: tuple[str, ...]           # gtk-launch fallback
    process_names: frozenset[str]          # exact names used when closing
    aliases: tuple[str, ...]


APPS: tuple[AppSpec, ...] = (
    AppSpec("chrome", "Chrome",
            (("google-chrome",), ("chromium",), ("chromium-browser",)),
            ("google-chrome.desktop", "chromium_chromium.desktop", "chromium-browser.desktop"),
            frozenset({"chrome", "google-chrome", "chromium", "chromium-browser"}),
            ("chrome", "google chrome", "كروم", "الكروم", "جوجل كروم")),
    AppSpec("firefox", "Firefox", (("firefox",),),
            ("firefox.desktop", "firefox_firefox.desktop"),
            frozenset({"firefox", "firefox-bin"}),
            ("firefox", "فايرفوكس", "فاير فوكس", "الفايرفوكس")),
    AppSpec("vscode", "VS Code", (("code",),), ("code.desktop", "code_code.desktop"),
            frozenset({"code"}),
            ("vs code", "vscode", "visual studio code", "في اس كود")),
    AppSpec("terminal", "Terminal", (("gnome-terminal",), ("x-terminal-emulator",)),
            ("org.gnome.Terminal.desktop",),
            frozenset({"gnome-terminal-server", "gnome-terminal-", "gnome-terminal"}),
            ("terminal", "cmd", "تيرمنال", "ترمينال", "الترمينال", "الطرفية")),
    AppSpec("spotify", "Spotify", (("spotify",),), ("spotify.desktop", "spotify_spotify.desktop"),
            frozenset({"spotify"}), ("spotify", "سبوتيفاي")),
    AppSpec("vlc", "VLC", (("vlc",),), ("vlc.desktop", "vlc_vlc.desktop"),
            frozenset({"vlc"}), ("vlc", "في ال سي")),
    AppSpec("calculator", "Calculator", (("gnome-calculator",), ("galculator",)),
            ("org.gnome.Calculator.desktop", "galculator.desktop"),
            frozenset({"gnome-calculator", "gnome-calculato", "galculator"}),
            ("calculator", "calc", "الاله الحاسبه", "الآلة الحاسبة")),
    AppSpec("files", "Files", (("nautilus",), ("xdg-open", "{home}")),
            ("org.gnome.Nautilus.desktop",),
            frozenset({"nautilus"}),
            ("files", "file manager", "nautilus", "مدير الملفات", "الملفات")),
    AppSpec("settings", "Settings", (("gnome-control-center",),),
            ("gnome-control-center.desktop",),
            frozenset({"gnome-control-center", "gnome-control-c"}),
            ("settings", "الاعدادات")),
)


def _alias_index() -> dict[str, AppSpec]:
    index: dict[str, AppSpec] = {}
    for spec in APPS:
        for alias in (spec.key, spec.display_name, *spec.aliases):
            index.setdefault(normalize_key(alias), spec)
    return index


def find_app(name: object) -> AppSpec | None:
    """Exact (normalised) alias match only; fuzzy matching is the NLU's job."""
    if not isinstance(name, str):
        return None
    key = normalize_key(name)
    if key.startswith("the "):
        key = key[4:]
    return _alias_index().get(key)


def supported_app_names() -> list[str]:
    return [spec.display_name for spec in APPS]


# --------------------------------------------------------------------------
def _get_psutil() -> Any:
    try:
        import psutil  # noqa: PLC0415
    except ImportError:
        return None
    return psutil


def _has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _spawn_detached(argv: list[str]) -> subprocess.Popen:
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    threading.Thread(target=proc.wait, daemon=True).start()  # reap, avoid zombies
    return proc


def _start_and_check(argv: list[str]) -> bool:
    """False if it could not start or exited with an error code right away."""
    try:
        proc = _spawn_detached(argv)
    except OSError:
        return False
    if config.LAUNCH_SETTLE_SECONDS > 0:
        time.sleep(config.LAUNCH_SETTLE_SECONDS)
    code = proc.poll()
    # Only a real non-zero exit code is a failure. Exit 0 is normal when the app
    # hands the request to an already-running instance.
    return not (isinstance(code, int) and code != 0)


def _clean(text: object) -> str:
    return " ".join(str(text).split())[:40]


def _expand(argv: tuple[str, ...]) -> list[str]:
    home = str(Path.home())
    return [part.replace("{home}", home) for part in argv]


@guarded
def open_app(app_name: object) -> Result:
    """Launch an allowlisted application."""
    if not isinstance(app_name, str) or not app_name.strip():
        raise ActionError("Which application should I open?", "missing_parameter")
    spec = find_app(app_name)
    if spec is None:
        raise ActionError(f"I can't open {_clean(app_name)}.", "unsupported_app")

    found_executable = False
    for template in spec.commands:
        if shutil.which(template[0]) is None:
            continue
        found_executable = True
        if _start_and_check(_expand(template)):
            return ok(f"Opening {spec.display_name}.", app=spec.key, launched=True)

    gtk_launch = shutil.which("gtk-launch")
    if gtk_launch:
        for desktop_id in spec.desktop_ids:
            try:
                done = subprocess.run(
                    [gtk_launch, desktop_id],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=config.GTK_LAUNCH_TIMEOUT_SECONDS,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if getattr(done, "returncode", 1) == 0:
                return ok(f"Opening {spec.display_name}.", app=spec.key, launched=True)
            found_executable = True

    if found_executable and not _has_display():
        raise ActionError("No graphical desktop session is available.", "no_display")
    if found_executable:
        raise ActionError(f"{spec.display_name} failed to start.", "launch_failed")
    raise ActionError(f"{spec.display_name} is not installed.", "not_installed")


def _process_names(info: dict[str, Any]) -> set[str]:
    names = {info.get("name") or ""}
    cmdline = info.get("cmdline") or []
    if cmdline:
        names.add(os.path.basename(cmdline[0]))
    return names


def _find_processes(spec: AppSpec, psutil: Any) -> tuple[list[Any], bool]:
    excluded = {os.getpid()}
    try:
        excluded.update(p.pid for p in psutil.Process().parents())
    except Exception:  # noqa: BLE001
        pass
    uid = os.getuid()
    found: list[Any] = []
    skipped_self = False
    for proc in psutil.process_iter(["pid", "ppid", "name", "cmdline", "uids"]):
        info = proc.info
        uids = info.get("uids")
        if uids is None or uids.real != uid:
            continue
        if not (_process_names(info) & spec.process_names):
            continue
        if info["pid"] in excluded:
            skipped_self = True
            continue
        found.append(proc)
    return found, skipped_self


@guarded
def close_app(app_name: object) -> Result:
    """Ask an allowlisted application to quit (SIGTERM only, never SIGKILL)."""
    if not isinstance(app_name, str) or not app_name.strip():
        raise ActionError("Which application should I close?", "missing_parameter")
    spec = find_app(app_name)
    if spec is None:
        raise ActionError(f"I can't close {_clean(app_name)}.", "unsupported_app")
    psutil = _get_psutil()
    if psutil is None:
        raise ActionError("Closing applications needs the psutil package.", "missing_dependency")

    matches, skipped_self = _find_processes(spec, psutil)
    if not matches:
        if skipped_self:
            raise ActionError(
                f"I can't close {spec.display_name} because EchoOS is running in it.",
                "self_protected",
            )
        return ok(f"{spec.display_name} is not running.", app=spec.key, closed=0)

    matched_pids = {p.info["pid"] for p in matches}
    roots = [p for p in matches if p.info.get("ppid") not in matched_pids]  # parents only
    denied = False
    for proc in roots:
        try:
            proc.terminate()
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            denied = True
    _, alive = psutil.wait_procs(roots, timeout=config.CLOSE_TIMEOUT_SECONDS)
    if denied:
        raise ActionError(f"Permission denied while closing {spec.display_name}.", "permission_denied")
    if alive:
        raise ActionError(
            f"{spec.display_name} did not close. It may be waiting for you to save your work.",
            "close_timeout",
        )
    return ok(f"Closed {spec.display_name}.", app=spec.key, closed=len(roots))


@guarded
def open_folder(directory: object = None) -> Result:
    """Open a safe folder in the desktop file manager."""
    path = resolve_directory(directory, write=False)
    for command in ("xdg-open", "nautilus"):
        if shutil.which(command) and _start_and_check([command, str(path)]):
            return ok(f"Opening {label_for(path)}.", path=str(path))
    if not _has_display():
        raise ActionError("No graphical desktop session is available.", "no_display")
    raise ActionError("I could not open the file manager.", "launch_failed")
