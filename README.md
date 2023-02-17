
# Slack-GPT Bot

Repository for a slack bot app connected to the [OpenAI API](https://openai.com/api/). The method is mainly inspired by the one described [here](https://medium.com/@alexandre.tkint/integrate-openais-chatgpt-within-slack-a-step-by-step-approach-bea43400d311).


## Installation

### Code repository

```
$ git clone https://github.com/ggendro/slack-gpt.git
$ cd slack-gpt
$ pip install -r requirements.txt
```

### Tokens

It is necessary to have two slack tokens to connect the bot to the workspace, they can be obtained [here](https://api.slack.com/). Link this server to an existing one or crete a new one and give it the proper authorisations as described in this [page](https://medium.com/@alexandre.tkint/integrate-openais-chatgpt-within-slack-a-step-by-step-approach-bea43400d311).


An OpenAI API key is also required and can be obtained [here](https://platform.openai.com/docs/quickstart). Once obtained, it must be pasted under <openai_api_key> as described in the usage section.


## Usage

To launch the server, run the following script:
```
python app.py --slack_app_token <slack_app_token> --slack_bot_token <slack_bot_token> --openai_api_key <openai_api_key>
```

You will be able to communicate with the bot in your slack workspace.