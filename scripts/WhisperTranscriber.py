from scripts.Transcriber import Transcriber
import gradio as gr
import os
import glob
from scripts.Translator import Translator
# OBS Should use pyhton binding, not system command!

class WhisperTranscriber(Transcriber):
    
    def __init__(self, base_path):
        self.BASE_PATH = base_path
        self.translator: Translator = Translator()
    def transcribe_audio_file(self, audio_file: gr.File, translate:bool = False) -> str:
        TEMP_FILE_NAME = f"{self.BASE_PATH}/temp/test.wav"
        with open(TEMP_FILE_NAME, "wb") as binary_file:
            # Write bytes to file
            binary_file.write(audio_file)
        # SHOULD BE DONE WITH PYTHON BINDING, BUY MY ENVIRONMENT IS BROKEN AT THE MOMENT
        print(f"Transcribing audio file: {TEMP_FILE_NAME}")
        os.system(f"""whisper {TEMP_FILE_NAME} --model medium --output_dir {f"{self.BASE_PATH}/temp"}""")
        text_files = glob.glob(self.BASE_PATH+"/temp/*.txt", recursive=False)
        if(len(text_files)!=1):
            raise Exception("Did not find 1 txt file in temp dir, transcription must have failed")
        with open(text_files[0], encoding="utf8") as f:
            lines = f.readlines()
        text = ""
        if(translate):
            try:
                lines = self.translator.translate_lyrics(lines)
                tmp = "\n".join(lines)
                print(f"Translated lyrics into: {tmp}")
            except Exception as e:
                print("Failed to translate the lyrics: " + str(e))
        for line in lines:
            text += line
        return text