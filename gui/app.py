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
try:
    from command_processor import process_command, confirm_command, is_yes
    CORE_AVAILABLE = True
    print("[EchoOS GUI] ✅ Connected to EchoOS Core via command_processor.py")
except Exception as e:
    CORE_AVAILABLE = False
    print(f"[EchoOS GUI] ⚠️ Failed to load command_processor: {e}")

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

PENDING_CONFIRMATIONS = {}


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
        "pending_confirmations": len(PENDING_CONFIRMATIONS),
    })


@app.route("/command", methods=["POST"])
def command():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    session_id = data.get("session_id", "default_user")

    if not text:
        return utf8_jsonify({
            "status": "error",
            "message": "No command provided.",
        })

    if not CORE_AVAILABLE:
        return utf8_jsonify({
            "status": "error",
            "message": "EchoOS Core is not available.",
        })

    # Case 1: Answering a pending confirmation
    if session_id in PENDING_CONFIRMATIONS:
        pending_intent = PENDING_CONFIRMATIONS.pop(session_id)
        result = confirm_command(pending_intent, text)
        clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
        return utf8_jsonify(clean_result)

    # Case 2: Fresh command
    result = process_command(text)

    # If action requires confirmation, save the pending intent
    if result.get("status") == "needs_confirmation":
        PENDING_CONFIRMATIONS[session_id] = result.get("_pending_intent")

    clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
    return utf8_jsonify(clean_result)


@app.route("/api/listen", methods=["POST"])
def listen():
    """Trigger native PC microphone recording via audio.py + Whisper."""
    if not AUDIO_AVAILABLE:
        return utf8_jsonify({
            "status": "error",
            "message": "Native audio capture is not available on this environment.",
        })

    try:
        # Listen with relaxed VAD sensitivity (vad_mode=0) suitable for laptop mics
        text = listen_once(require_wake_word=False, start_timeout=6, vad_mode=0)
        if not text:
            return utf8_jsonify({
                "status": "no_speech",
                "message": "لم أسمع أي كلام، حاول مرة أخرى.",
            })

        # Process the transcribed text through EchoOS
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id", "default_user")

        if session_id in PENDING_CONFIRMATIONS:
            pending_intent = PENDING_CONFIRMATIONS.pop(session_id)
            result = confirm_command(pending_intent, text)
        else:
            result = process_command(text)
            if result.get("status") == "needs_confirmation":
                PENDING_CONFIRMATIONS[session_id] = result.get("_pending_intent")

        clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
        clean_result["heard_text"] = text
        return utf8_jsonify(clean_result)

    except Exception as e:
        return utf8_jsonify({
            "status": "error",
            "message": f"خطأ في التسجيل الصوتي: {str(e)}",
        })


# ── Desktop Window Launcher ─────────────────────────────────────────────────
def start_flask(port):
    app.run(debug=False, host="127.0.0.1", port=port, use_reloader=False)


if __name__ == "__main__":
    port = int(os.environ.get("ECHOOS_GUI_PORT", 5050))

    # Check if user passed --server-only or if pywebview is missing
    server_only = "--server" in sys.argv

    if server_only:
        print(f"\n  🤖  EchoOS Server Running at: http://127.0.0.1:{port}\n")
        app.run(debug=False, host="0.0.0.0", port=port)
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
            app.run(debug=False, host="0.0.0.0", port=port)
