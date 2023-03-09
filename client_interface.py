
import requests
from io import BytesIO
from typing import Union

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
        self.assistant_name = ""

        self.completion_engines = {
            "engines" : [
                "text-davinci-003",
                "text-davinci-002",
                "text-davinci-001",
                "text-curie-001",
                "text-babbage-001",
                "text-ada-001",
                "davinci",
                "curie",
                "babbage",
                "ada",
                "code-davinci-002",
                "code-cushman-001",
            ],
            "function": self._prompt_completion
        }
        self.chat_engines = {
            "engines" : [
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-0301"
            ],
            "function": self._prompt_chat
        }
        # self.code_engines = [
        #     "code-davinci-002",
        #     "code-cushman-001",
        # ]

    def get_engines(self):
        return self.completion_engines["engines"] + self.chat_engines["engines"] # + self.code_engines
    

    def _text_preprocess(self, context, prompt):
        str_context = [entry["message"] for entry in context]
        
        if type(prompt) is list and len(prompt) == 1:
            str_prompt = [prompt[0]["message"]]
        elif type(prompt) is list and len(prompt) == 2:
            str_prompt = [prompt[0]["message"], prompt[1]["message"]]
        else:
            str_prompt = [prompt["message"]]

        return "\n".join(str_context + str_prompt)
    
    def _text_postprocess(self, response):
        return [resp.text for resp in response.choices]
    
    def _chat_preprocess(self, context, prompt):
        messages = [{"role": ("user" if entry["user"] != self.assistant_name else "assistant"), "content": entry["message"]} for entry in context]
        
        if type(prompt) is list and len(prompt) == 1:
            messages.append({"role": "user", "content": prompt[0]["message"]})
        elif type(prompt) is list and len(prompt) == 2:
            messages.append({"role": "user", "content": prompt[0]["message"]})
            messages.append({"role": "assistant", "content": prompt[1]["message"]})
        else:
            messages.append({"role": "user", "content": prompt["message"]})

        return messages
    
    def _chat_postprocess(self, response):
        return [resp.message.content for resp in response.choices]

    def _postprocess(self, text):
        if len(text) == 0:
            return "<|endoftext|>"
        else:
            return text
        

    def prompt_chat_gpt(self, prompt : Union[list, str], context : list = [], engine : str = "text-davinci-003", temperature : int = 0.5):
        responses = None
        if engine in self.chat_engines["engines"]:
            responses = self.chat_engines["function"](prompt, context, engine, temperature)
        else:
            responses = self.completion_engines["function"](prompt, context, engine, temperature)
        
        return self._postprocess(responses[0])

    def prompt_chat_gpt_top_k(self, prompt : Union[list, str], context : list = [], top_k : int = 1, engine : str = "text-davinci-003", temperature : int = 0.5):
        responses = None
        if engine in self.chat_engines["engines"]:
            responses = self.chat_engines["function"](prompt, context, engine, temperature, n=top_k)
        else:
            responses = self.completion_engines["function"](prompt, context, engine, temperature, n=top_k)

        return [self._postprocess(choice) for choice in responses]
    
    
    def _prompt_completion(self, prompt, context, engine, temperature, n=1):
        prompt = self._text_preprocess(context, prompt)
        responses = openai.Completion.create(
            engine=engine,
            prompt=prompt,
            max_tokens=1024,
            n=n,
            stop=None,
            temperature=temperature)
        return self._text_postprocess(responses)
    
    def _prompt_chat(self, prompt, context, engine, temperature, n=1):
        messages = self._chat_preprocess(context, prompt)
        responses = openai.ChatCompletion.create(
            model=engine,
            messages=messages,
            max_tokens=1024,
            n=n,
            stop=None,
            temperature=temperature)
        return self._chat_postprocess(responses)
    

    def prompt_dalle2(self, prompt):
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="256x256"
        )
        image_url = response['data'][0]['url']
        return image_url