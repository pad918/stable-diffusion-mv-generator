import gradio as gr
class Transcriber:
    # Creates all transcription files in folder and returns transcription, as
    # list of captions
    def transcribe_audio_file(audio_file: gr.File, translate:bool = False) -> str:
        return