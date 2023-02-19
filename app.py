
import argparse
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt import App

from bot import SlackBot
from client_interface import ClientInterface, OpenaiInterface


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
client = ClientInterface(SLACK_BOT_TOKEN)
openai_client = OpenaiInterface(OPENAI_API_KEY)

# Bot class
bot = SlackBot(client, openai_client)


# This gets activated when the bot is tagged in a channel    
@app.event("app_mention")
def handle_message_events(body, logger):
    channel = body["event"]["channel"]
    thread = body["event"]["ts"] if "thread_ts" not in body["event"] else body["event"]["thread_ts"]
    message = str(body["event"]["text"]).split(">")[1]
    
    bot.receive_message(channel, thread, message)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()