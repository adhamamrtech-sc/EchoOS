# Interfaces between modules

These formats are agreed by the whole team. Do not change one without telling everyone.

| Function            | File                    | Takes                        | Returns                                                        |
| ------------------- | ----------------------- | ---------------------------- | -------------------------------------------------------------- |
| `record(seconds=5)` | `audio.py`              | number of seconds            | NumPy array: 1-D, float32, mono, 16000 Hz, values from -1 to 1 |
| `transcribe(audio)` | `asr.py`                | the array from `record()`    | text string (empty string if nothing was heard)                |
| `understand(text)`  | `nlu/` (package)        | text string                  | dict, see below                                                |
| `run(intent)`       | `actions/__init__.py`   | the dict from `understand()` | dict, see below                                                |
| `speak(text)`       | `feedback.py`           | text string                  | nothing                                                        |

## Intent (returned by understand)

    {"action": "set_wifi", "target": "wifi", "params": {"state": "off"},
     "score": 1.0, "confidence": 1.0, "confidence_label": "high", "status": "ok"}

- `action`: one of the names in `ALLOWED_ACTIONS`, or `"unknown"` for a sentence that is not understood.
- `target`: text or `None` (for example the app name in `open_app`).
- `params`: a dict, empty `{}` if there are none. Numbers are real numbers, not text (`50`, not `"50"`).
- `confidence`: a number from 0 to 1. `confidence_label` is the same as text: `high`, `medium` or `low`.
- `status`: `"ok"`, or why the sentence was rejected (`unknown`, `missing_target`, `missing_number`, `invalid_number`, ...).

## Action result (returned by run)

    {"status": "ok", "message": "Volume set to 50%"}

- `status`: `"ok"`, `"error"` or `"needs_confirmation"`.
- `message`: a short sentence that can be spoken out loud.
- Risky actions return `needs_confirmation` unless `params["confirmed"] is True`.
  Only `main.py` sets `confirmed`, and only after a clear spoken yes.

## Command status

The NLU may understand a command before an action exists for it. Only commands
marked **implemented** can run. When you add a handler to `ALLOWED_ACTIONS`,
change its row here and remove it from `PENDING` in `tests/test_nlu_actions.py`.

| Action               | Status          | params                    | Owner / note                                         |
| -------------------- | --------------- | ------------------------- | ---------------------------------------------------- |
| `open_app`           | implemented     | target = app name         | `actions/apps_files.py` (Dana)                       |
| `volume_up`          | implemented     | none                      | `actions/system_network.py` (Menna)                  |
| `set_volume`         | implemented     | `value`: 0 to 100         | Menna                                                |
| `set_brightness`     | implemented     | `value`: 0 to 100         | Menna. Needs user in the `video` group (no sudo)     |
| `lock_screen`        | implemented     | none                      | Menna                                                |
| `get_network_status` | implemented     | none                      | Menna                                                |
| `set_wifi`           | implemented     | `state`: `on` or `off`    | Menna. `off` needs confirmation                      |
| `confirm_wifi_off`   | implemented     | none                      | internal helper, the NLU never outputs it            |
| `set_bluetooth`      | implemented     | `state`: `on` or `off`    | Menna. `off` needs confirmation                      |
| `get_system_info`    | implemented     | `metrics`: cpu, ram, disk | Menna. Uses psutil, falls back to `uname -a`         |
| `close_app`          | implemented         | target = app name         | Dana                                                 |
| `open_folder`        | implemented         | target = folder           | Dana                                                 |
| `create_file`        | implemented         | `filename`                | Dana                                                 |
| `create_folder`      | implemented         | `name`                    | Dana                                                 |
| `rename_file`        | implemented         | `old`, `new`              | Dana                                                 |
| `list_files`         | implemented         | optional `folder`         | Dana                                                 |
| `get_time`           | planned         | none                      | unassigned                                           |
| `screenshot`         | planned         | none                      | unassigned                                           |
| `show_processes`     | planned         | none                      | unassigned                                           |
| `exit`               | planned         | none                      | handled in `main.py` later                           |
| `delete_file`        | implemented         | `filename`                | asks first; deletes only a confirmed, unchanged file (Dana)    |
| `shutdown`           | blocked         | none                      | dangerous: needs confirmation and a safety review    |
| `restart`            | blocked         | none                      | dangerous: needs confirmation and a safety review    |

New actions are added to `ALLOWED_ACTIONS` by the Team Leader after a safety review.
