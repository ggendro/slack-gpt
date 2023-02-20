
# Slack-GPT Bot

Repository for a slack bot app connected to the [OpenAI API](https://openai.com/api/). Our method is inspired by [this blogpost](https://medium.com/@alexandre.tkint/integrate-openais-chatgpt-within-slack-a-step-by-step-approach-bea43400d311).


## Installation

```
$ git clone https://github.com/ggendro/slack-gpt.git
$ cd slack-gpt
$ pip install -r requirements.txt
```

## Tokens

To connect the bot to Slack and OpenAI, you need a `<slack_app_token>`, a `<slack_bot_token>`, and an `<openai_api_key>`. Follow the following steps to generate them:

### 1. `<slack_app_token>`

To obtain the <slack_app_token>, you need to create an app with the [Slack API](https://api.slack.com/). 

You need to give your app the following permissions:
 - app_mentions:read
 - channels:history
 - channels:read
 - chat:write
 - files:write

Enable socket mode and copy the generated token, this is your `<slack_app_token>`.

### 2. `<slack_bot_token>`

Stay in [Slack API](https://api.slack.com/). Enable "Event Subscription" and subscribe to the "app_mention" bot event.

Generate a Bot User OAuth Token in OAuth & Permissions, this is the `<slack_bot_token>`.

### 3. `<openai_api_key>`

An OpenAI API key is also required and can be obtained on the [OpenAI API page](https://platform.openai.com/account/api-keys). Once obtained, it must be pasted under `<openai_api_key>` as described in the usage section.


## Usage

To launch the server, run the following script:
```
python app.py --slack_app_token <slack_app_token> --slack_bot_token <slack_bot_token> --openai_api_key <openai_api_key>
```

You will be able to communicate with the bot in your slack workspace using the name given in your app.