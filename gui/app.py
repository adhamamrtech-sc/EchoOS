"""
EchoOS Desktop GUI Application
Runs as a native desktop window on Windows (WebView2) and Ubuntu (WebKitGTK).
Uses pywebview with local Flask server and EchoOS Core (command_processor.py).
"""

import os
import sys
import json
import platform
import threading
from flask import Flask, render_template, request, Response

# ── UTF-8 Terminal Safety ──────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Add EchoOS Root to sys.path ─────────────────────────────────────────────
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ── Import Shared Command Processor & Audio ─────────────────────────────────
PROCESSOR = None

try:
    from command_processor import CommandProcessor
    from main import strip_wake_word

    # ECHOOS_GUI_SPEAK=1 also speaks replies on the server (espeak). Off by
    # default because the page already reads replies aloud in the browser.
    _speaker = None
    if os.environ.get("ECHOOS_GUI_SPEAK") == "1":
        from feedback import speak as _speaker

    PROCESSOR = CommandProcessor(speaker=_speaker)
    CORE_AVAILABLE = True
    print("[EchoOS GUI] ✅ Connected to the EchoOS pipeline (main.process_text)")
except Exception as e:
    CORE_AVAILABLE = False
    print(f"[EchoOS GUI] ⚠️ Failed to load the EchoOS pipeline: {e}")

try:
    from audio import listen_once
    AUDIO_AVAILABLE = True
    print("[EchoOS GUI] ✅ Connected to EchoOS Native Audio (Whisper & VAD)")
except Exception as e:
    AUDIO_AVAILABLE = False
    print(f"[EchoOS GUI] ⚠️ Audio module notice: {e}")

# ── Flask Application Setup ─────────────────────────────────────────────────
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
try:
    app.json.ensure_ascii = False
except Exception:
    pass

# One microphone: only one listen at a time.
LISTEN_LOCK = threading.Lock()

# Only these Host headers are accepted. Blocks DNS-rebinding attacks, where a
# web page makes the browser talk to this local server under another name.
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


def _host_name(host_header):
    """"localhost:5050" -> "localhost", "[::1]:5050" -> "[::1]"."""
    host = (host_header or "").strip().lower()
    if host.startswith("["):
        return host.split("]")[0] + "]"
    return host.rsplit(":", 1)[0] if ":" in host else host


@app.before_request
def only_local_hosts():
    if _host_name(request.host) not in ALLOWED_HOSTS:
        return Response("Forbidden", status=403)


def utf8_jsonify(data, status_code=200):
    """Return JSON response with explicit UTF-8 charset."""
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status_code,
        mimetype="application/json; charset=utf-8",
    )


# ── Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def status():
    return utf8_jsonify({
        "echoos_available": CORE_AVAILABLE,
        "audio_available": AUDIO_AVAILABLE,
        "platform": platform.system(),
        "mode": "EchoOS Desktop App",
        "pending_confirmation": bool(PROCESSOR and PROCESSOR.has_pending()),
    })


@app.route("/command", methods=["POST"])
def command():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()

    if not text:
        return utf8_jsonify({"status": "error", "message": "No command provided."})

    if not CORE_AVAILABLE:
        return utf8_jsonify({"status": "error", "message": "EchoOS Core is not available."})

    return utf8_jsonify(PROCESSOR.handle(text))


@app.route("/api/listen", methods=["POST"])
def listen():
    """Record from the microphone (audio.py + Whisper) and run what was said."""
    if not CORE_AVAILABLE:
        return utf8_jsonify({"status": "error", "message": "EchoOS Core is not available."})

    if not AUDIO_AVAILABLE:
        return utf8_jsonify({
            "status": "error",
            "message": "Native audio capture is not available on this environment.",
        })

    if not LISTEN_LOCK.acquire(blocking=False):
        return utf8_jsonify({"status": "error", "message": "Already listening."})

    try:
        # Push-to-talk: no wake word needed, the button is the trigger.
        text = listen_once(require_wake_word=False, start_timeout=6, vad_mode=0)

        if not text:
            return utf8_jsonify({
                "status": "no_speech",
                "message": "I didn't hear anything, please try again.",
            })

        # If the user said "Hi Echo, ..." anyway, drop the wake word.
        heard_wake_word, rest = strip_wake_word(text)
        command_text = rest if heard_wake_word and rest else text

        result = PROCESSOR.handle(command_text)
        result["heard_text"] = text
        return utf8_jsonify(result)

    except Exception:
        return utf8_jsonify({
            "status": "error",
            "message": "Recording failed. Check the microphone and try again.",
        })

    finally:
        LISTEN_LOCK.release()


# ── Desktop Window Launcher ─────────────────────────────────────────────────
def start_flask(port):
    app.run(debug=False, host="127.0.0.1", port=port, use_reloader=False)


if __name__ == "__main__":
    port = int(os.environ.get("ECHOOS_GUI_PORT", 5050))

    # Check if user passed --server-only or if pywebview is missing
    server_only = "--server" in sys.argv

    if server_only:
        print(f"\n  🤖  EchoOS Server Running at: http://127.0.0.1:{port}\n")
        app.run(debug=False, host="127.0.0.1", port=port)
    else:
        try:
            import webview

            # Run Flask in background thread
            t = threading.Thread(target=start_flask, args=(port,), daemon=True)
            t.start()

            print(f"\n  🚀  Launching EchoOS Desktop App ({platform.system()})...\n")

            # Create native desktop window
            window = webview.create_window(
                title="EchoOS — Voice Controlled Operating System",
                url=f"http://127.0.0.1:{port}",
                width=480,
                height=780,
                resizable=True,
                background_color="#080911",
                text_select=False,
            )
            webview.start()

        except Exception as e:
            print(f"\n  ⚠️  Could not start Desktop Window: {e}")
            print(f"  Fallback: Running browser server on http://localhost:{port}\n")
            app.run(debug=False, host="127.0.0.1", port=port)
