CHAT_MODELS = ["gpt-4", "gpt-4-0314", "gpt-3.5-turbo", "gpt-3.5-turbo-0301"]
DEFAULT_CHAT_MODEL = "gpt-4"
DEFAULT_SYSTEM_PROMPT = (
    "You are GPT-4, a powerful large language model trained by OpenAI. Answer as "
    "concisely as possible."
)

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
DEFAULT_MODEL = "text-davinci-003"

EDIT_MODELS = ["text-davinci-edit-001", "code-davinci-edit-001"]
DEFAULT_EDIT_MODEL = "text-davinci-edit-001"
DEFAULT_TEMPERATURE = 0.5

AUDIO_MODELS = ["whisper-1"]
DEFAULT_AUDIO_MODEL = "whisper-1"
MAX_AUDIO_FILE_SIZE = 25_000_000  # 25 MB

SERVICE_NAME = "slack-gpt-bot"
BOT_USER_ID = None  # Set programmatically in app.py
