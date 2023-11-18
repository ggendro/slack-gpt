import os

from aws_lambda_powertools.logging import Logger, correlation_paths
from slack_bolt import App, BoltRequest
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

import constants as c
from commands import init_commands
from events import init_events
from keys import BOT_OAUTH_TOKEN, SIGNING_SECRET
from shortcuts import init_shortcuts

logger = Logger(c.SERVICE_NAME, level=os.environ.get("LOG_LEVEL", "INFO"))
app = App(
    token=BOT_OAUTH_TOKEN,
    name="slack-gpt-bot-app",
    signing_secret=SIGNING_SECRET,
    logger=logger,  # type: ignore
    process_before_response=True,
)
c.BOT_USER_ID = app.client.auth_test()["user_id"]
logger.info("Bot user ID: %s", c.BOT_USER_ID)


@app.use
def ignore_retries(req: BoltRequest, next):
    if "x-slack-retry-num" not in req.headers:
        next()


init_commands(app)
init_shortcuts(app)
init_events(app)


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL, log_event=True
)
def lambda_handler(event, context):
    return SlackRequestHandler(app).handle(event, context)
