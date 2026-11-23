"""
EchoOS GUI bridge.

Ubuntu/WSL use the local browser interface. Windows may use pywebview,
with a browser-server fallback if the native window cannot start.
"""
import json
import logging
import os
import platform
import sys
import threading
import time

from flask import Flask, Response, render_template, request

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower() != "utf-8":
                stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass

logging.basicConfig(
    level=os.environ.get("ECHOOS_GUI_LOG_LEVEL", "INFO").upper(),
    format="[EchoOS GUI] %(levelname)s: %(message)s",
)
logger = logging.getLogger("echoos.gui")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

PROCESSOR = None
PROCESSOR_LOCK = threading.RLock()
LISTEN_LOCK = threading.Lock()
LISTEN_CANCEL = threading.Event()

try:
    from command_processor import CommandProcessor
    from main import strip_wake_word

    _speaker = None
    if os.environ.get("ECHOOS_GUI_SPEAK") == "1":
        from feedback import speak as _speaker

    PROCESSOR = CommandProcessor(speaker=_speaker)
    CORE_AVAILABLE = True
    logger.info("Connected to EchoOS pipeline (main.process_text)")
except Exception:
    CORE_AVAILABLE = False
    logger.exception("Could not load EchoOS command pipeline")

try:
    from audio import listen_once
    AUDIO_AVAILABLE = True
    logger.info("Connected to EchoOS native audio (Whisper and VAD)")
except Exception:
    AUDIO_AVAILABLE = False
    logger.exception("Native audio is unavailable")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
try:
    app.json.ensure_ascii = False
except AttributeError:
    pass

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


def _host_name(host_header):
    """Extract a hostname, preserving bracketed IPv6 addresses."""
    host = (host_header or "").strip().lower()
    if host.startswith("["):
        return host.split("]", 1)[0] + "]"
    return host.rsplit(":", 1)[0] if ":" in host else host


@app.before_request
def only_local_hosts():
    if _host_name(request.host) not in ALLOWED_HOSTS:
        return Response("Forbidden", status=403)


def utf8_jsonify(data, status_code=200):
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status_code,
        mimetype="application/json; charset=utf-8",
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def status():
    with PROCESSOR_LOCK:
        pending = bool(PROCESSOR and PROCESSOR.has_pending())
    return utf8_jsonify({
        "echoos_available": CORE_AVAILABLE,
        "audio_available": AUDIO_AVAILABLE,
        "platform": platform.system(),
        "mode": "EchoOS GUI",
        "pending_confirmation": pending,
    })


@app.route("/command", methods=["POST"])
def command():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    command_text = str(data.get("text", "")).strip()

    if not command_text:
        return utf8_jsonify({"status": "error", "message": "No command provided."})
    if not CORE_AVAILABLE:
        return utf8_jsonify({"status": "error", "message": "EchoOS Core is unavailable."})

    # Typed commands have priority over an in-progress microphone recording.
    if LISTEN_LOCK.locked():
        LISTEN_CANCEL.set()

    with PROCESSOR_LOCK:
        return utf8_jsonify(PROCESSOR.handle(command_text))


LISTEN_TIMEOUTS = {"once": 8, "standby": 8, "session": 30}
CONFIRM_TIMEOUT = 6


