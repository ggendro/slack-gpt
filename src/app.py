import os

from aws_lambda_powertools.logging import Logger, correlation_paths
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from commands import init_commands
from constants import SERVICE_NAME
from events import init_events
from keys import BOT_OAUTH_TOKEN, SIGNING_SECRET
from shortcuts import init_shortcuts

logger = Logger(SERVICE_NAME, level=os.environ.get("LOG_LEVEL", "INFO"))
app = App(
    token=BOT_OAUTH_TOKEN,
    name="slack-gpt-bot-app",
    signing_secret=SIGNING_SECRET,
    logger=logger,
    process_before_response=True,
)

init_commands(app)
init_shortcuts(app)
init_events(app)


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL, log_event=True
)
def lambda_handler(event, context):
    return SlackRequestHandler(app).handle(event, context)
