import re
from typing import Any

from aws_lambda_powertools.logging import Logger
from slack_bolt import App, Say
from slack_sdk import WebClient

import constants as c
from util import (
    ChatCompletionMessageParam,
    chat,
    completion,
    get_chat_params,
    get_img,
    log_post_error,
    normalise_text,
)

logger = Logger(c.SERVICE_NAME, child=True)


# This gets activated when the bot is tagged in a message
def handle_mention(event: dict[str, Any], say: Say, client: WebClient):
    match = re.match(r"^<@[a-zA-Z0-9]+>(.*)$", event["text"])
    if not match:
        client.chat_postEphemeral(
            text="You must tag me at the beginning of your message if you want me to respond.",  # noqa: E501
            thread_ts=event["thread_ts"],
            user=event["user"],
            channel=event["channel"],
        )
        return
    prompt = match.group(1)

    client.chat_postEphemeral(
        text="Processing...",
        thread_ts=event["thread_ts"],
        user=event["user"],
        channel=event["channel"],
    )

    try:
        response = completion(
            prompt, c.DEFAULT_COMPLETION_MODEL, c.DEFAULT_TEMPERATURE, event["user"]
        )
    except RuntimeError as e:
        log_post_error(e, event["user"], event["channel"], event["thread_ts"], client)
        return
    say(response, thread_ts=event["thread_ts"], parse="none")


def _find_paramters(message: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if "blocks" not in message:
        # Try to parse old-style message
        text = normalise_text(message["text"])
        param_str, orig_prompt = text.split("\n", 1)
        params = get_chat_params(param_str)
        return params, orig_prompt

    params = {}
    orig_prompt = ""
    for block in message["blocks"]:
        if block["block_id"] == "parameters":
            param_str = normalise_text(block["elements"][0]["text"])
            param_str = param_str.strip("`")
            params = get_chat_params(param_str)
        elif block["block_id"] in ["system_prompt", "orig_prompt"]:
            if "elements" in block:  # context
                orig_prompt = normalise_text(block["elements"][0]["text"])
            else:  # section
                orig_prompt = normalise_text(block["text"]["text"])
    return params, orig_prompt


# This gets activated on messages in subscribed channels
def handle_message(event: dict[str, Any], say: Say, client: WebClient):
    if (
        (
            "subtype" in event
            and event["subtype"] not in ["message_replied", "file_share"]
        )
        or "thread_ts" not in event
        or event["thread_ts"] == event["ts"]
    ):
        logger.info("Not a reply")
        return
    if event["parent_user_id"] != c.BOT_USER_ID:
        logger.info("Not a reply to ourself. Thread user: %s", event["parent_user_id"])
        return
    if event["user"] == c.BOT_USER_ID:
        # Don't reply to our own messages
        logger.info("Message from ourself")
        return
    if f"@{c.BOT_USER_ID}" in event["text"]:
        # Don't reply to mentions
        logger.info("Message mentions ourself")
        return

    res = client.conversations_replies(channel=event["channel"], ts=event["thread_ts"])
    messages = res["messages"]
    params, orig_prompt = _find_paramters(messages[0])
    if not params:
        logger.error("Cannot determine OpenAI parameters.")
        return
    model = params["model"]
    temperature = params["temperature"]

    try:
        if model in c.COMPLETION_MODELS:
            prompt = "\n".join([orig_prompt] + [msg["text"] for msg in messages[1:]])
            response_text = completion(prompt, model, temperature, event["user"])
        else:  # model in CHAT_MODELS
            thread: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": orig_prompt}
            ]
            for msg in messages[1:]:
                text = normalise_text(msg["text"])
                if msg["user"] == c.BOT_USER_ID:
                    thread.append({"content": text, "role": "assistant"})
                    continue

                image_urls = []
                for file in msg.get("files", []):
                    if (
                        file["mimetype"].startswith("image")
                        or file["filetype"] in c.VALID_IMAGE_TYPES
                    ):
                        image_urls.append(file["url_private"])

                if len(image_urls) == 0:
                    thread.append({"content": text, "role": "user"})
                    continue

                # One or more valid images
                content = [{"text": text, "type": "text"}] + [
                    {"image_url": {"url": get_img(url)}, "type": "image_url"}
                    for url in image_urls
                ]
                thread.append({"content": content, "role": "user"})  # type: ignore

            logger.info("thread: %s", thread)

            response_text = chat(thread, model, temperature, event["user"])
    except RuntimeError as e:
        log_post_error(e, event["user"], event["channel"], event["thread_ts"], client)
        return

    if model == "code-davinci-002":
        response_text = f"```{response_text}```"
    logger.info("reply: %s", response_text)
    say(response_text, thread_ts=event["thread_ts"])


def init_events(app: App):
    app.event("app_mention")(ack=lambda ack: ack(), lazy=[handle_mention])
    app.event("message")(ack=lambda ack: ack(), lazy=[handle_message])
