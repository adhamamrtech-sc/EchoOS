"""
Create Windows desktop and Start Menu shortcuts for EchoOS.

Shortcuts launch the GUI (gui/app.py) using pythonw.exe so no terminal
window appears. Run this once after setting up the virtual environment:

    .venv\\Scripts\\python.exe gui\\create_shortcut.py

Requires pywin32 (pip install pywin32), which is added to gui/requirements.txt.
"""

import os
import sys
import pathlib
import textwrap


def _require_windows() -> None:
    if sys.platform != "win32":
        print("[EchoOS] create_shortcut.py يشتغل على Windows بس.")
        sys.exit(1)


def _resolve_paths() -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    """Return (project_root, pythonw_exe, app_py)."""
    # الملف ده موجود في gui/ — نطلع لفوق للـ project root
    gui_dir = pathlib.Path(__file__).resolve().parent
    project_root = gui_dir.parent

    pythonw = project_root / ".venv" / "Scripts" / "pythonw.exe"
    app_py = gui_dir / "app.py"
    icon_path = gui_dir / "static" / "echoos.svg"

    if not pythonw.exists():
        print("[EchoOS] مش لاقي .venv\\Scripts\\pythonw.exe")
        print("         اعمل الـ venv الأول:\n"
              "           python -m venv .venv\n"
              "           .venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
              "           .venv\\Scripts\\python.exe -m pip install -r gui\\requirements.txt")
        sys.exit(1)

    if not app_py.exists():
        print(f"[EchoOS] مش لاقي gui\\app.py في {app_py}")
        sys.exit(1)

    return project_root, pythonw, app_py, icon_path


def _get_shell():
    """Get WScript.Shell instance."""
    try:
        import win32com.client  # type: ignore[import]
    except ImportError:
        print("[EchoOS] مكتبة pywin32 مش متنصبة.")
        print("         نصّبها بـ: .venv\\Scripts\\python.exe -m pip install pywin32")
        sys.exit(1)
    return win32com.client.Dispatch("WScript.Shell")


def _get_desktop_folder(shell) -> pathlib.Path:
    """Return the active Desktop folder (handles OneDrive and redirected folders)."""
    try:
        desktop_str = shell.SpecialFolders("Desktop")
        if desktop_str and pathlib.Path(desktop_str).is_dir():
            return pathlib.Path(desktop_str)
    except Exception:
        pass

    import winreg  # type: ignore[import]
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        val, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        expanded = pathlib.Path(os.path.expandvars(val))
        if expanded.is_dir():
            return expanded
    except Exception:
        pass

    return pathlib.Path.home() / "Desktop"


def _get_start_menu_folder(shell) -> pathlib.Path:
    """Return the user's Start Menu Programs folder."""
    try:
        programs_str = shell.SpecialFolders("Programs")
        if programs_str and pathlib.Path(programs_str).is_dir():
            return pathlib.Path(programs_str)
    except Exception:
        pass

    return pathlib.Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def _create_lnk(
    shell,
    shortcut_path: pathlib.Path,
    target: pathlib.Path,
    arguments: str,
    working_dir: pathlib.Path,
    icon: pathlib.Path,
    description: str,
) -> None:
    """Create a .lnk shortcut using Windows Script Host via pywin32."""
    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = str(target)
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = str(working_dir)
    shortcut.Description = description

    # الـ SVG مش مدعوم كـ icon في Windows مباشرة — بنستخدم أيقونة Python كـ fallback
    # لو عندك echoos.ico حطّه في gui/static/ وهيتاخد تلقائياً
    ico = icon.with_suffix(".ico")
    if ico.exists():
        shortcut.IconLocation = str(ico)
    else:
        shortcut.IconLocation = str(target)   # pythonw.exe icon

    shortcut.WindowStyle = 1   # Normal window
    shortcut.save()


def main() -> None:
    _require_windows()

    project_root, pythonw, app_py, icon_path = _resolve_paths()
    shell = _get_shell()

    shortcut_name = "EchoOS.lnk"
    description = "EchoOS — Voice Controlled Operating System"
    # نمرر مسار app.py كـ argument لـ pythonw.exe
    arguments = f'"{app_py}"'

    created = []

    # 1. Desktop shortcut (يدعم OneDrive وجميع مسارات Desktop الموجهة)
    desktop = _get_desktop_folder(shell)
    if desktop.is_dir():
        desktop_lnk = desktop / shortcut_name
        _create_lnk(
            shell=shell,
            shortcut_path=desktop_lnk,
            target=pythonw,
            arguments=arguments,
            working_dir=project_root,
            icon=icon_path,
            description=description,
        )
        created.append(f"Desktop: {desktop_lnk}")
        print(f"[EchoOS] ✓ Desktop shortcut: {desktop_lnk}")

    # 2. Start Menu shortcut
    start_menu = _get_start_menu_folder(shell) / "EchoOS"
    start_menu.mkdir(parents=True, exist_ok=True)
    start_menu_lnk = start_menu / shortcut_name
    _create_lnk(
        shell=shell,
        shortcut_path=start_menu_lnk,
        target=pythonw,
        arguments=arguments,
        working_dir=project_root,
        icon=icon_path,
        description=description,
    )
    created.append(f"Start Menu: {start_menu_lnk}")
    print(f"[EchoOS] ✓ Start Menu shortcut: {start_menu_lnk}")

    print()
    print("[EchoOS] الـ shortcuts اتعملت بنجاح!")
    print("         دوس على EchoOS من الـ Desktop أو Start Menu وهيفتح من غير terminal.")
    print()
    print("         لو عاوز تلغي الـ shortcuts:")
    print(textwrap.dedent(f"""
           Desktop:    del "{desktop / shortcut_name}"
           Start Menu: rmdir /s /q "{start_menu}"
    """).strip())


if __name__ == "__main__":
    main()
