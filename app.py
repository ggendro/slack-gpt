
import argparse
import openai
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack.web import WebClient
from slack_bolt import App


# Parse tokens and API keys
parser = argparse.ArgumentParser(description = 'Start slack bot. Slack app token, slack bot token, and openai API key are required.')
parser.add_argument('--slack_app_token', type=str, required=True, help='Slack app token')
parser.add_argument('--slack_bot_token', type=str, required=True, help='Slack bot token')
parser.add_argument('--openai_api_key', type=str, required=True, help='OpenAI API key')
args = parser.parse_args()

SLACK_BOT_TOKEN = args.slack_bot_token
SLACK_APP_TOKEN = args.slack_app_token
OPENAI_API_KEY  = args.openai_api_key


# Event API & Web API
app = App(token=SLACK_BOT_TOKEN) 
client = WebClient(SLACK_BOT_TOKEN)


# This gets activated when the bot is tagged in a channel    
@app.event("app_mention")
def handle_message_events(body, logger):

    # Log message
    print("request: ", str(body["event"]["text"]).split(">")[1])
    
    # Create prompt for ChatGPT
    prompt = str(body["event"]["text"]).split(">")[1]
    
    # Let thre user know that we are busy with the request 
    response = client.chat_postMessage(channel=body["event"]["channel"], 
                                       thread_ts=body["event"]["event_ts"],
                                       text=f"Hello from your bot! :robot_face: \nThanks for your request, I'm on it!")
    print("status: ", "OK" if response["ok"] else "KO")
    
    # Check ChatGPT
    openai.api_key = OPENAI_API_KEY
    response_text = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5).choices[0].text
    print("reply: ", response_text)
    
    
    # Reply to thread 
    response = client.chat_postMessage(channel=body["event"]["channel"], 
                                       thread_ts=body["event"]["event_ts"],
                                       text=f"Here you go: \n{response_text}")
    print("status: ", "OK" if response["ok"] else "KO")



if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()