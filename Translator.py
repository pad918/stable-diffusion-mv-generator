import openai
import os
import time

class Translator:

    def translate_sinlge(self, line) -> str:
        completion = openai.ChatCompletion.create(
        max_tokens = 150,
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"""
                Translate input from the input language to english. Keep the original formating.
                Respond only with the translated text.
                """},
                {"role": "user", "content": f"{line}"}
            ]
        )
        return completion.choices[0].message.content

    def translate_lyrics(self, lyrics):
        translated = []
        j = 1
        for line in lyrics:
            for i in range(10):
                try:
                    tr = self.translate_sinlge(line)
                    print(f"Translated\n \t:{line} \n\t---> {tr}")
                    print(f"{j}/{len(lyrics)}")
                    translated.append(tr)
                    j+=1
                    break
                except Exception as e:
                    print("Failed, retrying")
                    time.sleep(3)
        return translated
    
    def all_in_one_translation(self, lyrics):
        lyric_prompt = "\n".join(lyrics)
        completion = openai.ChatCompletion.create(
        max_tokens = 2000,
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"""
                Translate lyrics from the input language to english. Keep the original formating.
                Respond only with the translated text. Inculde all potensial duplicated lines.
                """},
                {"role": "user", "content": f"{lyric_prompt}"}
            ]
        )
        response:str = completion.choices[0].message.content
        result = response.split("\n")
        if(len(result) != len(lyrics)):
            print("FAILED TO TRANSLATE, TRYNG THE OLD TRICK")
            result = response.split("\n\n")

        if(len(result) != len(lyrics)):
            raise Exception(f"Gpt got confused {len(result)}!={len(lyrics)}")
        
        return result
        