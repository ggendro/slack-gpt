# Slack-GPT Bot

Repository for a slack bot app connected to the [OpenAI
API](https://openai.com/api/). The method is mainly inspired by the one
described
[here](https://medium.com/@alexandre.tkint/integrate-openais-chatgpt-within-slack-a-step-by-step-approach-bea43400d311).

## Installation
This version of the bot is designed to be hosted on AWS using an AWS
Lambda function which responds to HTTP requests from Slack. This
introduces some latency and overhead, which occasionally leads to Slack
timeouts.

### Code repository
To get the code, clone the repository and install the requirements as
follows:
```
$ git clone https://github.com/ggendro/slack-gpt.git
$ cd slack-gpt
$ pip install -r src/requirements.txt
$ pip install aws-lambda-powertools
```
You also need to install the AWS SAM CLI. See the instructions
[here](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)

### API keys and tokens
It is necessary to have API tokens to connect the bot to the workspace,
they can be obtained [here](https://api.slack.com/). Link this server to
an existing one or crete a new one and give it the proper authorisations
as described in this
[page](https://medium.com/@alexandre.tkint/integrate-openais-chatgpt-within-slack-a-step-by-step-approach-bea43400d311).

An OpenAI API key is also required and can be obtained
[here](https://platform.openai.com/docs/quickstart).

Once obtained, put the API keys and tokens into the AWS Systems Manager
Parameter Store, under a common prefix (e.g. `/slack-gpt-bot`). These
keys will be obtained automatically upon the app being loaded by AWS
Lambda. See [`src/keys.py`](src/keys.py) for details.

## Running on AWS
You will need to have an AWS account, and have set up the necessary
credentials for SAM to use.

Create an IAM Role for the bot called `SlackGPTBotRole`, with the following policies:
- AWSXRayDaemonWriteAccess
- AWSLambdaBasicExecutionRole
- AWSLambdaRole
as well as an inline policy to allow access to the Parameter Store (for
API keys):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "ssm:GetParametersByPath",
                "ssm:GetParameters",
                "ssm:GetParameter"
            ],
            "Resource": [
                "arn:aws:ssm:<region>:<accountid>:parameter/slack-gpt-bot",
                "arn:aws:ssm:<region>:<accountid>:parameter/slack-gpt-bot/*"
            ]
        }
    ]
}
```

To build the application, run the AWS SAM CLI as follows:
```
$ sam build
$ sam deploy --guided
```
You can overwrite some template parameters using the CLI:
```
$ sam deploy --parameter-overrides "LogLevel=DEBUG,Tracing=PassThrough"
```

You should now be able to communicate with the bot in your slack
workspace.
