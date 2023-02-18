import os
from typing import Any

import openai
from aws_lambda_powertools.logging import Logger, correlation_paths
from slack_bolt import Ack, App, Say
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from keys import BOT_OAUTH_TOKEN, OPENAI_API_KEY, SIGNING_SECRET

logger = Logger("slack-gpt-bot", level=os.environ.get("LOG_LEVEL", "INFO"))
app = App(
    token=BOT_OAUTH_TOKEN,
    name="slack-gpt-bot-app",
    signing_secret=SIGNING_SECRET,
    logger=logger,
    process_before_response=True,
)


# This gets activated when the bot is tagged in a channel
def handle_mention(payload: dict[str, Any], say: Say):
    # Log message
    logger.info("request: %s", payload["text"])

    # Create prompt for ChatGPT
    prompt = str(payload["text"]).split(">")[1]

    # Let thre user know that we are busy with the request
    response = app.client.chat_postEphemeral(
        text=f"Hello from your bot! :robot_face: \nThanks for your request, I'm on it!",
        thread_ts=payload["event_ts"],
        user=payload["user"],
        channel=payload["channel"],
    )
    logger.info("status: %s", "OK" if response["ok"] else "KO")

    # Check ChatGPT
    openai.api_key = OPENAI_API_KEY
    response_text = (
        openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5,
        )
        .choices[0]
        .text
    )
    logger.info("reply: %s", response_text)

    # Reply to thread
    response = say(f"Here you go: \n{response_text}", thread_ts=payload["event_ts"])
    logger.info("status: %s", "OK" if response["ok"] else "KO")


def ack_to_slack(ack: Ack):
    ack()


app.event("app_mention")(ack=ack_to_slack, lazy=[handle_mention])


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL, log_event=True
)
def lambda_handler(event, context):
    return SlackRequestHandler(app).handle(event, context)
