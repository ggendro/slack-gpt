import os

COMPLETION_MODELS = [
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
EDIT_MODELS = ["text-davinci-edit-001", "code-davinci-edit-001"]
DEFAULT_MODEL = "text-davinci-003"
DEFAULT_EDIT_MODEL = "text-davinci-edit-001"
DEFAULT_TEMPERATURE = 0.5
SERVICE_NAME = "slack-gpt-bot"
BOT_USER_ID = None  # Set programmatically in app.py
