import re
from typing import Any

from aws_lambda_powertools.logging import Logger
from slack_bolt import App, Respond, Say

from constants import (
    COMPLETION_MODELS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    SERVICE_NAME,
)
from util import completion

logger = Logger(SERVICE_NAME, child=True)


# This gets activated on the use of the /gpt command
def handle_gpt_command(command: dict[str, Any], say: Say, respond: Respond):
    logger.info("request: %s", command["text"])

    if command["text"].lower() == "help":
        respond(
            "Usage: /gpt [model] [temperature] prompt\n\n"
            f"model: one of {', '.join(COMPLETION_MODELS)} (default: {DEFAULT_MODEL})\n"
            "temperature: a number between 0 and 2 (default: 0.5)\n"
            "prompt: the text to use as a prompt for the model"
        )
        return

    match = re.match(r"^([a-z0-9-]+ )?(\d\.?\d* )?(.*)$", command["text"], re.DOTALL)
    if not match:
        respond("Invalid command. Usage: /gpt [model] [temperature] prompt")
        return
    model = match.group(1).strip() if match.group(1) else DEFAULT_MODEL
    temperature = match.group(2).strip() if match.group(2) else DEFAULT_TEMPERATURE
    temperature = float(temperature)
    prompt = match.group(3)

    if model not in COMPLETION_MODELS:
        respond(
            f"Invalid model: {model}. Valid models are: {', '.join(COMPLETION_MODELS)}"
        )
        return
    if temperature < 0 or temperature > 2:
        respond(f"Invalid temperature: {temperature}. Must be between 0 and 2.")
        return

    respond("Processing...")
    response_text = completion(prompt, model, temperature, command["user_id"])
    res = say(
        f"<model={model},temperature={temperature:.3f}>\n{prompt}",
        parse="none",
        mrkdwn=False,
    )
    if model in ["code-davinci-002", "code-cushman-001"]:
        response_text = f"```{response_text}```"
    say(response_text, thread_ts=res["ts"], parse="none", mrkdwn=False)


def init_commands(app: App):
    app.command("/gpt")(ack=lambda ack: ack(), lazy=[handle_gpt_command])
