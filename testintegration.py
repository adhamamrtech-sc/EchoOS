from audio import record 
from asr import transcribe
import numpy as np

def test_live_pipeline():
    print("---- test live pipeline for asr and voice ---")
    print("please speak now,note that we recording only 5 seconds!")

    #recording real voice 
    audio_array = record(5)
    if audio_array is not None and len(audio_array)>0 :
        print("recorded successfully, transcribing....")
        text = transcribe(audio_array)
        print(f"transcribtion: '{text}'")
    else:
        print("no voice recorded, please try again")

if __name__ == "__main__":
    test_live_pipeline()
