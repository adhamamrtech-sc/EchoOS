from audio import record 
from asr import transcribe 
import numpy as np 

#voice reception from audio module
print("recording ....")
audio_data= record(3)

# is it 16hz mono or not?
print("audio type:", f"{type(audio_data)}")
if isinstance(audio_data, np.ndarray):
    print("input is a numpy array")

#transcribe() output
result_text = transcribe(audio_data)
print("text type:" ,f"{type(result_text)}")
print("transcription result:", f"'{result_text}'")
if isinstance(result_text, str):
    print("text string is acceptable")
else:
    print("text string not acceptable")