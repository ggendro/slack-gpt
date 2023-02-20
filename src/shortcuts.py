from typing import Any

from slack_bolt import Ack, App, Say
from slack_sdk import WebClient

from constants import (
    COMPLETION_MODELS,
    DEFAULT_EDIT_MODEL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    EDIT_MODELS,
)
from util import completion, edit


def respond_message(shortcut: dict[str, Any], client: WebClient):
    channel_id = shortcut["channel"]["id"]
    if "thread_ts" in shortcut["message"]:
        thread_ts = shortcut["message"]["thread_ts"]
    else:
        thread_ts = shortcut["message"]["ts"]
    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Respond to message"},
            "callback_id": "respond_message_view",
            "private_metadata": channel_id + "," + thread_ts,
            "blocks": [
                {
                    "type": "context",
                    "elements": [
                        {"type": "plain_text", "text": shortcut["message"]["text"]}
                    ],
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "block_id": "model_select",
                    "label": {"type": "plain_text", "text": "Model"},
                    "element": {
                        "type": "static_select",
                        "action_id": "model_select_action",
                        "options": [
                            {"text": {"type": "plain_text", "text": x}, "value": x}
                            for x in COMPLETION_MODELS
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": DEFAULT_MODEL},
                            "value": DEFAULT_MODEL,
                        },
                    },
                },
                {
                    "type": "input",
                    "block_id": "temperature_input",
                    "label": {"type": "plain_text", "text": "Temperature"},
                    "element": {
                        "type": "number_input",
                        "is_decimal_allowed": True,
                        "action_id": "temperature_input_action",
                        "initial_value": str(DEFAULT_TEMPERATURE),
                        "min_value": "0",
                        "max_value": "2",
                    },
                },
            ],
            "submit": {"type": "plain_text", "text": "Respond"},
        },
    )


def respond_message_submit_lazy(
    view: dict[str, Any], body: dict[str, Any], say: Say, client: WebClient
):
    values = view["state"]["values"]
    model = values["model_select"]["model_select_action"]["selected_option"]["value"]
    temperature = values["temperature_input"]["temperature_input_action"]["value"]
    temperature = float(temperature)

    channel_id, thread_ts = view["private_metadata"].split(",")

    res = client.conversations_history(
        channel=channel_id, inclusive=True, oldest=thread_ts, limit=1
    )
    prompt = res["messages"][0]["text"]

    response_text = completion(prompt, model, temperature, body["user"]["id"])
    say(
        response_text,
        thread_ts=thread_ts,
        channel=channel_id,
        parse="none",
        mrkdwn=False,
    )


def edit_message(shortcut: dict[str, Any], client: WebClient):
    channel_id = shortcut["channel"]["id"]
    if "thread_ts" in shortcut["message"]:
        thread_ts = shortcut["message"]["thread_ts"]
    else:
        thread_ts = shortcut["message"]["ts"]

    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Edit message"},
            "callback_id": "edit_message_view",
            "private_metadata": channel_id + "," + thread_ts,
            "blocks": [
                {
                    "type": "context",
                    "elements": [
                        {"type": "plain_text", "text": shortcut["message"]["text"]}
                    ],
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "block_id": "model_select",
                    "label": {"type": "plain_text", "text": "Model"},
                    "element": {
                        "type": "static_select",
                        "action_id": "model_select_action",
                        "options": [
                            {"text": {"type": "plain_text", "text": x}, "value": x}
                            for x in EDIT_MODELS
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": DEFAULT_EDIT_MODEL},
                            "value": DEFAULT_EDIT_MODEL,
                        },
                    },
                },
                {
                    "type": "input",
                    "block_id": "temperature_input",
                    "label": {"type": "plain_text", "text": "Temperature"},
                    "element": {
                        "type": "number_input",
                        "is_decimal_allowed": True,
                        "action_id": "temperature_input_action",
                        "initial_value": str(DEFAULT_TEMPERATURE),
                        "min_value": "0",
                        "max_value": "2",
                    },
                },
                {
                    "type": "input",
                    "block_id": "instruct_input",
                    "label": {"type": "plain_text", "text": "Instructions"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "instruct_input_action",
                        "min_length": 1,
                        "focus_on_load": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Enter instructions",
                        },
                    },
                },
                {
                    "type": "input",
                    "block_id": "num_edits_input",
                    "label": {"type": "plain_text", "text": "Number of suggestions"},
                    "element": {
                        "type": "number_input",
                        "is_decimal_allowed": False,
                        "action_id": "num_edits_input_action",
                        "initial_value": "2",
                        "min_value": "1",
                        "max_value": "5",
                    },
                },
            ],
            "submit": {"type": "plain_text", "text": "Generate edits"},
        },
    )


