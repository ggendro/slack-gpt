from io import BytesIO
from typing import Any, Optional

import openai
import requests
from aws_lambda_powertools.logging import Logger
from slack_sdk import WebClient

import constants as c
from keys import BOT_OAUTH_TOKEN, OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
logger = Logger(c.SERVICE_NAME, child=True)


def normalise_text(text: str) -> str:
    return text.replace("&lt;", "<").replace("&gt;", ">")


param_types = {
    "model": str,
    "temperature": float,
    "max_tokens": int,
    "top_p": float,
    "frequency_penalty": float,
    "presence_penalty": float,
    "stop": str,
    "logprobs": int,
    "echo": bool,
    "best_of": int,
    "n": int,
    "stream": bool,
    "logit_bias": dict[str, float],
}


def get_chat_params(param_str: str) -> dict[str, Any]:
    """Converts a string of parameters into a dictionary of parameters.

    Args:
    =====
    param_str: str
        A string of parameters in the format "<key1=value1,key2=value2>"

    Returns:
    ========
    dict[str, Any]: A dictionary of parameters
    """
    param_str = param_str.strip("<>")
    params = dict([param.split("=") for param in param_str.split(",")])
    for key, value in params.items():
        if key in param_types:
            params[key] = param_types[key](value)
    return params


def chat_params_str(params: dict[str, Any]) -> str:
    """Converts a dictionary of parameters into a string of parameters.

    Args:
    =====
    params: dict[str, Any]
        A dictionary of parameters.

    Returns:
    ========
    str: A string of parameters in the format "<key1=value1,key2=value2>"
    """
    return "<" + ",".join(f"{key}={value}" for key, value in params.items()) + ">"


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
    e: BaseException, user: str, channel: str, thread: Optional[str], client: WebClient
):
    """Logs an error and posts an ephemeral message to the user."""
    logger.error("Error: %s", e)
    client.chat_postEphemeral(
        text=f"An error occurred while processing your message:\n```{e}```",
        channel=channel,
        user=user,
        thread_ts=thread,
    )


def transcribe(url: str, prompt: str, model: str, temperature: float) -> str:
    """Transcribes an audio file using OpenAI's API."""
    r = requests.get(url, headers={"Authorization": f"Bearer {BOT_OAUTH_TOKEN}"})
    filename = url.split("/")[-1]
    try:
        with BytesIO(r.content) as file:
            response = openai.Audio.transcribe_raw(
                model=model,
                file=file,
                filename=filename,
                temperature=temperature,
                prompt=prompt,
            ).text
    except openai.OpenAIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(
            f"OpenAI Error: HTTP {e.http_status}: {e.user_message}"
        ) from e
    if len(response) == 0:
        logger.warning("Empty GPT response.")
        response = "<|endoftext|>"
    logger.info("GPT Response: %s", response)
    return response


def alternate_msgs(msgs: list[str], user_starts: bool = True) -> list[dict[str, str]]:
    """Alternates between user and assistant messages.

    Args:
    =====
    msgs: list[str]
        A list of messages.
    user_starts: bool
        Whether the user starts the conversation or not.

    Returns:
    ========
    list[dict[str, str]]: A list of messages with the role of the sender.
    """
    messages = []
    for i, msg in enumerate(msgs):
        messages.append(
            {
                "role": "user" if i % 2 == int(user_starts) else "assistant",
                "content": msg,
            }
        )
    return messages


def chat(
    messages: list[str], system_msg: str, model: str, temperature: float, user: str
) -> str:
    """Uses OpenAI's API to chat with a user."""
    messages_dict = alternate_msgs(messages)
    try:
        response = (
            openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                ]
                + messages_dict,
                # max_tokens=1024,
                n=1,
                stop=None,
                temperature=temperature,
                user=f"sail-gpt-bot-{user}",
            )
            .choices[0]
            .message.content
        )
    except openai.OpenAIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(
            f"OpenAI Error: HTTP {e.http_status}: {e.user_message}"
        ) from e
    if len(response) == 0:
        logger.warning("Empty GPT response.")
        response = "<|endoftext|>"
    logger.info("GPT Response: %s", response)
    return response


def completion(prompt: str, model: str, temperature: float, user: str) -> str:
    """Uses OpenAI's API to complete a prompt."""
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
        raise RuntimeError(
            f"OpenAI Error: HTTP {e.http_status}: {e.user_message}"
        ) from e
    if len(response) == 0:
        logger.warning("Empty GPT response.")
        response = "<|endoftext|>"
    logger.info("GPT Response: %s", response)
    return response


def edit(
    prompt: str, model: str, instruction: str, temperature: float, n: int
) -> list[str]:
    """Uses OpenAI's API to edit a prompt."""
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
        raise RuntimeError(
            f"OpenAI Error: HTTP {e.http_status}: {e.user_message}"
        ) from e
    choices = [choice.text for choice in choices]
    logger.info("GPT Response: %s", choices)
    return choices
