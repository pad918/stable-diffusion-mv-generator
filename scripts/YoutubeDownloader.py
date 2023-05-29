import yt_dlp
import requests
import ffmpeg

print("v1111")

class YoutubeDownloader:

    def download_all(self, video_url:str, destination_dir:str):
        self.download_audio   (video_url, f"{destination_dir}/audio.wav")
        self.download_captions(video_url, f"{destination_dir}/captions.vtt")

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

                if subtitles:
                    # find vtt file
                    def find(predicate, lst):
                        return next((item for item in lst if predicate(item)), None)
                    vtt_url = find(lambda x: x['ext']=='vtt', subtitles)['url']
                    response = requests.get(vtt_url)
                    response.raise_for_status()  # Check for any errors
                    with open(destination_file_path, 'w', encoding='utf-8') as f:
                        f.write(response.text)

                else:
                    print("No English captions found for the video.")
            except yt_dlp.DownloadError as e:
                print(f"Error: {str(e)}")