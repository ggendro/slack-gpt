from typing import Any

import openai
from aws_lambda_powertools.logging import Logger
from slack_sdk import WebClient

from constants import SERVICE_NAME
from keys import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
logger = Logger(SERVICE_NAME, child=True)


def error_view(e: BaseException) -> dict[str, Any]:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Edit message"},
        "callback_id": "error_modal",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "An Error occurred"},
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": f"```{e}```"}},
        ],
    }


def log_post_error(
    e: BaseException, user: str, channel: str, thread: str, client: WebClient
):
    logger.error("Error: %s", e)
    client.chat_postEphemeral(
        text=f"An error occurred while processing your message:\n```{e}```",
        channel=channel,
        user=user,
        thread_ts=thread,
    )


def completion(prompt: str, model: str, temperature: float, user: str) -> str:
    try:
        response = (
            openai.Completion.create(
                model=model,
                prompt=prompt,
                max_tokens=1024,
                n=1,
                stop=None,
                temperature=temperature,
                user=f"sail-gpt-bot-{user}",
            )
            .choices[0]
            .text
        )
    except openai.OpenAIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(f"OpenAI Error: HTTP {e.code}: {e.user_message}") from e
    if len(response) == 0:
        logger.warning("Empty GPT response.")
        response = "<|endoftext|>"
    logger.info("GPT Response: %s", response)
    return response


def edit(
    prompt: str, model: str, instruction: str, temperature: float, n: int
) -> list[str]:
    try:
        choices = openai.Edit.create(
            model=model,
            input=prompt,
            instruction=instruction,
            n=n,
            temperature=temperature,
        ).choices
    except openai.OpenAIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(f"OpenAI Error: HTTP {e.code}: {e.user_message}") from e
    choices = [choice.text for choice in choices]
    logger.info("GPT Response: %s", choices)
    return choices
