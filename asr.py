"""Speech to text. Owner: ASR Engineers."""

import os
import numpy as np
from faster_whisper import WhisperModel

whisper_model_size = os.environ.get("ECHOOS_WHISPER", "large-v3-turbo")
whisper_model = WhisperModel(whisper_model_size, device="cpu", compute_type="int8")

SAMPLE_RATE = 16000

def _language(language: str | None) -> str | None:
    chosen = (language or os.environ.get("ECHOOS_LANG", "auto")).strip().lower()
    return None if chosen in ("", "auto") else chosen

def _condition_audio(audio: np.ndarray) -> np.ndarray:
    """RMS normalization + light padding for robust open-vocabulary transcription."""
    if audio.size == 0:
        return audio

    # RMS Normalization لتوحيد طاقة الصوت
    rms = float(np.sqrt(np.mean(np.square(audio))))
    if rms > 1e-4:
        target_rms = 0.08
        audio = np.clip(audio * (target_rms / rms), -0.95, 0.95)

    # Padding خفيف لحماية أول حرف وجملة الأوامر القصيرة
    pad = np.zeros(int(0.15 * SAMPLE_RATE), dtype=np.float32)
    return np.ascontiguousarray(np.concatenate([pad, audio, pad]), dtype=np.float32)

def transcribe(audio, language: str | None = None) -> str:
    """Return the transcribed text of a float32 mono 16 kHz array, or '' on failure."""
    try:
        audio_data = np.asarray(audio, dtype=np.float32)
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=-1)

        audio_data = _condition_audio(audio_data)
        if audio_data.size == 0:
            return ""

        chosen_lang = _language(language)

        segments, _info = whisper_model.transcribe(
            audio_data,
            language=chosen_lang,             # None للـ auto (مفتوح على 99 لغة)
            beam_size=5,
            best_of=5,
            temperature=0.0,
            initial_prompt=None,
            condition_on_previous_text=False,
            vad_filter=True,                  # تفعيل Silero VAD الداخلي المובدث في المكتبة بأمان
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=400,
            ),
            without_timestamps=True,
        )

        text_result = " ".join(segment.text.strip() for segment in segments).strip()
        if text_result:
            return text_result

    except Exception as error:
        print(f"[asr] transcription error: {error}")

    return ""

