from typing import Any

import requests
from slack_bolt import Ack, App, Say
from slack_sdk import WebClient

import constants as c
from util import completion, edit, error_view, log_post_error, transcribe


def respond_message(shortcut: dict[str, Any], client: WebClient):
    channel_id = shortcut["channel"]["id"]
    ts = shortcut["message"]["ts"]
    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Respond to message"},
            "callback_id": "respond_message_view",
            "private_metadata": channel_id + "," + ts,
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
                            for x in c.COMPLETION_MODELS
                        ],
                        "initial_option": {
                            "text": {"type": "plain_text", "text": c.DEFAULT_MODEL},
                            "value": c.DEFAULT_MODEL,
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
                        "initial_value": str(c.DEFAULT_TEMPERATURE),
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

    channel_id, ts = view["private_metadata"].split(",")

    res = client.conversations_replies(
        channel=channel_id, ts=ts, inclusive=True, oldest=ts, limit=1
    )
    prompt = res["messages"][0]["text"]
    thread_ts = res["messages"][0].get("thread_ts", ts)

    try:
        response_text = completion(prompt, model, temperature, body["user"]["id"])
    except RuntimeError as e:
        log_post_error(e, body["user"]["id"], channel_id, thread_ts, client)
        return
    say(
        response_text,
        thread_ts=thread_ts,
        channel=channel_id,
        parse="none",
        mrkdwn=False,
    )


def edit_message(shortcut: dict[str, Any], client: WebClient):
    channel_id = shortcut["channel"]["id"]
    ts = shortcut["message"]["ts"]

    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Edit message"},
            "callback_id": "edit_message_view",
            "private_metadata": channel_id + "," + ts,
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
                            for x in c.EDIT_MODELS
                        ],
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": c.DEFAULT_EDIT_MODEL,
                            },
                            "value": c.DEFAULT_EDIT_MODEL,
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
                        "initial_value": str(c.DEFAULT_TEMPERATURE),
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
    channel_id, ts = view["private_metadata"].split(",")

    model = values["model_select"]["model_select_action"]["selected_option"]["value"]
    temperature = values["temperature_input"]["temperature_input_action"]["value"]
    temperature = float(temperature)
    instructions = values["instruct_input"]["instruct_input_action"]["value"]
    num_edits = int(values["num_edits_input"]["num_edits_input_action"]["value"])

    res = client.conversations_replies(
        channel=channel_id, ts=ts, inclusive=True, oldest=ts, limit=1
    )
    prompt = res["messages"][0]["text"]
    thread_ts = res["messages"][0].get("thread_ts", ts)

    try:
        choices = edit(prompt, model, instructions, temperature, num_edits)
    except RuntimeError as e:
        client.views_update(view_id=view["id"], view=error_view(e))
        return

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


def transcribe_audio(shortcut: dict[str, Any], client: WebClient):
    if "files" not in shortcut["message"]:
        client.chat_postEphemeral(
            channel=shortcut["channel"]["id"],
            user=shortcut["user"]["id"],
            text="No audio file found in message",
        )
        return

    files = shortcut["message"]["files"]
    audio_file = next(
        (
            f
            for f in files
            if f["mimetype"].startswith("audio/")
            or f["subtype"] == "slack_audio"
            or f["media_display_type"] == "audio"
        ),
        None,
    )
    if audio_file is None:
        client.chat_postEphemeral(
            channel=shortcut["channel"]["id"],
            user=shortcut["user"]["id"],
            text="No audio file found in message",
        )
        return
    audio_url = audio_file["url_private_download"]
    r = requests.head(audio_url)
    file_size = int(r.headers.get("Content-Length", "0"))
    if file_size > c.MAX_AUDIO_FILE_SIZE:
        client.chat_postEphemeral(
            channel=shortcut["channel"]["id"],
            user=shortcut["user"]["id"],
            text=f"Audio file is too large (max {c.MAX_AUDIO_FILE_SIZE / 1e6} MB)",
        )
        return

    channel_id, ts = shortcut["channel"]["id"], shortcut["message"]["ts"]

    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Transcibe audio"},
            "callback_id": "transcribe_audio_view",
            "private_metadata": channel_id + "," + ts + "," + audio_url,
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
                            for x in c.AUDIO_MODELS
                        ],
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": c.DEFAULT_AUDIO_MODEL,
                            },
                            "value": c.DEFAULT_AUDIO_MODEL,
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
                        "initial_value": "0",
                        "min_value": "0",
                        "max_value": "2",
                    },
                },
                {
                    "type": "input",
                    "block_id": "prompt_input",
                    "optional": True,
                    "label": {"type": "plain_text", "text": "Prompt (optional)"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "prompt_input_action",
                        "min_length": 0,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Enter prompt (optional)",
                        },
                        "initial_value": "Transcribe this audio",
                    },
                },
            ],
            "submit": {"type": "plain_text", "text": "Transcribe"},
        },
    )


def transcribe_audio_submit_lazy(view: dict[str, Any], say: Say):
    values = view["state"]["values"]
    channel_id, thread_ts, audio_url = view["private_metadata"].split(",")
    model = values["model_select"]["model_select_action"]["selected_option"]["value"]
    temperature = values["temperature_input"]["temperature_input_action"]["value"]
    temperature = float(temperature)
    prompt = values["prompt_input"]["prompt_input_action"]["value"]

    transcription = transcribe(audio_url, prompt, model, temperature)

    say(
        transcription,
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

    app.message_shortcut("transcribe_audio")(
        ack=lambda ack: ack(), lazy=[transcribe_audio]
    )
    app.view_submission("transcribe_audio_view")(
        ack=lambda ack: ack(response_action="clear"),
        lazy=[transcribe_audio_submit_lazy],
    )
