import re
from typing import Any

from aws_lambda_powertools.logging import Logger
from slack_bolt import App, Respond, Say
from slack_sdk import WebClient

import constants as c
from util import chat_params_str, image

logger = Logger(c.SERVICE_NAME, child=True)


def handle_chat_command(command: dict[str, Any], say: Say, respond: Respond):
    logger.info("request: %s", command["text"])

    if command["text"].lower() == "help":
        respond(
            f"""Usage: ```/chat [model] [temperature] system_prompt```

`model`: one of {', '.join(c.COMPLETION_MODELS)} (default: {c.DEFAULT_COMPLETION_MODEL})
`temperature`: a number between 0 and 2 (default: 0.5)
`system_prompt`: the system prompt to prime ChatGPT (default: "{c.DEFAULT_SYSTEM_PROMPT}")"""  # noqa: E501
        )
        return

    match = re.match(r"^([a-z0-9-.]+ ?)?(\d\.?\d* ?)?(.*)$", command["text"], re.DOTALL)
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
def handle_gpt_command(command: dict[str, Any], say: Say, respond: Respond):
    logger.info("request: %s", command["text"])

    if command["text"].lower() == "help":
        respond(
            f"""Usage: ```/gpt [model] [temperature]```

`model`: one of {', '.join(c.COMPLETION_MODELS)} (default: {c.DEFAULT_COMPLETION_MODEL})
`temperature`: a number between 0 and 2 (default: 0.5)
"""
        )
        return

    match = re.match(r"^([a-z0-9-]+ )?(\d\.?\d* )?$", command["text"], re.DOTALL)
    if not match:
        respond("Invalid command. Usage: /gpt [model] [temperature] prompt")
        return
    model = match.group(1).strip() if match.group(1) else c.DEFAULT_COMPLETION_MODEL
    temperature = match.group(2).strip() if match.group(2) else c.DEFAULT_TEMPERATURE
    temperature = float(temperature)

    if model not in c.COMPLETION_MODELS:
        respond(
            f"Invalid model: `{model}`. Valid models are:\n"
            f"`{'`, `'.join(c.COMPLETION_MODELS)}`"
        )
        return
    if temperature < 0 or temperature > 2:
        respond(f"Invalid temperature: {temperature}. Must be between 0 and 2.")
        return

    params = {"model": model, "temperature": temperature}
    say(
        text="New conversation with other GPT models: :robot_face:",
        blocks=[
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Conversation with older GPT models :robot_face:",
                },
            },
            {
                "type": "context",
                "block_id": "parameters",
                "elements": [
                    {"type": "mrkdwn", "text": f"`{chat_params_str(params)}`"}
                ],
            },
        ],
    )


# This gets activated on the use of the /image command
def handle_image_command(
    command: dict[str, Any], say: Say, respond: Respond, client: WebClient
):
    logger.info("request: %s", command["text"])

    if command["text"].lower() == "help":
        respond(
            f"""Usage: ```/image [model] prompt```

`model`: one of {', '.join(c.IMAGE_MODELS)} (default: {c.DEFAULT_IMAGE_MODEL})
`prompt`: image prompt
"""
        )
        return

    match = re.match(r"^([a-z0-9-.]+ ?)?(.*)$", command["text"], re.DOTALL)
    if not match:
        respond("Invalid command. Usage: /image [model] prompt")
        return
    model = match.group(1).strip() if match.group(1) else c.DEFAULT_IMAGE_MODEL
    prompt = match.group(2)

    if model not in c.IMAGE_MODELS:
        respond(
            f"Invalid model: {model}. Valid models are: {', '.join(c.IMAGE_MODELS)}"
        )
        return

    respond(text="Generating image...")

    image_bytes = image(prompt=prompt, model=model, user=command["user_id"])
    trigger_id = command["trigger_id"]

    user_info = client.users_info(user=command["user_id"])
    display_name = user_info["user"]["profile"]["display_name"]

    client.files_upload_v2(
        filename=f"image_{trigger_id}.webp",
        file=image_bytes,
        channel=command["channel_id"],
        title=f"Image generated by {display_name}",
        alt_txt=prompt[:1000],  # Alt text limited to 1000 chars
        initial_comment=(
            f"Image generated by {display_name} with the following prompt: {prompt}"
        ),
    )


def init_commands(app: App):
    app.command("/gpt")(ack=lambda ack: ack(), lazy=[handle_gpt_command])
    app.command("/chat")(ack=lambda ack: ack(), lazy=[handle_chat_command])
    app.command("/image")(ack=lambda ack: ack(), lazy=[handle_image_command])
