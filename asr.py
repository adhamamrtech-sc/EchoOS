import os 
import json 
from faster_whisper import WhisperModel
import vosk
import numpy as np

whisper_model_size = "base"
whisper_model = WhisperModel(whisper_model_size, device = "cpu", compute_type="int8")

vosk_model_path ="model_vosk"
vosk_model = None

def get_vosk_model():
    global vosk_model
    if vosk_model is None and os.path.exists(vosk_model_path):
        vosk_model = vosk.Model(vosk_model_path)
    return vosk_model
def transcribe(audio, language=None):
    try:
        if isinstance(audio, np.ndarray):
            audio_data = audio.astype(np.float32)
        else:
            audio_data = np.array(audio, dtype=np.float32)

        segment, info = whisper_model.transcribe(audio_data, beam_size=5, language=language)
        text_result = "".join([segment.text for segment in segment]).strip()

        if text_result:
            return text_result
    except Exception as ex:
        print(f"vosk transcription error: {ex}")
    return ""
    