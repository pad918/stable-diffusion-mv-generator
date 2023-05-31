import yt_dlp
import requests
import ffmpeg
import re
import webvtt
from string import printable

print("v1112")

class YoutubeDownloader:

    def extract_text_from_vtt(self, vtt_file_path):
        pattern = r'<[^>]+>'
        
        vtt = webvtt.read(vtt_file_path)
        clean_lines = []
        for s in vtt:
            txt = s.text
            clean = re.sub(pattern, '', txt)
            
            # Remove strange invisible unicode characters
            clean = re.sub("[^{}]+".format(printable), "", clean).strip()
            clean = clean.replace("\n", " ")
            if(clean!=""):
                clean_lines.append(clean)
        clean_text = "\n".join(clean_lines)

        # Create the text file in the same folder
        with open(f"{vtt_file_path}.txt", 'w', encoding='utf-8') as f:
            f.write(clean_text)


    def download_all(self, video_url:str, destination_dir:str):
        print("STARING YOUTUBE DOWNLOADER!")
        self.download_audio   (video_url, f"{destination_dir}/audio.wav")
        self.download_captions(video_url, f"{destination_dir}/captions.vtt")
        self.extract_text_from_vtt(f"{destination_dir}/captions.vtt")

    def download_audio(self, video_url:str, destination_file_path:str):
        ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            audio_url = info_dict.get('url', None)
            if audio_url:
                ffmpeg.input(audio_url).output(destination_file_path).run()
                print('Audio downloaded successfully!')
            else:
                print('Failed to retrieve audio URL.')

    def download_captions(self, video_url:str, destination_file_path:str):
        print("DOWNLOADING CAPTIONS!")
        ydl_opts = {
            'writesubtitles': True,
            'subtitleslangs': ['en'],  # Specify the language of the captions
            'skip_download': True,  # Avoid downloading the video
            'quiet': False,  # Suppress console output
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info_dict = ydl.extract_info(video_url, download=False)
                
                subtitles = info_dict.get('subtitles', {}).get('en')

                #Sometimes the language is not called 'en', but en.xxxxxx where the x's are random characters.
                if(not subtitles):
                    all = info_dict.get('subtitles', {})
                    key = list(all.keys())[0]
                    subtitles = info_dict.get('subtitles', {}).get(key)

                if subtitles:
                    def find(predicate, lst):
                        return next((item for item in lst if predicate(item)), None)
                    
                    def download(url, file_path):
                        print(f"Downloading: \n\t{url}\n\t --->\t {file_path}")
                        vtt_response = requests.get(url)
                        vtt_response.raise_for_status()  # Check for any errors
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(vtt_response.text)
                    
                    # Find the urls of the files
                    vtt_url = find(lambda x: x['ext']=='vtt', subtitles)['url']
                    #txt_url = find(lambda x: x['ext']=='txt', subtitles)['url']

                    # Download the vtt and txt caption files
                    download(vtt_url, destination_file_path)
                    #download(txt_url, destination_file_path+'.txt')
                    

                else:
                    print("No English captions found for the video.")
            except yt_dlp.DownloadError as e:
                print(f"Error: {str(e)}")