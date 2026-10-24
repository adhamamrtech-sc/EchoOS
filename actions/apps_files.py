"""Apps and files actions. Owner: Actions Engineer 1 (Dana).

Every handler takes the whole intent dict (like actions/system_network.py) and
returns {"status", "message"} (INTERFACES.md). Intent fields used, exactly as
nlu/entities.py produces them:

    open_app / close_app   target = app key ("firefox", "chrome", ...)
    open_folder            target = folder ("documents", ...)
    list_files             params["folder"] optional (target is just "files")
    create_file            params["filename"]
    create_folder          params["name"]
    rename_file            params["old"], params["new"]
    delete_file            params["filename"]; asks first, deletes only on the
                           confirmed re-run from main.py (see file_app_core/confirmation.py)

Files are only touched in Documents and Downloads (SECURITY.md). The logic lives
in actions/file_app_core/.
"""
from .file_app_core import apps, confirmation, files
from .file_app_core.results import Result, error, guarded


def _params(intent) -> dict:
    params = intent.get("params") if isinstance(intent, dict) else None
    return params if isinstance(params, dict) else {}


def _pick(params: dict, *keys):
    for key in keys:
        if params.get(key) not in (None, ""):
            return params[key]
    return None


def _folder(params: dict):
    return _pick(params, "folder", "directory", "path")


def _target(intent):
    return intent.get("target") if isinstance(intent, dict) else None


def _plain(handler):
    """Wrap a handler: reject non-dict intents and drop any pending delete."""

    @guarded
    def wrapper(intent) -> Result:
        if not isinstance(intent, dict):
            return error("I did not understand that command.", "invalid_intent")
        confirmation.clear()
        return handler(intent)

    wrapper.__name__ = handler.__name__
    wrapper.__doc__ = handler.__doc__
    return wrapper


@_plain
def open_app(intent):
    """Open an app from the supported list."""
    params = _params(intent)
    return apps.open_app(_target(intent) or _pick(params, "app", "name"))


@_plain
def close_app(intent):
    """Close an app from the supported list (SIGTERM only)."""
    params = _params(intent)
    return apps.close_app(_target(intent) or _pick(params, "app", "name"))


@_plain
def open_folder(intent):
    """Open a safe folder in the file manager."""
    params = _params(intent)
    return apps.open_folder(_folder(params) or _target(intent))


@_plain
def list_files(intent):
    """List the files in a safe folder (Documents by default)."""
    return files.list_files(_folder(_params(intent)))


@_plain
def create_file(intent):
    """Create an empty file (in Documents unless a folder is given)."""
    params = _params(intent)
    return files.create_file(_folder(params), _pick(params, "filename", "name"))


@_plain
def create_folder(intent):
    """Create a folder (in Documents unless a folder is given)."""
    params = _params(intent)
    return files.create_folder(_folder(params), _pick(params, "name", "foldername"))


@_plain
def rename_file(intent):
    """Rename a file or folder inside Documents or Downloads."""
    params = _params(intent)
    return files.rename_item(
        _folder(params),
        _pick(params, "old", "old_name"),
        _pick(params, "new", "new_name"),
    )


@guarded
def delete_file(intent) -> Result:
    """Delete a file. Returns needs_confirmation first; deletes on the confirmed re-run."""
    if not isinstance(intent, dict):
        return error("I did not understand that command.", "invalid_intent")
    params = _params(intent)
    return files.delete_file(
        _folder(params),
        _pick(params, "filename", "name"),
        confirmed=params.get("confirmed") is True,
    )


# For the Team Leader: `ALLOWED_ACTIONS.update(apps_files.ACTIONS)` after review.
ACTIONS = {
    "open_app": open_app,
    "close_app": close_app,
    "open_folder": open_folder,
    "list_files": list_files,
    "create_file": create_file,
    "create_folder": create_folder,
    "rename_file": rename_file,
    "delete_file": delete_file,
}
