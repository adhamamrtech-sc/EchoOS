"""
benchmark script for ASR models(faster_whisper vs vosk)
owner: ASR engineer
"""
import time 
import os
import re
import numpy as np 
from jiwer import wer 
import wave 
import vosk
import json
from asr import whisper_model, get_vosk_model, transcribe

test_cases = [
  {
    "audio_path": "sample.wav",
    "expected_text": "open fire fox, increase the volume, decrease the volume, increase the brightness, shut down, restart."
  }, 
  {
     "audio_path": "nayera2.wav",
     "expected_text": "open firefox, turn on wifi, set volume to 40, make it louder, lock the screen, show system info"

  },
  {
    "audio_path": "adham.wav",
    "expected_text" : "open firefox, turn on wifi, set volume to 40, make it louder, lock the screen, show system info"

      
  }
]

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text) 
    text = re.sub(r'\s+', ' ', text).strip() 
    return text

def load_audio_file(file_path):
    with wave.open(file_path, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        audio_int16 = np.frombuffer(frames, dtype=np.int16)
        audio_float32= audio_int16.astype(np.float32)/ 32768.0
        return audio_float32
def run_benchmark():
    print("="*60)
    print("       ASR MODEL BENCHMARK REPORT (ACCURACY & LATENCY)         ")
    print("="*60)

    for i, test in enumerate(test_cases, 1):
        audio_path = test["audio_path"]
        expected = test["expected_text"].strip().lower()

        print(f"\n--- test case #{i}: [{audio_path}] ---")
        print(f"Expected Text :\"{expected}\"")
        try:
            audio_data = load_audio_file(audio_path)
        except Exception as e:
            print(f"error loading {audio_path}: {e}")
            continue
        start_time = time.time()
        segments, _ = whisper_model.transcribe(audio_data, beam_size=5, language="en", temperature=0.0)
        whisper_text = "".join([seg.text for seg in segments]).strip().lower()
        expected = normalize_text(test["expected_text"])
        whisper_text = normalize_text(whisper_text)
        whisper_latency = (time.time() - start_time) * 1000 
        whisper_wer = wer(expected, whisper_text) if whisper_text else 1.0

        print("\n [Model: faster_whisper]")
        print(f"  result text:\"{whisper_text}\"")
        print(f"  latency    :{whisper_latency:2f} ms")
        print(f"  WER        : {whisper_wer*100:.2f}%")


        vosk_model = get_vosk_model()
        re = None 
        if get_vosk_model is not None and re is not None:
            start_time = time.time()
            audio_int16 = (audio_data * 32767).astype(np.int16).tobytes()
            
            
            rec.AcceptWaveform(audio_int16)
            res = json.loads(re.Result())
            vosk_text = res.get("text", "").strip().lower()
            vosk_latency = (time.time()- start_time)*1000
            vosk_wer = wer(expected, vosk_text) if vosk_text else 1.0

            print("\n [Model: vosk]")              
            print(f"  result text:\"{vosk_text}\"")
            print(f"  latency    :{vosk_latency:2f} ms")
            print(f"  WER        : {vosk_wer*100:.2f}%")
        else:
            print("\n[model: vosk]  --> skipped (model path not found)")
    print("="*60)
if __name__ == "__main__":
    run_benchmark()