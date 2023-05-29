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
from scripts.Transcriber            import Transcriber
from scripts.WhisperTranscriber     import WhisperTranscriber
from scripts.VideoGenerator         import VideoGenerator
from scripts.BasicVideoGenerator    import BasicVideoGenerator
from scripts.PromptRefiner          import PromptRefiner


import modules.scripts as scripts
import gradio as gr

from modules import sd_samplers
from modules.processing import Processed, process_images
from modules.shared import state

BASE_PATH = f"{scripts.basedir()}"#/extensions/MUSIC-VIDEO-GENERATOR"
print(f"BASE PATH: {BASE_PATH}")

# Set the used transcriber!
transcriber: Transcriber = WhisperTranscriber(BASE_PATH)
generator: VideoGenerator = BasicVideoGenerator()
refiner: PromptRefiner = PromptRefiner()
#### END


def process_string_tag(tag):
    return tag


def process_int_tag(tag):
    return int(tag)


def process_float_tag(tag):
    return float(tag)


def process_boolean_tag(tag):
    return True if (tag == "true") else False


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


def cmdargs(line):
    args = shlex.split(line)
    pos = 0
    res = {}

    while pos < len(args):
        arg = args[pos]

        assert arg.startswith("--"), f'must start with "--": {arg}'
        assert pos+1 < len(args), f'missing argument for command line option {arg}'

        tag = arg[2:]

        if tag == "prompt" or tag == "negative_prompt":
            pos += 1
            prompt = args[pos]
            pos += 1
            while pos < len(args) and not args[pos].startswith("--"):
                prompt += " "
                prompt += args[pos]
                pos += 1
            res[tag] = prompt
            continue


        func = prompt_tags.get(tag, None)
        assert func, f'unknown commandline option: {arg}'

        val = args[pos+1]
        if tag == "sampler_name":
            val = sd_samplers.samplers_map.get(val.lower(), None)

        res[tag] = func(val)

        pos += 2

    return res


def load_prompt_file(file):
    if file is None:
        return None, gr.update(), gr.update(lines=7)
    else:
        lines = [x.strip() for x in file.decode('utf8', errors='ignore').split("\n")]
        return None, "\n".join(lines), gr.update(lines=7)

class Script(scripts.Script):
    def title(self):
        return "Generates a music video from a song file ID 17"

    def ui(self, is_img2img):
        def test_print():
            print("TEST PRINTING: ")
            return "sdfjh"

        yt_video_input = gr.Textbox(label="Get audio and subtitles from a youtube video", lines = 1, elem_id=self.elem_id("yt_video_url"))
        with gr.Row(variant="compact", elem_id="apply_button_row"):
            yt_video_apply_btn = gr.Button(value="Get audio and captions from yt video", elem_id="run_crawler_btn")
        
        yt_video_apply_btn.click(test_print)

        checkbox_gpt_refinement = gr.Checkbox(label="Let gpt refine the prompts", value=False, elem_id=self.elem_id("checkbox_gpt_refinement"))
        checkbox_translate = gr.Checkbox(label="Translate lyrics to english", value=False, elem_id=self.elem_id("checkbox_translate"))
        audio          = gr.File(label="Audio file", type='binary', elem_id=self.elem_id("audio_file"))
        prompt_txt     = gr.Textbox(label="List of prompt inputs", lines=1, elem_id=self.elem_id("prompt_txt"))
        


        audio.change(fn=transcriber.transcribe_audio_file, inputs=[audio, checkbox_translate], outputs=[prompt_txt], show_progress=False)
        # We start at one line. When the text changes, we jump to seven lines, or two lines if no \n.
        # We don't shrink back to 1, because that causes the control to ignore [enter], and it may
        # be unclear to the user that shift-enter is needed.
        prompt_txt.change(lambda tb: gr.update(lines=7) if ("\n" in tb) else gr.update(lines=2), inputs=[prompt_txt], outputs=[prompt_txt], show_progress=False)
        return [prompt_txt, checkbox_gpt_refinement, checkbox_translate, yt_video_input]

    def run(self, p, prompt_txt: str, checkbox_gpt_refinement, checkbox_translate, yt_video_input):

        print(f"GENERATING USING THE TEXT PROMPT: {prompt_txt}")
        abc = prompt_tags.get("negative_prompt")
        print(f"PROMPT: {abc}")
        lines = [x.strip() for x in prompt_txt.splitlines()]
        lines = [x for x in lines if len(x) > 0]
        

        if(checkbox_gpt_refinement):
            print("Refining prompts...")
            try:
                refiner.generate_setting(lines)
                lines = refiner.refine(lines)
                print("Gpt succeded in refining the prompts")
            except Exception as e: 
                print('Failed refine prompts: '+ str(e))
            print("done")

        p.do_not_save_grid = True

        job_count = 0
        jobs = []

        for line in lines:
            if "--" in line:
                try:
                    args = cmdargs(line)
                except Exception:
                    print(f"Error parsing line {line} as commandline:", file=sys.stderr)
                    print(traceback.format_exc(), file=sys.stderr)
                    args = {"prompt": line}
            else:
                args = {"prompt": line}

            job_count += args.get("n_iter", p.n_iter)

            jobs.append(args)

        print(f"Will process {len(lines)} lines in {job_count} jobs.")

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

        # Save in images in a temp foler
        print(f"SAVING {len(images)} images in temp folder")
        i = 0
        for elm in images:
            img: Image = elm
            file_path = f"{BASE_PATH}/temp/{str(i).zfill(5)}.png"
            img.save(file_path)
            i+=1

        # GENERATE THE VIDEO
        try:
            generator.generate_video(f"{BASE_PATH}/temp")
            # TODO delete the files in the temp folder! (EXCEPT THE VIDEO FILE!) 
        except Exception as e:
            print("Failed to generate the video: ", str(e))
        return Processed(p, images, p.seed, "", all_prompts=all_prompts, infotexts=infotexts)
    
    def get_lines_from_segments(segments):
        lines = []
        for seg in segments:
            lines.append(seg["text"] + "\n")
        return lines

