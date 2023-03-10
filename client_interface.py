
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

        self.engines = {
            "completion" : {
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
                ],
                "function": self._prompt_completion
            },
            "chat" : {
                "engines" : [
                    "gpt-3.5-turbo",
                    "gpt-3.5-turbo-0301"
                ],
                "function": self._prompt_chat
            },
            "code" : {
                "engines" : [
                    "code-davinci-002",
                    "code-cushman-001",
                ],
                "function": self._prompt_completion
            }
        }
        self.engine_sizes = {
            "text-davinci-003" : 4097,
            "text-davinci-002" : 4097,
            "text-davinci-001" : 2049,
            "text-curie-001" : 2049,
            "text-babbage-001" : 2049,
            "text-ada-001" : 2049,
            "davinci" : 2049,
            "curie" : 2049,
            "babbage" : 2049,
            "ada" : 2049,
            "gpt-3.5-turbo" : 4096,
            "gpt-3.5-turbo-0301" : 4096,
            "code-davinci-002" : 8001,
            "code-cushman-001" : 2048,
        }

    def get_engines(self):
        return [engine for mode in self.engines.values() for engine in mode["engines"]]
    
    def get_engine_func(self, engine):
        for mode in self.engines.values():
            if engine in mode["engines"]:
                return mode["function"]
        return None
    
    def get_engine_token_size(self, engine):
        return self.engine_sizes[engine]

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
        

    def prompt_chat_gpt(self, prompt : Union[list, str], context : list = [], engine : str = "text-davinci-003", temperature : int = 0.5, max_tokens=1024):
        responses = self.get_engine_func(engine)(prompt, context, engine, temperature, max_tokens)       
        return self._postprocess(responses[0])

    def prompt_chat_gpt_top_k(self, prompt : Union[list, str], context : list = [], top_k : int = 1, engine : str = "text-davinci-003", temperature : int = 0.5, max_tokens=1024):
        responses = self.get_engine_func(engine)(prompt, context, engine, temperature, max_tokens, n=top_k)
        return [self._postprocess(choice) for choice in responses]
    
    
    def _prompt_completion(self, prompt, context, engine, temperature, max_tokens, n=1):
        prompt = self._text_preprocess(context, prompt)
        responses = openai.Completion.create(
            engine=engine,
            prompt=prompt,
            max_tokens=max_tokens,
            n=n,
            stop=None,
            temperature=temperature)
        return self._text_postprocess(responses)
    
    def _prompt_chat(self, prompt, context, engine, temperature, max_tokens, n=1):
        messages = self._chat_preprocess(context, prompt)
        responses = openai.ChatCompletion.create(
            model=engine,
            messages=messages,
            max_tokens=max_tokens,
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