import os
import re
from typing import Any

import openai
from aws_lambda_powertools.logging import Logger, correlation_paths
from slack_bolt import Ack, App, Respond, Say
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from keys import BOT_OAUTH_TOKEN, OPENAI_API_KEY, SIGNING_SECRET

BOT_USER_ID = os.environ["BOT_USER_ID"]

logger = Logger("slack-gpt-bot", level=os.environ.get("LOG_LEVEL", "INFO"))
app = App(
    token=BOT_OAUTH_TOKEN,
    name="slack-gpt-bot-app",
    signing_secret=SIGNING_SECRET,
    logger=logger,
    process_before_response=True,
)
openai.api_key = OPENAI_API_KEY

VALID_MODELS = [
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
]
DEFAULT_MODEL = "text-davinci-003"
DEFAULT_TEMPERATURE = 0.5


# This gets activated when the bot is tagged in a channel
def handle_mention(payload: dict[str, Any], say: Say):
    # Log message
    logger.info("request: %s", payload["text"])

    # Create prompt for ChatGPT
    match = re.match(r"^<@[a-zA-Z0-9]+>(.*)$", payload["text"])
    if match:
        prompt = match.group(1)
    else:
        return

    # Let the user know that we are busy with the request
    app.client.chat_postEphemeral(
        text="Hello from your bot! :robot_face: \nThanks for your request, I'm on it!",
        thread_ts=payload["event_ts"],
        user=payload["user"],
        channel=payload["channel"],
    )

    # Check ChatGPT
    response_text = (
        openai.Completion.create(
            model=DEFAULT_MODEL,
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=DEFAULT_TEMPERATURE,
            user=f"sail-gpt-bot-{payload['user']}",
        )
        .choices[0]
        .text
    )
    logger.info("reply: %s", response_text)

    # Reply to thread
    response = say(f"Here you go: \n{response_text}", thread_ts=payload["event_ts"])
    logger.info("status: %s", "OK" if response["ok"] else "KO")


def handle_command(command: dict[str, Any], say: Say, respond: Respond):
    # Log message
    logger.info("request: %s", command["text"])

    # Create prompt for ChatGPT
    match = re.match(r"^([a-z0-9-]+ )?(\d\.?\d* )?(.*)$", command["text"])
    if not match:
        return
    model = match.group(1).strip() if match.group(1) else DEFAULT_MODEL
    temperature = (
        float(match.group(2).strip()) if match.group(2) else DEFAULT_TEMPERATURE
    )
    prompt = match.group(3)

    if model not in VALID_MODELS:
        respond(f"Invalid model: {model}. Valid models are: {', '.join(VALID_MODELS)}")
        return
    if temperature < 0 or temperature > 2:
        respond(f"Invalid temperature: {temperature}. Must be between 0 and 2.")
        return

    respond("Processing...")

    response_text = (
        openai.Completion.create(
            model=model,
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=temperature,
            user=f"sail-gpt-bot-{command['user_id']}",
        )
        .choices[0]
        .text
    )
    logger.info("reply: %s", response_text)

    res = say(f"<model={model},temperature={temperature:.3f}>\n{prompt}")
    response = say(response_text, thread_ts=res["ts"])
    logger.info("status: %s", "OK" if response["ok"] else "KO")


def handle_message(payload: dict[str, Any], say: Say):
    if (
        ("subtype" in payload and payload["subtype"] != "message_replied")
        or "thread_ts" not in payload
        or payload["thread_ts"] == payload["ts"]
    ):
        # Not a reply
        logger.info("Not a reply")
        return
    if payload["parent_user_id"] != BOT_USER_ID:
        # Not a reply to ourself
        logger.info("Not a reply to ourself")
        return
    if payload["user"] == BOT_USER_ID:
        # Don't reply to our own messages
        logger.info("Message from ourself")
        return
    if f"@{BOT_USER_ID}" in payload["text"]:
        # Don't reply to mentions
        logger.info("Message mentions ourself")
        return

    res = app.client.conversations_replies(
        channel=payload["channel"], ts=payload["thread_ts"]
    )
    orig_msg_txt: str = res["messages"][0]["text"]
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

    thread = [orig_prompt] + [
        msg["text"] for msg in res["messages"][1:] if "text" in msg
    ]
    prompt = "\n".join(thread)

    response_text = (
        openai.Completion.create(
            model=model,
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=temperature,
            user=f"sail-gpt-bot-{payload['user']}",
        )
        .choices[0]
        .text
    )
    say(response_text, thread_ts=payload["thread_ts"])
    logger.info("reply: %s", response_text)


def respond_message(shortcut: dict[str, Any]):
    channel_id = shortcut["channel"]["id"]
    if "thread_ts" in shortcut["message"]:
        thread_ts = shortcut["message"]["thread_ts"]
    else:
        thread_ts = shortcut["message"]["ts"]
    app.client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Respond to message"},
            "callback_id": "respond_message_view",
            "private_metadata": channel_id + "," + thread_ts,
            "blocks": [
                {
                    "type": "input",
                    "block_id": "model_select",
                    "label": {"type": "plain_text", "text": "Model"},
                    "element": {
                        "type": "static_select",
                        "action_id": "model_select_action",
                        "options": [
                            {"text": {"type": "plain_text", "text": x}, "value": x}
                            for x in VALID_MODELS
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": DEFAULT_MODEL},
                            "value": DEFAULT_MODEL,
                        },
                    },
                },
                {
                    "type": "input",
                    "block_id": "temperature_input",
                    "label": {"type": "plain_text", "text": "Temperature"},
                    "element": {
                        "type": "number_input",
                        "is_decimal_allowed": True,
                        "action_id": "temperature_input_action",
                        "initial_value": str(DEFAULT_TEMPERATURE),
                        "min_value": "0",
                        "max_value": "2",
                    },
                },
            ],
            "submit": {"type": "plain_text", "text": "Respond"},
        },
    )


def respond_message_submit_ack(ack: Ack):
    ack(response_action="clear")


def respond_message_submit_lazy(view: dict[str, Any], body: dict[str, Any], say: Say):
    values = view["state"]["values"]
    model = values["model_select"]["model_select_action"]["selected_option"]["value"]
    temperature = values["temperature_input"]["temperature_input_action"]["value"]
    temperature = float(temperature)

    channel_id, thread_ts = view["private_metadata"].split(",")

    res = app.client.conversations_history(
        channel=channel_id, inclusive=True, oldest=thread_ts, limit=1
    )
    prompt = res["messages"][0]["text"]

    response_text = (
        openai.Completion.create(
            model=model,
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=temperature,
            user=f"sail-gpt-bot-{body['user']['id']}",
        )
        .choices[0]
        .text
    )
    say(response_text, thread_ts=thread_ts, channel=channel_id)
    logger.info("reply: %s", response_text)


# Acks need to be immediate to avoid timeout
app.event("app_mention")(ack=lambda ack: ack(), lazy=[handle_mention])
app.event("message")(ack=lambda ack: ack(), lazy=[handle_message])
app.command("/gpt")(ack=lambda ack: ack(), lazy=[handle_command])
app.message_shortcut("respond_message")(ack=lambda ack: ack(), lazy=[respond_message])
app.view_submission("respond_message_view")(
    ack=respond_message_submit_ack, lazy=[respond_message_submit_lazy]
)


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL, log_event=True
)
def lambda_handler(event, context):
    return SlackRequestHandler(app).handle(event, context)
