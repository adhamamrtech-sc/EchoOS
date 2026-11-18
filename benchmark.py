"""
benchmark script for ASR models(faster_whisper vs vosk)
owner: ASR engineer
"""
from __future__ import annotations
import difflib
import re
import statistics
import time
import unicodedata
import wave
from typing import Optional
import numpy as np
import asr  

test_cases = [
  {
    "audio_path": "sample.wav",
    "expected_text": "open firefox increase the volume decrease the volume increase brightness shutdown restart",
    "language" : "auto"
  }, 
  {
     "audio_path": "nayera2.wav",
     "expected_text": "open chrome what time is it now set brightness to 35 turn on camera",
     "language" : "auto"

  },
  {
    "audio_path": "adham.wav",
    "expected_text" : "open firefox turn on wifi set volume to 40 make it louder lock the screen show system info",
    "language" : "auto"
  },
  {
    "audio_path": "menna walid.wav",
    "expected_text":"increase volume get system info lock screen",
    "language" : "auto"
  },
  {
      "audio_path":"nayera4.wav",
      "expected_text" : "ما هو الطقس اليوم اظهر نسبه البطاريه شغل مشغل الموسيقى افتح الاله الحاسبه",
      "language" : "auto"
  },
  {
      "audio_path": "nayera5.wav",
      "expected_text" :"اغلق الجهاز اعد تشغيل الجهاز ارفع الصوت اخفض مستوى السطوع",
      "language" : "auto"

      
  },
]

TARGET_SR = 16_000
# Text normalization
# Arabic harakat (fathatan..sukun, superscript alef) and tatweel
AR_ORTHOGRAPHY = str.maketrans({
    "آ": "ا", "أ": "ا", "إ": "ا", "ٱ": "ا",  # توحيد الألفات
    "ى": "ي", "ئ": "ي",                      # توحيد الياء
    "ؤ": "و",                                # توحيد الواو
    "ة": "ه",                                # توحيد التاء المربوطة
    "ـ": "",                                 # إزالة التطويل
})
_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Universal, language-agnostic text normalization using Unicode categories."""
    if not text:
        return ""

    text = unicodedata.normalize("NFD", unicodedata.normalize("NFKC", text))

    cleaned_chars = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in ("Mn", "Cf"):
            continue
        if cat[0] in ("P", "S"):
            cleaned_chars.append(" ")
        else:
            cleaned_chars.append(ch)

    text = "".join(cleaned_chars)
    text = text.casefold().translate(AR_ORTHOGRAPHY)

    return _WHITESPACE.sub(" ", text).strip()


def align_compound_words(reference: str, hypothesis: str) -> tuple[str, str]:
    """Generic rule: merges split words (e.g. 'wi fi' -> 'wifi') if the joined form exists in the counterpart."""
    ref_words, hyp_words = set(reference.split()), set(hypothesis.split())

    for w1, w2 in zip(hypothesis.split(), hypothesis.split()[1:]):
        if f"{w1}{w2}" in ref_words:
            hypothesis = re.sub(rf"\b{re.escape(w1)}\s+{re.escape(w2)}\b", f"{w1}{w2}", hypothesis)

    for w1, w2 in zip(reference.split(), reference.split()[1:]):
        if f"{w1}{w2}" in hyp_words:
            reference = re.sub(rf"\b{re.escape(w1)}\s+{re.escape(w2)}\b", f"{w1}{w2}", reference)

    return reference, hypothesis

def clean(text: str) -> str:
    return normalize_text(text)

# WER (word-level Levenshtein, single-row DP)
def wer(reference: str, hypothesis: str) -> float:
    """Return WER in percent. Inputs must already be normalized."""
    ref, hyp = reference.split(), hypothesis.split()
    if not ref:
        return 0.0 if not hyp else 100.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(
                prev[j] + 1,                 # deletion
                cur[j - 1] + 1,              # insertion
                prev[j - 1] + (r != h),      # substitution
            )
        prev = cur
    return 100.0 * prev[-1] / len(ref)

# Audio loading (minimal overhead: wave + numpy only)
def load_wav_float32(path: str) -> np.ndarray:
    """Load a PCM WAV into a mono 16 kHz float32 array in [-1, 1]."""
    with wave.open(path, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    if sampwidth == 2:
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        audio = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sampwidth == 1:
        audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"Unsupported sample width ({sampwidth} bytes) in {path}")

    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    if sr != TARGET_SR:  # linear resample fallback; prefer recording at 16 kHz
        n_out = int(round(len(audio) * TARGET_SR / sr))
        audio = np.interp(
            np.linspace(0.0, len(audio) - 1, n_out, dtype=np.float64),
            np.arange(len(audio), dtype=np.float64),
            audio,
        ).astype(np.float32)
    return np.ascontiguousarray(audio, dtype=np.float32)

# Transcription
def transcribe(audio: np.ndarray, language: str) -> tuple[str, float]:
    """Transcribe via asr.py and return (raw_text, latency_ms)."""
    start = time.perf_counter()
    text = asr.transcribe(audio, language=language)
    latency_ms = (time.perf_counter() - start) * 1000.0
    return text, latency_ms


def warm_up() -> None:
    """One dummy decode so lazy init / memory allocation is not billed to case #1."""
    silence = np.zeros(TARGET_SR, dtype=np.float32)
    asr.transcribe(silence, language="en")

# Main
def main() -> None:
    print("Warming up model...")
    warm_up()

    wers: list[float] = []
    latencies: list[float] = []
    sep = "=" * 72

    print(f"\n{sep}\n ASR BENCHMARK  |  faster-whisper  |  CPU int8\n{sep}")

    for idx, case in enumerate(test_cases, 1):
        path, expected, language = case["audio_path"], case["expected_text"], case["language"]
        print(f"\n[{idx}/{len(test_cases)}] {path}  (lang={language})")

        try:
            audio = load_wav_float32(path)       # loading is excluded from latency
            raw_text, latency_ms = transcribe(audio, language)
        except Exception as exc:  # keep the benchmark running on bad files
            print(f"  ERROR: {type(exc).__name__}: {exc}")
            continue

        result_text = clean(raw_text)
        expected_clean = normalize_text(expected)
        expected_clean, result_text = align_compound_words(expected_clean, result_text)
        case_wer = wer(expected_clean, result_text)

        wers.append(case_wer)
        latencies.append(latency_ms)

        print(f"  Expected Text : {expected_clean}")
        print(f"  Result Text   : {result_text}")
        if expected_clean != result_text:
            exp_words = expected_clean.split()
            res_words = result_text.split()
        print(f"  Latency       : {latency_ms:,.1f} ms")
        print(f"  WER           : {case_wer:.2f} %")

    print(f"\n{sep}\n PERFORMANCE SUMMARY\n{sep}")
    if wers:
        print(f"  Cases evaluated : {len(wers)} / {len(test_cases)}")
        print(f"  Average WER     : {statistics.mean(wers):.2f} %")
        print(f"  Average Latency : {statistics.mean(latencies):,.1f} ms")
        print(f"  Min / Max Lat.  : {min(latencies):,.1f} / {max(latencies):,.1f} ms")
    else:
        print("  No cases were evaluated successfully.")
    print(sep)


if __name__ == "__main__":
    main()