def edit_message_submit_ack(ack: Ack):
    ack(
        response_action="update",
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Edit message"},
            "callback_id": "edit_message_wait",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "Please wait while I generate edits...",
                    },
                }
            ],
        },
    )


def edit_message_submit_lazy(view: dict[str, Any], client: WebClient):
    values = view["state"]["values"]
    channel_id, thread_ts = view["private_metadata"].split(",")

    model = values["model_select"]["model_select_action"]["selected_option"]["value"]
    temperature = values["temperature_input"]["temperature_input_action"]["value"]
    temperature = float(temperature)
    instructions = values["instruct_input"]["instruct_input_action"]["value"]
    num_edits = int(values["num_edits_input"]["num_edits_input_action"]["value"])

    res = client.conversations_history(
        channel=channel_id, inclusive=True, oldest=thread_ts, limit=1
    )
    prompt = res["messages"][0]["text"]

    choices = edit(prompt, model, instructions, temperature, num_edits)

    blocks = []
    for i, choice in enumerate(choices):
        blocks.append(
            {
                "type": "section",
                "block_id": f"choice_{i + 1}",
                "text": {"type": "mrkdwn", "text": choice},
            }
        )
        blocks.append({"type": "divider"})

    client.views_update(
        view_id=view["id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Edit message"},
            "callback_id": "edit_selection_view",
            "private_metadata": channel_id + "," + thread_ts,
            "blocks": blocks
            + [
                {
                    "type": "input",
                    "block_id": "edit_select",
                    "label": {"type": "plain_text", "text": "Suggestions"},
                    "element": {
                        "type": "static_select",
                        "action_id": "edit_select_action",
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": str(i)},
                                "value": str(i),
                            }
                            for i in range(1, len(choices) + 1)
                        ],
                        "placeholder": {"type": "plain_text", "text": "Select an edit"},
                    },
                },
            ],
            "submit": {"type": "plain_text", "text": "Post edit"},
        },
    )


def edit_choice_submit_lazy(view: dict[str, Any], say: Say):
    values = view["state"]["values"]
    channel_id, thread_ts = view["private_metadata"].split(",")
    val = values["edit_select"]["edit_select_action"]["selected_option"]["value"]
    val = int(val)
    choices = []
    for block in view["blocks"]:
        if block["type"] == "section" and block["block_id"].startswith("choice_"):
            choices.append(block["text"]["text"])
    say(
        choices[val - 1],
        thread_ts=thread_ts,
        channel=channel_id,
        parse="none",
        mrkdwn=False,
    )


def init_shortcuts(app: App):
    app.message_shortcut("respond_message")(
        ack=lambda ack: ack(), lazy=[respond_message]
    )
    app.view_submission("respond_message_view")(
        ack=lambda ack: ack(response_action="clear"), lazy=[respond_message_submit_lazy]
    )
    app.message_shortcut("edit_message")(ack=lambda ack: ack(), lazy=[edit_message])
    app.view_submission("edit_message_view")(
        ack=edit_message_submit_ack, lazy=[edit_message_submit_lazy]
    )
    app.view_submission("edit_selection_view")(
        ack=lambda ack: ack(response_action="clear"), lazy=[edit_choice_submit_lazy]
    )
