"""Speech to text. Owner: ASR Engineers."""
import os
import threading
import numpy as np
from faster_whisper import WhisperModel
import re
import math
from difflib import get_close_matches
def snap(text, commands, cutoff=0.6):
    m = get_close_matches(text, commands, n=1, cutoff=cutoff)
    return m[0] if m else text
def _rank(score, prob):
    return score + 0.5 * math.log(max(prob, 1e-6))
_BAD_CHARS = re.compile(r"[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FFa-zA-Z0-9\s.,!?'\"،؟\-]")
whisper_model_size = os.environ.get("ECHOOS_WHISPER", "small")
_model = None
_lock = threading.Lock()
def get_model() -> WhisperModel:
    """ loading model at first time only """
    global _model
    if _model is None:
        with _lock:                       
            if _model is None:
                _model = WhisperModel(
                    whisper_model_size,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=int(os.environ.get("ECHOOS_THREADS", os.cpu_count() or 4)),
                )
    return _model
SAMPLE_RATE = 16000
def _language(language: str | None) -> str | None:
    chosen = (language or os.environ.get("ECHOOS_LANG", "auto")).strip().lower()
    return None if chosen in ("", "auto") else chosen
def _condition_audio(audio: np.ndarray) -> np.ndarray:
    """RMS normalization + light padding for robust open-vocabulary transcription."""
    if audio.size == 0:
        return audio
    rms = float(np.sqrt(np.mean(np.square(audio))))
    if rms > 1e-4:
        target_rms = 0.08
        audio = np.clip(audio * (target_rms / rms), -0.95, 0.95)
    pad = np.zeros(int(0.15 * SAMPLE_RATE), dtype=np.float32)
    return np.ascontiguousarray(np.concatenate([pad, audio, pad]), dtype=np.float32)
ALLOWED_LANGUAGES = ("en", "ar")
LOW_CONF = -0.6   
def _detect(model, audio) -> dict:
    try:
        _l, _p, all_probs = model.detect_language(
            audio, vad_filter=True, vad_parameters=dict(speech_pad_ms=400)
        )
    except Exception:
        _l, _p, all_probs = model.detect_language(audio)
    scores = dict(all_probs)
    return {c: scores.get(c, 0.0) for c in ALLOWED_LANGUAGES}
def _decode(model, audio, lang):
    segments, _info = model.transcribe(
        audio,
        language=lang,
        beam_size=3,
        temperature=0.0,
        initial_prompt=None,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300, speech_pad_ms=400),
        without_timestamps=True,
        no_repeat_ngram_size=3,     
        repetition_penalty=1.1,
    )
    segs = list(segments)
    text = " ".join(s.text.strip() for s in segs).strip()
    score = sum(s.avg_logprob for s in segs) / len(segs) if segs else -10.0
    return text, score
def transcribe(audio, language: str | None = None) -> str:
    try:
        audio_data = np.asarray(audio, dtype=np.float32)
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=-1)
        audio_data = _condition_audio(audio_data)
        if audio_data.size == 0:
            return ""
        model = get_model()
        forced = _language(language)
        if forced:
            text, score = _decode(model, audio_data, forced)
        else:
            probs = _detect(model, audio_data)
            first = max(probs, key=probs.get)
            other = "ar" if first == "en" else "en"
            text, score = _decode(model, audio_data, first)
            print(f"[asr] probs={probs} first={first} score={score:.2f}")
            if score < LOW_CONF:                      
                text2, score2 = _decode(model, audio_data, other)
                print(f"[asr] retry {other} score={score2:.2f}")
                if _rank(score2, probs[other]) > _rank(score, probs[first]):
                    text, score = text2, score2
        if _BAD_CHARS.search(text):
            print(f"[asr] rejected: {text!r}")
            return ""
        return text
    except Exception as error:
        print(f"[asr] transcription error: {error}")
    return ""