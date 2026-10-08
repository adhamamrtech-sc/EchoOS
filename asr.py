import os 
import time 
import json
import wave 
from faster_whisper import WhisperModel
import vosk

#experimental audio file
audio_file = "sample.wav"
def test_faster_whisper(audio_path):
    print("\n--- 1.test ---")
    start_time = time.time()

    #download the model(tiny=75mb) 
    model_size = "tiny"
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    load_time = time.time() - start_time
    print(f"model downloaded successfully in (tiny):{load_time:.2f} sec")

    #transcribe operation
    transcribe_start = time.time()
    segments, info = model.transcribe(audio_path, beam_size=5)
    text = "".join([segment.text for segment in segments]).strip()
    transcribe_time = time.time() - transcribe_start
    print(f"the output text: {text}")
    print(f"transcribe time: {transcribe_time}")
    return transcribe_time, text



def test_vosk(audio_path, model_path="model"):
    print("n\--- 2.vosk test ---")

    if not os.path.exists(model_path):
        print("error vosk model folder not found. please download it frist")
        return 0, ""
    start_time = time.time()
    model = vosk.Models(model_path)
    load_time = time.time() - start_time
    print(f"model downloaded in: {load_time:.2f} sec")
    wf = wave.open(audio_path, "rb")
    rec = vosk.KaldiRecognizer(model, wf.getframerate())

    transcribe_start = time.time()
    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWavefrom(data):
            res = json.loads(rec.Result())
            results.append(res.get("text", ""))
    final_res = json.loads(rec.FinalResult())
    results.append(final_res("text", ""))

    text = "".join(results).strip()
    transcribe_time = time.time() - transcribe_start

    print(f"output text: {text}")
    print(f"transcribe time: {transcribe_time:.2f} sec ")
    return transcribe_time, text

if __name__ == "__main__":
    if not os.path.exists(audio_file):
        print(f"attention: please fill an audio file with name of '{audio_file}'in the folder to start the test")
    else:
        print("=== comparison between  faster-whisper and vosk ===")
        whisper_time, whisper_text = test_faster_whisper(audio_file)
        vosk_time, vosk_text = test_vosk(audio_file)    