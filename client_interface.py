
import requests
from io import BytesIO
import openai
from slack.web import WebClient


class ClientInterface():

    def __init__(self, slack_token):
        self.client = WebClient(slack_token)

    def get_id(self):
        return self.client.auth_test()["user_id"]

    def send_message(self, channel, thread, text, attachments=None):
        response = self.client.chat_postMessage(channel=channel, 
                                       thread_ts=thread,
                                       text=text,
                                       attachments=attachments)
        
        status = response["ok"]
        print("status: ", "OK" if status else "KO")
        return status
    
    def send_image(self, channel, thread, image_url):
        response = requests.get(image_url)
        image_data = BytesIO(response.content)
        response = self.client.files_upload(channels=channel, 
                                            thread_ts=thread,
                                            file=image_data)
        
        status = response["ok"]
        print("status: ", "OK" if status else "KO")
        return status
    
class OpenaiInterface():
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key
        openai.api_key = self.openai_api_key

    def postprocess(self, text):
        if len(text) == 0:
            return "<|endoftext|>"
        else:
            return text

    def prompt_chat_gpt(self, prompt, engine="text-davinci-003", temperature=0.5):
        response_text = openai.Completion.create(
            engine=engine,
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=temperature)
        response_text = response_text.choices[0].text
        return self.postprocess(response_text)

    def prompt_chat_gpt_top_k(self, prompt, top_k=1, engine="text-davinci-003", temperature=0.5):
        response_choices = openai.Completion.create(
            engine=engine,
            prompt=prompt,
            max_tokens=1024,
            n=top_k,
            stop=None,
            temperature=temperature).choices
        
        return [self.postprocess(choice.text) for choice in response_choices]
    
    def prompt_dalle2(self, prompt):
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="256x256"
        )
        image_url = response['data'][0]['url']
        return image_url