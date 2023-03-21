import boto3

ssm = boto3.client("ssm")

res = ssm.get_parameters_by_path(Path="/slack-gpt-bot", WithDecryption=True)
params = {p["Name"].split("/")[-1]: p["Value"] for p in res["Parameters"]}

BOT_OAUTH_TOKEN = params["BOT_OAUTH_TOKEN"]
CLIENT_SECRET = params["CLIENT_SECRET"]
SIGNING_SECRET = params["SIGNING_SECRET"]
OPENAI_API_KEY = params["OPENAI_API_KEY"]
OPENAI_ORG_ID = params["OPENAI_ORG_ID"]
