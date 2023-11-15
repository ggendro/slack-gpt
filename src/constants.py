CHAT_MODELS = [
    "gpt-4",
    "gpt-4-32k",
    "gpt-4-0314",
    "gpt-4-0613",
    "gpt-4-32k-0314",
    "gpt-4-32k-0613",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0301",
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-1106",
    "gpt-4-1106-preview",
    "gpt-4-vision-preview",
]
DEFAULT_CHAT_MODEL = "gpt-4"
DEFAULT_SYSTEM_PROMPT = (
    "You are GPT-4, a powerful large language model trained by OpenAI. Answer as "
    "concisely as possible."
)

COMPLETION_MODELS = [
    "gpt-3.5-turbo-instruct",
    "text-davinci-003",
    "text-davinci-002",
    "text-curie-001",
    "text-babbage-001",
    "text-ada-001",
    "davinci",
    "curie",
    "babbage",
    "ada",
    "code-davinci-002",
]
DEFAULT_COMPLETION_MODEL = "text-davinci-003"

EDIT_MODELS = ["text-davinci-edit-001", "code-davinci-edit-001"]
DEFAULT_EDIT_MODEL = "text-davinci-edit-001"
DEFAULT_TEMPERATURE = 0.5

ASR_MODELS = ["whisper-1"]
DEFAULT_ASR_MODEL = "whisper-1"
MAX_AUDIO_FILE_SIZE = 25_000_000  # 25 MB

TTS_MODELS = ["tts-1", "tts-1-1106", "tts-1-hd", "tts-1-hd-1106"]
DEFAULT_TTS_MODEL = "tts-1"
TTS_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
DEFAULT_TTS_VOICE = "fable"

IMAGE_MODELS = ["dall-e-3", "dall-e-2"]
DEFAULT_IMAGE_MODEL = "dall-e-3"

SERVICE_NAME = "slack-gpt-bot"
BOT_USER_ID = None  # Set programmatically in app.py
