
import openai
from slack.web import WebClient

class ClientInterface():

    def __init__(self, slack_token):
        self.client = WebClient(slack_token)

    def send_message(self, channel, thread, text):
        response = self.client.chat_postMessage(channel=channel, 
                                       thread_ts=thread,
                                       text=text)
        
        status = response["ok"]
        print("status: ", "OK" if status else "KO")
        return status
    
class OpenaiInterface():
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key
        openai.api_key = self.openai_api_key

    def prompt_chat_gpt(self, prompt):
        response_text = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5).choices[0].text
        print("reply: ", response_text)
        return response_text