from audio import record
import scipy.io.wavfile as wav
import numpy as np
import sys 
def record_test_command():

    print("please write your name :) :", end="", flush=True)
    name = sys.stdin.readline().strip()
    if not name:
       name = "test_user"

    filename = f"{name}.wav"
    print("now we're recording 10 seconds, speak now!")

    audio_data = record(10)
    if audio_data is not None:
      #turn it into .WAV
      audio_int16 = (audio_data*32767).astype('int16')
      wav.write(filename, 16000, audio_int16)
      print(f"file successfully saved as '{filename}'")
    else:
       print("warning: there is no voice has been captured, make sure that the mic is recording !")
if __name__ == "__main__":
    record_test_command()