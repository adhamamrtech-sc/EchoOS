# Interfaces between modules

These formats are shared contracts. Coordinate with the relevant owner before changing one, and update the tests and this document in the same pull request.

| Function | File | Takes | Returns |
| --- | --- | --- | --- |
| `listen_once(...)` | `audio.py` | Listening / VAD options | Recognized text, or an empty string when no speech is captured |
| `record_until_silence(...)` | `audio.py` | Recording limits and VAD settings | NumPy array: 1-D, float32, mono, 16 kHz |
| `record(seconds=5)` | `audio.py` | Number of seconds | Fixed-length 1-D float32 audio array; mainly used by diagnostics and recording tools |
| `strip_wake_word(text)` | `audio.py` | Recognized text | Tuple: whether the wake phrase was found, and the remaining command text |
| `transcribe(audio, language=None)` | `asr.py` | Mono 16 kHz audio array | Text string (empty string if nothing was recognized) |
| `understand(text)` | `nlu/` package | Text string | Intent candidate dictionary |
| `run(intent)` | `actions/__init__.py` | Validated decision dictionary | Action-result dictionary |
| `speak(text)` | `feedback.py` | Text string | Nothing |

The normal application path uses `listen_once()`; `record()` remains available for fixed-duration diagnostics and data collection.

## Intent candidate (returned by understand)

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
- Only `main.py` sets `confirmed`, and only after a clear spoken yes.

## Command status

The NLU may understand a command before an action exists for it. Only commands marked **implemented** can run. When you add a handler to `ALLOWED_ACTIONS`, change its row here and remove it from `PENDING` in `tests/test_nlu_actions.py`.

| Action | Status | params | Owner / note |
| --- | --- | --- | --- |
| `open_app` | implemented | target = app name | `actions/apps_files.py` |
| `volume_up` | implemented | none | `actions/system_network.py` |
| `set_volume` | implemented | `value`: 0 to 100 | `actions/system_network.py` |
| `set_brightness` | implemented | `value`: 0 to 100 | Requires user in the `video` group (no sudo) |
| `lock_screen` | implemented | none | `actions/system_network.py` |
| `get_network_status` | implemented | none | `actions/system_network.py` |
| `set_wifi` | implemented | `state`: `on` or `off` | `off` needs confirmation |
| `confirm_wifi_off` | implemented | none | Internal helper; the NLU never outputs it |
| `set_bluetooth` | implemented | `state`: `on` or `off` | `off` needs confirmation |
| `get_system_info` | implemented | `metrics`: cpu, ram, disk | Uses psutil, falls back to `uname -a` |
| `close_app` | implemented | target = app name | `actions/apps_files.py` |
| `open_folder` | implemented | target = folder | `actions/apps_files.py` |
| `create_file` | implemented | `filename`, optional `folder` | `actions/apps_files.py` |
| `create_folder` | implemented | `name`, optional `folder` | `actions/apps_files.py` |
| `rename_file` | implemented | `old`, `new`, optional `folder` | `actions/apps_files.py` |
| `list_files` | implemented | optional `folder` | `actions/apps_files.py` |
| `get_time` | planned | none | Unassigned |
| `screenshot` | planned | none | Unassigned |
| `show_processes` | planned | none | Unassigned |
| `exit` | planned | none | Handled in `main.py` later |
| `delete_file` | implemented | `filename`, optional `folder` | Asks first; deletes only a confirmed, unchanged file |
| `shutdown` | blocked | none | Dangerous: needs confirmation and a safety review |
| `restart` | blocked | none | Dangerous: needs confirmation and a safety review |

New actions are added to `ALLOWED_ACTIONS` by the Team Leader after a safety review.
