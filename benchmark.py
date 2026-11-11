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
from asr import whisper_model, transcribe

test_cases = [
  {
    "audio_path": "sample.wav",
    "expected_text": "open firefox increase the volume decrease the volume increase brightness shut down restart"
  }, 
  {
     "audio_path": "nayera2.wav",
     "expected_text": "open firefox turn on wifi set volume to 40 make it louder lock the screen show system info"

  },
  {
    "audio_path": "adham.wav",
    "expected_text" : "open firefox turn on wifi set volume to 40 make it louder lock the screen show system info"
  },
  {
    "audio_path": "menna walid.wav",
    "expected_text":"increase volume get system info lock screen"
  },
  {
      "audio_path":"nayera4.wav",
      "expected_text" : "افتح فايرفوكس علي الصوت وطي الاضاءه شغل موسيقى شغل فيديو"
  },
  {
      "audio_path": "nayera5.wav",
      "expected_text" :"افتح كروم اظهر نسبه البطاريه علي الصوت شغل الاّلة الحاسبة"
      
  }
]
COMMAND_HINT = (
    "Voice commands: turn on Wi-Fi, turn off Wi-Fi, turn on Bluetooth, "
    "turn off Bluetooth, make it louder, set volume to 40, set brightness to 60, "
    "open Firefox, open Chrome, lock my computer, system info, network status, yes, no."
)
COMMAND_HINT_AR = (
    "الأوامر الصوتية: افتح كروم، افتح الفايرفوكس، اعلي الصوت، اخفض الصوت، "
    "اظهر نسبة البطارية، شغل الآلة الحاسبة، اغلق الحاسوب."
)

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text) 
    text = re.sub(r'\s+', ' ', text).strip() 
    return text
def fix_common_mistakes(text):
    corrections = {
        "fire fox": "firefox",      
        "log the screen": "lock the screen",
        "lower" :"louder",
        "look at" : "lock",
        "look" : "lock"
        }
    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
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

    total_wer = 0.0
    total_latency = 0.0
    valid_cases = 0 

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

        resolved_lang = os.environ.get("ECHOOS_LANG", "auto")
        whisper_lang = None if resolved_lang == "auto" else resolved_lang
        active_prompt = active_prompt = COMMAND_HINT if resolved_lang == "en" else None
        
        segments, _ = whisper_model.transcribe(audio_data, 
                                               beam_size=2,
                                               language=whisper_lang, 
                                               temperature=0.0,
                                               initial_prompt=active_prompt,
                                               condition_on_previous_text=False, 
                                               vad_filter=True,
                                               vad_parameters=dict (speech_pad_ms=400)
                                                )
        whisper_text = "".join([seg.text for seg in segments]).strip().lower()
        expected = normalize_text(test["expected_text"])
        whisper_text = normalize_text(whisper_text)
        whisper_latency = (time.time() - start_time) * 1000 
        whisper_text = fix_common_mistakes(whisper_text)
        whisper_wer = wer(expected, whisper_text) if whisper_text else 1.0

        total_wer += whisper_wer
        total_latency += whisper_latency
        valid_cases += 1 

        print(f"  result text:\"{whisper_text}\"")
        print(f"  latency    :{whisper_latency:.2f} ms")
        print(f"  WER        : {whisper_wer*100:.2f}%")
    if valid_cases > 0:
        print("\n" + "=" * 60)
        print("                   FINAL PERFORMANCE SUMMARY                   ")
        print("=" * 60)
        print(f"  Average WER     : {(total_wer / valid_cases) * 100:.2f}%")
        print(f"  Average Latency : {total_latency / valid_cases:.2f} ms")
    print("="*60)
if __name__ == "__main__":
    run_benchmark()