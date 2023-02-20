import openai
from aws_lambda_powertools.logging import Logger

from constants import SERVICE_NAME
from keys import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
logger = Logger(SERVICE_NAME, child=True)


def completion(prompt: str, model: str, temperature: float, user: str) -> str:
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
    if len(response) == 0:
        logger.warning("Empty GPT response.")
        response = "<|endoftext|>"
    logger.info("GPT Response: %s", response)
    return response


def edit(
    prompt: str, model: str, instruction: str, temperature: float, n: int
) -> list[str]:
    choices = openai.Edit.create(
        model=model, input=prompt, instruction=instruction, n=n, temperature=temperature
    ).choices
    choices = [choice.text for choice in choices]
    logger.info("GPT Response: %s", choices)
    return choices
