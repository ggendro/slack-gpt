import re
from typing import Any

from aws_lambda_powertools.logging import Logger
from slack_bolt import App, Say
from slack_sdk import WebClient

from constants import BOT_USER_ID, DEFAULT_MODEL, DEFAULT_TEMPERATURE, SERVICE_NAME
from util import completion

logger = Logger(SERVICE_NAME, child=True)


# This gets activated when the bot is tagged in a message
def handle_mention(event: dict[str, Any], say: Say, client: WebClient):
    logger.info("request: %s", event["text"])

    match = re.match(r"^<@[a-zA-Z0-9]+>(.*)$", event["text"])
    if not match:
        client.chat_postEphemeral(
            text="You must tag me at the beginning of your message.",
            thread_ts=event["event_ts"],
            user=event["user"],
            channel=event["channel"],
        )
        return
    prompt = match.group(1)

    client.chat_postEphemeral(
        text="Processing...",
        thread_ts=event["event_ts"],
        user=event["user"],
        channel=event["channel"],
    )
    response_text = completion(
        prompt, DEFAULT_MODEL, DEFAULT_TEMPERATURE, event["user"]
    )
    say(
        f"Here you go: \n{response_text}",
        thread_ts=event["event_ts"],
        parse="none",
        mrkdwn=False,
    )


# This gets activated on messages in subscribed channels
def handle_message(event: dict[str, Any], say: Say, client: WebClient):
    if (
        ("subtype" in event and event["subtype"] != "message_replied")
        or "thread_ts" not in event
        or event["thread_ts"] == event["ts"]
    ):
        # Not a reply
        logger.info("Not a reply")
        return
    if event["parent_user_id"] != BOT_USER_ID:
        # Not a reply to ourself
        logger.info("Not a reply to ourself")
        return
    if event["user"] == BOT_USER_ID:
        # Don't reply to our own messages
        logger.info("Message from ourself")
        return
    if f"@{BOT_USER_ID}" in event["text"]:
        # Don't reply to mentions
        logger.info("Message mentions ourself")
        return

    res = client.conversations_replies(channel=event["channel"], ts=event["thread_ts"])
    messages = res["messages"]
    orig_msg_txt: str = messages[0]["text"]
    orig_msg_txt = orig_msg_txt.replace("&lt;", "<").replace("&gt;", ">")

    match = re.match(
        r"^<model=([a-z0-9-]+),temperature=(\d\.?\d*)>\n(.*)$", orig_msg_txt
    )
    if not match:
        # Cannot determine parameters
        logger.warning("Cannot determine OpenAI parameters from text: %s", orig_msg_txt)
        return
    model = match.group(1)
    temperature = float(match.group(2))
    orig_prompt = match.group(3)

    thread = [orig_prompt] + [msg["text"] for msg in messages[1:] if "text" in msg]
    prompt = "\n".join(thread)

    if len(prompt) == 0:
        logger.error("Empty thread prompt. Thread data: %s", messages)
        return

    logger.info("thread prompt: %s", prompt)

    response_text = completion(prompt, model, temperature, event["user"])
    logger.info("reply: %s", response_text)
    say(response_text, thread_ts=event["thread_ts"], parse="none", mrkdwn=False)


def init_events(app: App):
    app.event("app_mention")(ack=lambda ack: ack(), lazy=[handle_mention])
    app.event("message")(ack=lambda ack: ack(), lazy=[handle_message])
