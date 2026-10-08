    # Interfaces between modules

These formats are agreed by the whole team. Do not change one without telling everyone.

| Function            | File                | Takes                        | Returns                                                        |
| ------------------- | ------------------- | ---------------------------- | -------------------------------------------------------------- |
| `record(seconds=5)` | audio.py            | number of seconds            | NumPy array: 1-D, float32, mono, 16000 Hz, values from -1 to 1 |
| `transcribe(audio)` | asr.py              | the array from `record()`    | text string (empty string if nothing was heard)                |
| `understand(text)`  | nlu.py              | text string                  | dict, see below                                                |
| `run(intent)`       | actions/**init**.py | the dict from `understand()` | dict, see below                                                |
| `speak(text)`       | feedback.py         | text string                  | nothing                                                        |

## Intent (returned by understand)

    {"action": "set_volume", "target": None, "params": {"value": 50}, "confidence": 0.9}

- `action`: one of the names in `ALLOWED_ACTIONS`, or `"unknown"` for a sentence that is not understood.
- `target`: text or `None` (for example the app name in `open_app`).
- `params`: a dict, empty `{}` if there are none. Numbers are real numbers, not text (`50`, not `"50"`).
- `confidence`: a number from 0 to 1.

## Action result (returned by run)

    {"status": "ok", "message": "Volume set to 50%"}

- `status`: `"ok"`, `"error"` or `"needs_confirmation"`.
- `message`: a short sentence that can be spoken out loud.

## Allowed actions right now

| Action               | target                          | params            |
| -------------------- | ------------------------------- | ----------------- |
| `open_app`           | app name, for example `firefox` | none              |
| `set_volume`         | none                            | `value`: 0 to 100 |
| `set_brightness`     | none                            | `value`: 0 to 100 |
| `lock_screen`        | none                            | none              |
| `get_network_status` | none                            | none              |

New actions are added to `ALLOWED_ACTIONS` by the Team Leader after a safety review.
