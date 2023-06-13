import datetime
import time
import ffmpeg
import glob
import webvtt
import copy
import random
import sys
import traceback
import shlex
import os
from PIL import Image
from typing import List
from scripts.Transcriber            import Transcriber
from scripts.WhisperTranscriber     import WhisperTranscriber
from scripts.VideoGenerator         import VideoGenerator
from scripts.BasicVideoGenerator    import BasicVideoGenerator
from scripts.GPTImageDescriber      import GPTImageDescriber
from scripts.PromptRefiner          import PromptRefiner
from scripts.YoutubeDownloader      import YoutubeDownloader


import modules.scripts as scripts
import gradio as gr

from modules import sd_samplers
from modules.processing import Processed, process_images
from modules.shared import state

BASE_PATH = f"{scripts.basedir()}"
print(f"BASE PATH: {BASE_PATH}")

# Set the used transcriber!
transcriber: Transcriber = WhisperTranscriber(BASE_PATH)
generator: VideoGenerator = BasicVideoGenerator()

# Create the processing stack
processing_stack: List[PromptRefiner] = []
processing_stack.append(GPTImageDescriber())

yt_scraper: YoutubeDownloader = YoutubeDownloader()

def process_string_tag(tag):
    return tag

def process_int_tag(tag):
    return int(tag)

def process_float_tag(tag):
    return float(tag)

def process_boolean_tag(tag):
    return True if (tag == "true") else False

def get_captions_from_file():
    text_files = glob.glob(BASE_PATH+"/temp/*.txt", recursive=False)
    if(len(text_files)!=1):
        raise Exception(f"Found {len(text_files)} txt file(s) in {BASE_PATH}/temp/*.txt, expected 1")
    with open(text_files[0], encoding="utf8") as f:
        lines = f.readlines()
    return " ".join(lines)

prompt_tags = {
    "sd_model": None,
    "outpath_samples": process_string_tag,
    "outpath_grids": process_string_tag,
    "prompt_for_display": process_string_tag,
    "prompt": process_string_tag,
    "negative_prompt": process_string_tag,
    "styles": process_string_tag,
    "seed": process_int_tag,
    "subseed_strength": process_float_tag,
    "subseed": process_int_tag,
    "seed_resize_from_h": process_int_tag,
    "seed_resize_from_w": process_int_tag,
    "sampler_index": process_int_tag,
    "sampler_name": process_string_tag,
    "batch_size": process_int_tag,
    "n_iter": process_int_tag,
    "steps": process_int_tag,
    "cfg_scale": process_float_tag,
    "width": process_int_tag,
    "height": process_int_tag,
    "restore_faces": process_boolean_tag,
    "tiling": process_boolean_tag,
    "do_not_save_samples": process_boolean_tag,
    "do_not_save_grid": process_boolean_tag
}

def wipe_directory(directory_path: str):
    # Check if the directory exists
    if not os.path.isdir(directory_path):
        print(f"Directory '{directory_path}' does not exist.")
        return
    
    def is_important_file(path):
        importaint_files = ['.py', '.mov', '.mp4', '.exe', '.dll']
        _, extension = os.path.splitext(path)
        return extension in importaint_files
    
    # Iterate over all files in the directory
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        
        # Do not remove important files
        if(is_important_file(file_path)):
            continue

        # Check if the current path is a file
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"Successfully removed file: {file_path}")
            except Exception as e:
                print(f"Error occurred while removing file: {file_path}")
                print(f"Error message: {str(e)}")


