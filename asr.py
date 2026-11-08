"""Speech to text. Owner: ASR Engineers."""
import os

import numpy as np
import vosk
from faster_whisper import WhisperModel

# Settings can be changed without editing code (set them before python main.py):
#   ECHOOS_WHISPER = tiny | base | small | medium     (default: small)
#   ECHOOS_LANG    = en | ar | auto                   (default: en)
whisper_model_size = os.environ.get("ECHOOS_WHISPER", "small")
whisper_model = WhisperModel(whisper_model_size, device="cpu", compute_type="int8")

vosk_model_path = "model_vosk"
vosk_model = None

# Short clips ("turn on Wi-Fi") are easy to mis-detect as another language
# or as numbers. Fixing the language and listing the commands we expect
# makes Whisper far more likely to write them correctly.
COMMAND_HINT = (
    "Voice commands: turn on Wi-Fi, turn off Wi-Fi, turn on Bluetooth, "
    "turn off Bluetooth, make it louder, set volume to 40, set brightness to 60, "
    "open Firefox, open Chrome, lock my computer, system info, network status, yes, no."
)


def get_vosk_model():
    global vosk_model
    if vosk_model is None and os.path.exists(vosk_model_path):
        vosk_model = vosk.Model(vosk_model_path)
    return vosk_model


def _language(language):
    """Explicit argument first, then ECHOOS_LANG. 'auto' lets Whisper guess."""
    chosen = language or os.environ.get("ECHOOS_LANG", "en")
    return None if chosen == "auto" else chosen


def transcribe(audio, language=None):
    """Return the text of a float32 mono 16 kHz array, or '' on failure."""
    try:
        if isinstance(audio, np.ndarray):
            audio_data = audio.astype(np.float32)
        else:
            audio_data = np.array(audio, dtype=np.float32)

        chosen = _language(language)

        segments, _info = whisper_model.transcribe(
            audio_data,
            beam_size=5,
            language=chosen,
            initial_prompt=COMMAND_HINT if chosen == "en" else None,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text_result = " ".join(segment.text.strip() for segment in segments).strip()

        if text_result:
            return text_result
    except Exception as error:
        print(f"[asr] transcription error: {error}")

    return ""
