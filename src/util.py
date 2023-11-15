import base64
from io import BytesIO
from typing import Any, Literal, Optional

import openai
import requests
from aws_lambda_powertools.logging import Logger
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from slack_sdk import WebClient

import constants as c
from keys import BOT_OAUTH_TOKEN, OPENAI_API_KEY, OPENAI_ORG_ID

openai.api_key = OPENAI_API_KEY
openai.organization = OPENAI_ORG_ID
logger = Logger(c.SERVICE_NAME, child=True)


def normalise_text(text: str) -> str:
    """Remove symbol escapes from text."""
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

    Args
    ----
    param_str: str
        A string of parameters in the format "<key1=value1,key2=value2>"

    Returns
    -------
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

    Args
    ----
    params: dict[str, Any]
        A dictionary of parameters.

    Returns
    -------
    str: A string of parameters in the format "<key1=value1,key2=value2>"
    """
    return "<" + ",".join(f"{key}={value}" for key, value in params.items()) + ">"


def error_view(e: BaseException) -> dict[str, Any]:
    """Creates a Slack view for an error.

    Args
    ----
    e: BaseException
        The error.

    Returns
    -------
    dict[str, Any]: A Slack view.
    """
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
    """Logs an error and posts an ephemeral message to the user.

    Args
    ----
    e: BaseException
        The error.
    user: str
        The user's ID.
    channel: str
        The channel's ID.
    thread: Optional[str]
        The thread's ID.
    client: WebClient
        The Slack client.
    """
    logger.error("Error: %s", e)
    client.chat_postEphemeral(
        text=f"An error occurred while processing your message:\n```{e}```",
        channel=channel,
        user=user,
        thread_ts=thread,
    )


def image(prompt: str, model: str, user: str) -> bytes:
    """Generates an image with DALL-E.

    Args
    ----
    prompt: str
        The image prompt.
    model: str
        The image generation model to use.
    user: str
        The user's ID.

    Returns
    -------
    bytes: The image data
    """
    try:
        response = (
            openai.images.generate(
                prompt=prompt,
                model=model,
                n=1,
                response_format="b64_json",
                size="1024x1024",
                user=user,
            )
            .data[0]
            .b64_json
        )
    except openai.APIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(f"OpenAI Error {e.code}: {e.message}") from e
    if response is None:
        raise RuntimeError("No image content")
    image_bytes = base64.decodebytes(response.encode())
    return image_bytes


def tts(
    text: str,
    model: str,
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
) -> bytes:
    """Generates a TTS (text-to-speech) audio from the given text using
    OpenAI's speech API.

    Args
    ----
    text: str
        The text to generate speech for.
    model: str
        The model to use
    voice: str
        The voice to use.

    Returns
    -------
    bytes: The audio response from the model.
    """
    try:
        response = openai.audio.speech.create(
            input=text, model=model, voice=voice, response_format="mp3", speed=1.0
        ).read()
    except openai.APIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(f"OpenAI Error {e.code}: {e.message}") from e
    return response


def transcribe(url: str, prompt: str, model: str, temperature: float) -> str:
    """Transcribes an audio file using OpenAI's API.

    Args
    ----
    url: str
        The URL of the audio file.
    prompt: str
        The prompt to use.
    model: str
        The model to use.
    temperature: float
        The temperature to use.

    Returns
    -------
    str: The response from the model.
    """
    r = requests.get(url, headers={"Authorization": f"Bearer {BOT_OAUTH_TOKEN}"})
    try:
        with BytesIO(r.content) as file:
            response = openai.audio.transcriptions.create(
                model=model,
                file=file,
                temperature=temperature,
                prompt=prompt,
            ).text
    except openai.APIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(f"OpenAI Error {e.code}: {e.message}") from e
    if len(response) == 0:
        logger.warning("Empty GPT response.")
        response = "<|endoftext|>"
    logger.info("GPT Response: %s", response)
    return response


def create_msgs(
    msgs: list[str], system_prompt: str, user_starts: bool = True
) -> list[ChatCompletionMessageParam]:
    """Alternates between user and assistant messages.

    Args
    ----
    msgs: list[str]
        A list of messages.
    user_starts: bool
        Whether the user starts the conversation or not.

    Returns
    -------
    list[dict[str, str]]: A list of messages with the role of the sender.
    """
    return [ChatCompletionSystemMessageParam(role="system", content=system_prompt)] + [
        ChatCompletionUserMessageParam(content=msg, role="user")
        if i % 2 == int(user_starts)
        else ChatCompletionAssistantMessageParam(content=msg, role="assistant")
        for i, msg in enumerate(msgs)
    ]  # type: ignore


def chat(
    messages: list[str], system_msg: str, model: str, temperature: float, user: str
) -> str:
    """Uses OpenAI's API to chat with a user.

    Args
    ----
    messages: list[str]
        A list of messages alternating between user and assistant.
    system_msg: str
        The initial system message.
    model: str
        The model to use.
    temperature: float
        The temperature to use.
    user: str
        The user's ID.

    Returns
    -------
    str: The response from the model.
    """
    try:
        response = (
            openai.chat.completions.create(
                model=model,
                messages=create_msgs(messages, system_msg),
                # max_tokens=1024,
                n=1,
                stop=None,
                temperature=temperature,
                user=f"sail-gpt-bot-{user}",
            )
            .choices[0]
            .message.content
        )
    except openai.APIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(f"OpenAI Error {e.code}: {e.message}") from e
    if response is None or len(response) == 0:
        logger.warning("Empty GPT response.")
        response = "<|endoftext|>"
    logger.info("GPT Response: %s", response)
    return response


def completion(prompt: str, model: str, temperature: float, user: str) -> str:
    """Uses OpenAI's API to complete a prompt.

    Args
    ----
    prompt: str
        The prompt to complete.
    model: str
        The model to use.
    temperature: float
        The temperature to use.
    user: str
        The user's ID.

    Returns
    -------
    str: The response from the model.
    """
    try:
        response = (
            openai.completions.create(
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
    except openai.APIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(f"OpenAI Error {e.code}: {e.message}") from e
    if len(response) == 0:
        logger.warning("Empty GPT response.")
        response = "<|endoftext|>"
    logger.info("GPT Response: %s", response)
    return response


def edit(
    prompt: str, model: str, instruction: str, temperature: float, n: int
) -> list[str]:
    """Uses OpenAI's API to edit a prompt.

    Args
    ----
    prompt: str
        The prompt to edit.
    model: str
        The model to use.
    instruction: str
        The editing instructions.
    temperature: float
        The temperature to use.
    n: int
        The number of choices to return.

    Returns
    -------
    list[str]: The responses from the model.
    """
    try:
        choices = openai.edits.create(
            model=model,
            input=prompt,
            instruction=instruction,
            n=n,
            temperature=temperature,
        ).choices
    except openai.APIError as e:
        logger.error("OpenAI Error: %s", e)
        raise RuntimeError(f"OpenAI Error {e.code}: {e.message}") from e
    edits_text = [choice.text for choice in choices]
    logger.info("GPT Response: %s", edits_text)
    return edits_text