class Script(scripts.Script):
    def title(self):
        return "Generates a music video from a song file"

    def transcribe_and_update(self, audio: str, translate: bool, prompt_txt):
        transcriber.transcribe_audio_file(audio, translate)
        return get_captions_from_file()
        

    def ui(self, is_img2img):
        
        def update_value(url):
            self.yt_url = url
            return url
        def scrape_video():
            try:
                self.yt_url
            except:
                raise Exception(f"No youtube video selected!")
            print(f"URL: {self.yt_url}")
            yt_scraper.download_all(self.yt_url, f"{BASE_PATH}/temp")
            return get_captions_from_file()

        yt_video_input: gr.Textbox = gr.Textbox(label="Get audio and subtitles from a youtube video", lines = 1, elem_id=self.elem_id("yt_video_url"))

        with gr.Row(variant="compact", elem_id="apply_button_row"):
            yt_video_apply_btn = gr.Button(value="Get audio and captions from yt video", elem_id="run_crawler_btn")
        
        

        checkbox_gpt_refinement = gr.Checkbox(label="Let gpt refine the prompts", value=True, elem_id=self.elem_id("checkbox_gpt_refinement"))
        checkbox_translate = gr.Checkbox(label="Translate lyrics to english", value=False, elem_id=self.elem_id("checkbox_translate"))
        audio           = gr.File(label="Audio file", type='binary', elem_id=self.elem_id("audio_file"))
        prompt_txt      = gr.Textbox(label="Lyrics used for generation", lines=1, elem_id=self.elem_id("prompt_txt"))
        gpt_context_txt = gr.Textbox(label="Additional gpt context for image generation", lines=4, elem_id=self.elem_id("gpt_context_txt"))
        
        
        yt_video_apply_btn.click(scrape_video, inputs=[], outputs=[prompt_txt])
        audio.change(fn=self.transcribe_and_update, inputs=[audio, checkbox_translate, prompt_txt], outputs=[prompt_txt], show_progress=False)
        
        prompt_txt.change(lambda tb: gr.update(lines=7) if ("\n" in tb) else gr.update(lines=2), inputs=[prompt_txt], outputs=[prompt_txt], show_progress=False)
        gpt_context_txt.change(lambda tb: gr.update(lines=7) if ("\n" in tb) else gr.update(lines=4), inputs=[gpt_context_txt], outputs=[gpt_context_txt], show_progress=False)
        
        yt_video_input.change(lambda tb: update_value(str(tb)), inputs=[yt_video_input], outputs=[yt_video_input], show_progress=False)
        return [prompt_txt, checkbox_gpt_refinement, checkbox_translate, yt_video_input, gpt_context_txt]

    def run(self, p, prompt_txt: str, checkbox_gpt_refinement, checkbox_translate, yt_video_input, gpt_context_txt):
        options = {
            'checkbox_gpt_refinement': checkbox_gpt_refinement,
            'gpt_context': gpt_context_txt
            }
        
        print(f"GENERATING USING THE TEXT PROMPT: \n{p.prompt}\n\n and description: {prompt_txt}")
        print(f"And additional context: {gpt_context_txt}")
        abc = prompt_tags.get("negative_prompt")
        print(f"PROMPT: {abc}")
        lines = [x.strip() for x in prompt_txt.splitlines()]
        lines = [x for x in lines if len(x) > 0]
        
        # Convert the lyrics into images by running them through
        # a number of refiners
        try:
            for refiner in processing_stack:
                lines = refiner.refine(lines, options)
            # TODO Insert p.prompt in the beginning of all lines.
            for i in range(len(lines)):
                lines[i] = f"{p.prompt}, {lines[i]}" 
        except Exception as e:
            print("Failed to refine the pompts: " + str(e))
            raise

        p.do_not_save_grid = True

        job_count = 0
        jobs = []

        for line in lines:
            
            args = {"prompt": line}

            job_count += args.get("n_iter", p.n_iter)

            jobs.append(args)

        print(f"Will process {len(lines)} images in {job_count} jobs.")

        state.job_count = job_count

        images = []
        all_prompts = []
        infotexts = []
        for args in jobs:
            state.job = f"{state.job_no + 1} out of {state.job_count}"

            copy_p = copy.copy(p)
            for k, v in args.items():
                setattr(copy_p, k, v)

            proc = process_images(copy_p)
            images += proc.images

            all_prompts += proc.all_prompts
            infotexts += proc.infotexts

        # Save images in a temp foler
        print(f"SAVING {len(images)} images in temp folder")
        i = 0
        for elm in images:
            img: Image = elm
            file_path = f"{BASE_PATH}/temp/{str(i).zfill(5)}.png"
            img.save(file_path)
            i+=1

        # GENERATE THE VIDEO
        try:
            temp_folder:str = f"{BASE_PATH}/temp"
            generator.generate_video(temp_folder)
            wipe_directory(temp_folder)
            
        except Exception as e:
            print("Failed to generate the video: ", str(e))
        return Processed(p, images, p.seed, "", all_prompts=all_prompts, infotexts=infotexts)

