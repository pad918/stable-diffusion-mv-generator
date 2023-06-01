from scripts.VideoGenerator import VideoGenerator
import glob
import webvtt
from datetime import datetime as dt
import datetime
import time
import os
import modules.scripts as scripts
# Repressents the simplest possible video generator.
print("aaaa")
class BasicVideoGenerator(VideoGenerator):
    
    def parse_time(self, input: str):
        tt = time.strptime(input.split('.')[0],'%H:%M:%S')
        part = input.split('.')[1]
        return datetime.timedelta(hours=tt.tm_hour,minutes=tt.tm_min,seconds=tt.tm_sec).total_seconds() + float(part)/1000.0
    
    def parse_vtt_subtitle_file(self, vtt_file_path:str):
        vtt = webvtt.read(vtt_file_path)
        timings = []
        for s in vtt:
            time = {'text': s.text, 'start': self.parse_time(s.start), 'end': self.parse_time(s.end)}
            timings.append(time)
        return timings
    
    def create_options_file(self, images_paths, timeings) -> str:
        option_file:str = ""
        for i in range(len(images_paths)):
            image_path  = images_paths[i]
            time        = timeings[i]
            is_last_img: bool = i==(len(images_paths)-1)
            is_first_img: bool = i==0
            if(not is_first_img and not is_last_img):
                duration = (timeings[i+1]['start']-time['start'])
            elif(is_first_img and is_last_img):
                print("NOPE")
            elif(is_first_img):
                duration = timeings[1]['start']
            elif(is_last_img):
                duration = 60 # Poor mans fix
            
            print(f"{i}, {image_path} duration: {duration}")
            option_file += f"file '{image_path}'\n"
            option_file += f"duration {1000.0*duration}ms\n"

        return option_file
    
    # Embedds subtitles to video by creating a copy and then removing the old file
    def embedd_subtitles(self, video_path:str, sub_path:str):
        # To avoid overwriting the source file, we add "_captioned" to the name of the new file
        root, extension = os.path.splitext(video_path)
        embedded_file_path = f"{root}_captioned{extension}" # eg a/b/c.123.mp4 ==> a/b/c_captioned.mp4
        os.system(f"""ffmpeg -i {video_path} -i {sub_path} -c copy -c:s mov_text {embedded_file_path} -shortest""")

        #Remove the original file
        os.remove(video_path)
        return

    def generate_video(self, input_directory:str):
        images_paths = sorted(glob.glob(input_directory+"/*.png", recursive=False))
        vtt_paths    = glob.glob(input_directory + "/*.vtt", recursive=False)
        audio_paths  = glob.glob(input_directory + "/*.wav", recursive=False)
        if(len(vtt_paths)!=1):
            raise Exception("DID NOT FIND 1 vtt in folder!")

        if(len(audio_paths)!=1):
            raise Exception("DID NOT FIND 1 wav file in folder!")

        timeings = self.parse_vtt_subtitle_file(vtt_paths[0])

        op = self.create_options_file(images_paths, timeings)
        with open('options.txt', 'w') as f:
                f.write(op)
        
        #Create a filename of the current time in iso 8601 (sortable)
        file_name = str(dt.now().strftime("%Y_%m_%d__%H_%M_%S"))+ ".mp4"
        output_file_path = os.path.normpath(os.path.join(scripts.basedir(), "outputs/videos"))
        output_file_path = os.path.join(output_file_path, file_name)
        print(f"Saving file {file_name} to {output_file_path}")

        #Create the video file and add the subtitles with ffmpeg
        try:
            os.system(f"""ffmpeg -f concat -safe 0 -i options.txt -i {audio_paths[0]} -vf \"settb=AVTB,fps=10,scale=-1:1080\"  -vcodec h264 -r 10 {output_file_path} -y""")
            self.embedd_subtitles(output_file_path, vtt_paths[0])
        except Exception as e:
            print("Failed to generate video file: ")
            raise