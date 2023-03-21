import re
from typing import Any

from aws_lambda_powertools.logging import Logger
from slack_bolt import App, Respond, Say
from slack_sdk import WebClient

import constants as c
from util import chat_params_str, completion, log_post_error

logger = Logger(c.SERVICE_NAME, child=True)


def handle_chat_command(command: dict[str, Any], say: Say, respond: Respond):
    logger.info("request: %s", command["text"])

    if command["text"].lower() == "help":
        respond(
            f"""Usage: ```/chat [model] [temperature] system_prompt```

`model`: one of {', '.join(c.COMPLETION_MODELS)} (default: {c.DEFAULT_MODEL})
`temperature`: a number between 0 and 2 (default: 0.5)
`system_prompt`: the system prompt to prime ChatGPT (default: "{c.DEFAULT_SYSTEM_PROMPT}")"""  # noqa: E501
        )
        return

    match = re.match(r"^([a-z0-9-]+ )?(\d\.?\d* )?(.*)$", command["text"], re.DOTALL)
    if not match:
        respond("Invalid command. Usage: /chat [model] [temperature] system_prompt")
        return
    model = match.group(1).strip() if match.group(1) else c.DEFAULT_CHAT_MODEL
    temperature = match.group(2).strip() if match.group(2) else c.DEFAULT_TEMPERATURE
    temperature = float(temperature)
    system_prompt = match.group(3)
    if not system_prompt:
        system_prompt = c.DEFAULT_SYSTEM_PROMPT

    if model not in c.CHAT_MODELS:
        respond(f"Invalid model: {model}. Valid models are: {', '.join(c.CHAT_MODELS)}")
        return
    if temperature < 0 or temperature > 2:
        respond(f"Invalid temperature: {temperature}. Must be between 0 and 2.")
        return

    params = {"model": model, "temperature": temperature}
    say(
        text="New conversation with ChatGPT: :robot_face:",
        blocks=[
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Conversation with ChatGPT :robot_face:",
                },
            },
            {
                "type": "context",
                "block_id": "parameters",
                "elements": [
                    {"type": "mrkdwn", "text": f"`{chat_params_str(params)}`"}
                ],
            },
            {
                "type": "context",
                "block_id": "system_prompt",
                "elements": [{"type": "plain_text", "text": system_prompt}],
            },
        ],
    )


# This gets activated on the use of the /gpt command
def handle_gpt_command(
    command: dict[str, Any], say: Say, respond: Respond, client: WebClient
):
    logger.info("request: %s", command["text"])

    if command["text"].lower() == "help":
        respond(
            f"""Usage: ```/gpt [model] [temperature] prompt```

`model`: one of {', '.join(c.COMPLETION_MODELS)} (default: {c.DEFAULT_MODEL})
`temperature`: a number between 0 and 2 (default: 0.5)
`prompt`: the text to use as a prompt for the model"""
        )
        return

    match = re.match(r"^([a-z0-9-]+ )?(\d\.?\d* )?(.*)$", command["text"], re.DOTALL)
    if not match:
        respond("Invalid command. Usage: /gpt [model] [temperature] prompt")
        return
    model = match.group(1).strip() if match.group(1) else c.DEFAULT_MODEL
    temperature = match.group(2).strip() if match.group(2) else c.DEFAULT_TEMPERATURE
    temperature = float(temperature)
    prompt = match.group(3)

    if model not in c.COMPLETION_MODELS:
        respond(
            f"Invalid model: `{model}`. Valid models are:\n"
            f"`{'`, `'.join(c.COMPLETION_MODELS)}`"
        )
        return
    if temperature < 0 or temperature > 2:
        respond(f"Invalid temperature: {temperature}. Must be between 0 and 2.")
        return

    respond("Processing...")
    try:
        response_text = completion(prompt, model, temperature, command["user_id"])
    except RuntimeError as e:
        log_post_error(e, command["user_id"], command["channel_id"], None, client)
        return

    params = {"model": model, "temperature": temperature}
    res = say(
        text="New conversation with other GPT models: :robot_face:",
        blocks=[
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Conversation with other GPT models :robot_face:",
                },
            },
            {
                "type": "context",
                "block_id": "parameters",
                "elements": [
                    {"type": "mrkdwn", "text": f"`{chat_params_str(params)}`"}
                ],
            },
            {
                "type": "section",
                "block_id": "orig_prompt",
                "text": {"type": "plain_text", "text": prompt},
            },
        ],
    )
    if model in ["code-davinci-002", "code-cushman-001"]:
        response_text = f"```{response_text}```"
    say(response_text, thread_ts=res["ts"])


def init_commands(app: App):
    app.command("/gpt")(ack=lambda ack: ack(), lazy=[handle_gpt_command])
    app.command("/chat")(ack=lambda ack: ack(), lazy=[handle_chat_command])
