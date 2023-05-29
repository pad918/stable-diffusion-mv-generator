import openai
import os
import time

class PromptRefiner:
    def __self__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.setting = ""
    def generate_setting(self, prompts):
        combined_lines:str = '\n\n'.join(prompts)
        completion = openai.ChatCompletion.create(
        max_tokens = 300,
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"""
                Create a short senario from the given lyrics,make up relevant part of the story.  \nLyrics:\n{combined_lines}
                """}
            ]   
        )
        result:str = completion.choices[0].message.content
        self.setting = result
        print(f"Using setting: \n{result}")

    def refine_lyric(self, line):
        completion = openai.ChatCompletion.create(
        max_tokens = 150,
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"""
                You are an artist that creates images for lines of lyrics in songs.
                Images are created by describing the images contents in detail by using keywords. 
                The image descriptions will be put into an AI that generates images from descriptions.
                Here are two examples of good descriptions:
                
                1. houses in front, houses background, straight houses, digital art, smooth, sharp focus, gravity falls style, doraemon style, shinchan style, anime style  
                2. cute girl, crop-top, blond hair, black glasses, stretching, with background by greg rutkowski makoto shinkai kyoto animation key art feminine mid shot

                The images form a story together. The story of the song is as follows: \n{self.setting}

                Describe the image for the following line of lyrics:
                {line}
                """}
            ]
        )
        result:str = completion.choices[0].message.content
        print(f"Generated: {result}")
        return result
    

    def refine(self, prompts):
        if(self.setting == ""):
            raise Exception("No setting given!")
        refined = []
        j = 1
        for line in prompts:
            for i in range(10):
                try:
                    ref = self.refine_lyric(line)
                    refined.append(ref)
                    print(f"Generated {j}/{len(prompts)}")
                    j+=1
                    break
                except Exception:
                    print("Failed to generate, retrying")
                    time.sleep(5)
            


        return refined