@app.route("/api/listen", methods=["POST"])
def listen():
    """Capture one voice request; pending confirmations accept direct yes/no."""
    if not CORE_AVAILABLE:
        return utf8_jsonify({"status": "error", "message": "EchoOS Core is unavailable."})
    if not AUDIO_AVAILABLE:
        return utf8_jsonify({
            "status": "error",
            "message": "Native microphone audio is unavailable.",
        })

    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    requested_mode = data.get("mode")
    mode = (
        requested_mode
        if isinstance(requested_mode, str) and requested_mode in LISTEN_TIMEOUTS
        else "once"
    )

    if not LISTEN_LOCK.acquire(blocking=False):
        return utf8_jsonify({"status": "error", "message": "Already listening."})

    try:
        LISTEN_CANCEL.clear()
        with PROCESSOR_LOCK:
            waiting_for_answer = PROCESSOR.has_pending()
        timeout = CONFIRM_TIMEOUT if waiting_for_answer else LISTEN_TIMEOUTS[mode]

        started = time.monotonic()
        recognized_text = listen_once(
            require_wake_word=False,
            start_timeout=timeout,
        ) or ""
        logger.info(
            "%s heard %r (%.1fs including recording and Whisper)",
            mode,
            recognized_text,
            time.monotonic() - started,
        )

        if LISTEN_CANCEL.is_set():
            return utf8_jsonify({"status": "listen_cancelled"})

        with PROCESSOR_LOCK:
            pending_now = PROCESSOR.has_pending()

            # Recheck cancellation and pending state after recording to avoid
            # racing a typed yes/no or a newly-created confirmation.
            if LISTEN_CANCEL.is_set():
                return utf8_jsonify({"status": "listen_cancelled"})

            if waiting_for_answer and not pending_now:
                return utf8_jsonify({
                    "status": "confirmation_resolved",
                    "heard_text": recognized_text,
                })

            if pending_now:
                if not recognized_text:
                    return utf8_jsonify({"status": "confirmation_waiting"})
                result = PROCESSOR.handle(recognized_text)
                result["heard_text"] = recognized_text
                return utf8_jsonify(result)

            if not recognized_text:
                if mode == "standby":
                    return utf8_jsonify({"status": "standby_idle"})
                if mode == "session":
                    return utf8_jsonify({"status": "session_end"})
                return utf8_jsonify({
                    "status": "no_speech",
                    "message": "I didn't hear anything. Please try again.",
                })

            heard_wake_word, remaining_text = strip_wake_word(recognized_text)
            if mode == "standby" and not heard_wake_word:
                return utf8_jsonify({
                    "status": "standby_idle",
                    "heard_text": recognized_text,
                })

            if heard_wake_word and not remaining_text:
                return utf8_jsonify({
                    "status": "ok",
                    "message": "I'm listening.",
                    "heard_text": recognized_text,
                })

            command_text = remaining_text if heard_wake_word else recognized_text
            result = PROCESSOR.handle(command_text)
            result["heard_text"] = recognized_text
            return utf8_jsonify(result)

    except Exception:
        logger.exception("Microphone request failed")
        return utf8_jsonify({
            "status": "error",
            "message": "Recording failed. Check microphone access and the server log.",
        })
    finally:
        LISTEN_CANCEL.clear()
        LISTEN_LOCK.release()


def _run_browser_server(port):
    logger.info("Starting local browser interface at http://127.0.0.1:%s", port)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    port = int(os.environ.get("ECHOOS_GUI_PORT", "5050"))
    server_only = "--server" in sys.argv

    # Browser mode is the supported launch path on Ubuntu and WSL.
    if server_only or sys.platform != "win32":
        _run_browser_server(port)
    else:
        try:
            import webview
        except Exception:
            logger.exception("pywebview is unavailable; starting browser mode")
            _run_browser_server(port)
        else:
            # Start one server. A failed native window must not bind the same
            # port a second time in the browser fallback.
            from werkzeug.serving import make_server

            server = make_server("127.0.0.1", port, app, threaded=True)
            server_thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
                name="echoos-flask",
            )
            server_thread.start()
            try:
                webview.create_window(
                    title="EchoOS — Voice Controlled Operating System",
                    url=f"http://127.0.0.1:{port}",
                    width=480,
                    height=780,
                    resizable=True,
                    background_color="#080911",
                    text_select=False,
                )
                webview.start()
            except Exception:
                logger.exception("Native window failed; browser server remains available")
                print(
                    f"\n[EchoOS GUI] Open http://127.0.0.1:{port} in your browser.\n",
                    flush=True,
                )
                try:
                    server_thread.join()
                except KeyboardInterrupt:
                    logger.info("Stopping browser server")
            finally:
                server.shutdown()
                server_thread.join(timeout=2)
