from scripts.VideoGenerator import VideoGenerator
import glob
import webvtt
import datetime
import time
import os

# Repressents the simplest possible video generator.

class BasicVideoGenerator(VideoGenerator):
    def parse_time(self, input: str):
        tt = time.strptime(input.split('.')[0],'%H:%M:%S')
        part = input.split('.')[1]
        return datetime.timedelta(hours=tt.tm_hour,minutes=tt.tm_min,seconds=tt.tm_sec).total_seconds() + float(part)/1000.0
    def parse_vtt_subtitle(self, vtt_file_path):
        vtt = webvtt.read(vtt_file_path)
        timings = []
        for s in vtt:
            time = {'text': s.text, 'start': self.parse_time(s.start), 'end': self.parse_time(s.end)}
            timings.append(time)
        return timings
    def create_options_file(self, images_paths, timeings):
        option_file = ""
        for i in range(len(images_paths)):
            image_path  = images_paths[i]
            time        = timeings[i]
            duration = time['end']-time['start'] if i==len(images_paths)-1 else (timeings[i+1]['start']-time['start'])
            if(i==0 and len(image_path)>1):
                duration = timeings[1]['start']
            print(f"{i}, {image_path} duration: {duration}")
            option_file += f"file '{image_path}'\n"
            option_file += f"duration {1000.0*duration}ms\n"
        #option_file += f"{audio_paths[0]}\n"
        return option_file
    
    def generate_video(self, input_directory:str):
        images_paths = sorted(glob.glob(input_directory+"/*.png", recursive=False))
        vtt_paths    = glob.glob(input_directory + "/*.vtt", recursive=False)
        audio_paths  = glob.glob(input_directory + "/*.wav", recursive=False)
        if(len(vtt_paths)!=1):
            raise Exception("DID NOT FIND 1 vtt in folder!")

        if(len(audio_paths)!=1):
            raise Exception("DID NOT FIND 1 wav file in folder!")

        print("PARSING VTT")
        timeings = self.parse_vtt_subtitle(vtt_paths[0])
        print("SUCCESS!")

        op = self.create_options_file(images_paths, timeings)
        with open('options.txt', 'w') as f:
                f.write(op)

        print("USING FFMPEG COMMAND!!!")
        os.system(f"""ffmpeg -f concat -safe 0 -i options.txt -i {audio_paths[0]} -vf \"settb=AVTB,fps=10\" -vcodec png -r 10 {input_directory}/output.mp4 -y""")