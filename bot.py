
import re
import json
from typing import Optional

from client_interface import ClientInterface, OpenaiInterface

class HistoryCT():
    """
    History class for channels and threads
    """

    def __init__(self, history_save_path : str = "history.json", default_options : dict = {}):
        self.history = {}
        self.history_save_path = history_save_path
        self.default_options = default_options
    
    def init_history(self, channel, thread):
        if channel not in self.history:
            self.history[channel] = {
                "threads" : {},
                **self.default_options
            }
        if thread not in self.history[channel]["threads"]:
            self.history[channel]["threads"][thread] = {
                "history" : [],
                **{opt_name: self.history[channel][opt_name] for opt_name in self.default_options.keys()},
            }

    def get_history(self, channel, thread):
        if channel not in self.history:
            return []
        if thread not in self.history[channel]["threads"]:
            return []
        return self.history[channel]["threads"][thread]["history"]
    
    def add_to_history(self, channel, thread, message, user=None):
        self.init_history(channel, thread)
        self.history[channel]["threads"][thread]["history"].append({"user" : user, "message" : message})
    
    def get_option(self, channel : Optional[str] = None, thread : Optional[str] = None, option_name : str = ""):
        if channel is None or channel not in self.history:
            return self.default_options[option_name]
        if thread is None or thread not in self.history[channel]["threads"]:
            return self.history[channel][option_name]
        return self.history[channel]["threads"][thread][option_name]
    
    def set_option(self, channel : Optional[str] = None, thread : Optional[str] = None, option_name : str = "", option_value = None):
        if channel is None:
            self.default_options[option_name] = option_value
        if thread is None:
            self.history[channel][option_name] = option_value
        self.history[channel]["threads"][thread][option_name] = option_value

    
    def save_history(self, path: str = None):
        path = path if path is not None else self.history_save_path
        try:
            print("Saving history...")
            with open(self.history_save_path, "w") as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            print("Failed saving history:", e)
        
    def load_history(self, path: str = None):
        path = path if path is not None else self.history_save_path
        try: 
            print("Loading history...")
            with open(path, "r") as f:
                self.history = json.load(f)
        except Exception as e:
            print("Failed loading history:", e)
    

class SlackBot():

    def __init__(self, client: ClientInterface, openai_client: OpenaiInterface):
        self.client = client
        self.openai_client = openai_client
        self.id = self.client.get_id()
        self.openai_client.assistant_name = self._tag_user(self.id)

        self.modes = {
            "ping": self.ping,
            "help": self.help,
            "admin": self.admin,
            "prompt": self.prompt_chat_gpt,
            "topK": self.top_k,
            "dalle2": self.prompt_dalle2,
            "history": self.prompt_history
        }
        self.default_mode = "prompt"

        self.valid_engines = self.openai_client.get_engines()
        self.min_temperature = 0.0
        self.max_temperature = 1.0

        self.history = HistoryCT(
            history_save_path="history.json", 
            default_options={
                "history_enabled" : True,
                "save_users_enabled" : False,
                "engine" : "gpt-3.5-turbo",
                "temperature" : 0.5,
            })
        self.history.load_history()

        self.admin_commands = {
            "help" : self.admin_help,
            "history_channel_enabled" : self.admin_enable_history_channel,
            "history_thread_enabled" : self.admin_enable_history_thread,
            "save_usernames_channel_enabled" : self.admin_enable_save_usernames_channel,
            "save_usernames_thread_enabled" : self.admin_enable_save_usernames_thread,
            "engine_channel" : self.admin_set_engine_channel,
            "engine_thread" : self.admin_set_engine_thread,
            "temperature_channel" : self.admin_set_temperature_channel,
            "temperature_thread" : self.admin_set_temperature_thread,
        }

    def save_history(self):
        self.history.save_history()


    def receive_message(self, channel, thread, message, user, mode=None):
        if mode is not None:
            if mode in self.modes:
                print("mode: ", mode)
                self.modes[mode](channel, thread, message, user)
            else:
                print("mode: ", mode, "(unrecognised mode).")
                self.client.send_message(channel, thread, "Command not found. Type /help for a list of commands.")
            
        else:
            print("No mode, using default: ", self.default_mode)
            self.modes[self.default_mode](channel, thread, message, user)

    def _tag_user(self, user):
        return f"<@{user}>"

    def ping(self, channel, thread, message, user):
        self.client.send_message(channel, thread, f"Hi {self._tag_user(user)}, I'm here! :robot_face:")

    def help(self, channel, thread, *args):
        message = "The help command provides you with a list of available commands and their functions. Commands: \n"\
                    + "ping: I'm here! :robot_face: \n"\
                    + "help: This message. \n"\
                    + "admin: Admin commands. Type /admin help for more details. \n"\
                    + "prompt: Create a prompt for ChatGPT. \n"\
                    + "topK: Display the top-K replies of ChatGPT for the last prompt. \n"\
                    + "dalle2: Create a prompt for DALLE2. \n"\
                    + "history: View history of conversations."
        
        self.client.send_message(channel, thread, message)


    def prompt_chat_gpt(self, channel, thread, prompt, user):
        users_enabled = self.history.get_option(channel, thread, "save_users_enabled")
        history_enabled = self.history.get_option(channel, thread, "history_enabled")

        context = []
        if history_enabled:
            context = self.history.get_history(channel, thread)
            self.history.add_to_history(channel, thread, prompt, user)
        
        context = [{"user": self._tag_user(entry["user"]), "message": entry['message']} for entry in context]
        prompt = {"user": self._tag_user(user), "message": prompt}
        if users_enabled:
            context = [{"user": entry["user"], "message": f"{entry['user']}: {entry['message']}"} for entry in context]
            prompt = [
                        {"user": prompt["user"], "message": f"{prompt['user']}: {prompt['message']}"},
                        {"user": self._tag_user(self.id), "message": f"{self._tag_user(self.id)}: "} # This is the start of the reply for the assistant
                    ]

        reply = self.openai_client.prompt_chat_gpt(prompt, context, engine=self.history.get_option(channel, thread, "engine"), temperature=self.history.get_option(channel, thread, "temperature"))
        reply = re.sub(r"^\n+", "", reply)
        
        self.client.send_message(channel, thread, reply)

        if history_enabled:
            self.history.add_to_history(channel, thread, reply, self.id)


    def top_k(self, channel, thread, k, user):
        if type(k) is not int:
            try:
                k = int(k)
            except ValueError:
                self.client.send_message(channel, thread, "Please enter a valid integer for k.")
                return
        
        if k < 1 or k > 10:
            self.client.send_message(channel, thread, "Please enter a valid integer for k (1-10).")
            return

        if len(self.history.get_history(channel, thread)) < 2:
            self.client.send_message(channel, thread, "No history found for this thread.")
            return
        
        if not self.history.get_option(channel, thread, "history_enabled"):
            self.client.send_message(channel, thread, "History is not enabled for this thread.")
            return
        
        history = self.history.get_history(channel, thread)
        context = [{"user": self._tag_user(entry["user"]), "message": entry['message']} for entry in history[:-2]]
        prompt = {"user": self._tag_user(history[-2]['user']), "message": history[-2]['message']}
        
        if self.history.get_option(channel, thread, "save_users_enabled"):
            context = [{"user": entry["user"], "message": f"{entry['user']}: {entry['message']}"} for entry in context]
            prompt = [
                        {"user": prompt["user"], "message": f"{prompt['user']}: {prompt['message']}"},
                        {"user": self._tag_user(self.id), "message": f"{self._tag_user(self.id)}: "} # This is the start of the reply for the assistant
                    ]

        replies = self.openai_client.prompt_chat_gpt_top_k(prompt, top_k=k, engine=self.history.get_option(channel, thread, "engine"), temperature=self.history.get_option(channel, thread, "temperature"))
        replies = [re.sub(r"^\n+", "", reply) for reply in replies]
        replies_text = "\n".join([f"{i+1}. {reply}" for i, reply in enumerate(replies)])

        self.client.send_message(channel, thread, f"Top-{k} answers from ChatGPT for the last prompt:\n{replies_text}", attachments= [
        {
            "text": "Select one answer to replace the previous reply. Please, do not prompt another query in the meantime.",
            "callback_id": "top_k_callback",
            "attachment_type": "default",
            "actions": [{
                    "name": "top_k",
                    "text": f"{i+1}",
                    "type": "button",
                    "value": reply
                } for i, reply in enumerate(replies)]
        }
    ])
    
    def top_k_callback(self, channel, thread, message):
        self.client.send_message(channel, thread, message)
        self.history.get_history(channel, thread)[-1] = {"user" : self.id, "message" : message} # replace last message in history with new selected one


    def prompt_dalle2(self, channel, thread, prompt, user):
        image_url = self.openai_client.prompt_dalle2(prompt)
        self.client.send_image(channel, thread, image_url)


    def prompt_history(self, channel, thread, *args):
        history = self.history.get_history(channel, thread)
        if len(history) == 0:
            self.client.send_message(channel, thread, "No history found for this thread.")
        else:
            if self.history.get_option(channel, thread, "save_users_enabled"):
                history = [f"{self._tag_user(entry['user'])}: {entry['message']}" for entry in history]
            else:
                history = [entry["message"] for entry in history]
            self.client.send_message(channel, thread, "Here is my current available history:\n" + "".join(history))

    
    def admin(self, channel, thread, prompt, user):
        prompt = re.sub(r"^\s*", "", prompt)
        command, *params = re.split(r"\s+", prompt)

        if command in self.admin_commands:
            self.admin_commands[command](channel, thread, *params)
        else:
            self.admin_help(channel, thread, *params)

    def admin_help(self, channel, thread, *args):
        message = "The admin help command provides you with a list of available admin commands and their functions. Commands: \n"\
                + "help: This message. \n"\
                + "history_channel_enabled: Enable or disable history for the current channel. \n"\
                + "history_thread_enabled: Enable or disable history for the current thread. \n"\
                + "save_usernames_channel_enabled: Enable or disable the save of usernames for the current channel. \n"\
                + "save_usernames_thread_enabled: Enable or disable the save of usernames for the current thread. \n"\
                + "engine_channel: Set the engine for the current channel. \n"\
                + "engine_thread: Set the engine for the current thread. \n"\
                + "temperature_channel: Set the temperature for the current channel. \n"\
                + "temperature_thread: Set the temperature for the current thread."
        
        self.client.send_message(channel, thread, message)
    
    def _admin_enable_option_channel(self, channel, thread, option, option_name, value):
        self.history.init_history(channel, thread) # Ensure that the history is initialized for this channel and thread

        if value is None:
            self.client.send_message(channel, thread, f"{option_name} is currently " + ("enabled" if self.history.get_option(channel, thread=None, option_name=option) else "disabled") + f" for this channel.")
        else:
            if value.lower() in ["true", "yes", "on", "1"]:
                self.history.set_option(channel, thread=None, option_name=option, option_value=True)
                self.client.send_message(channel, thread, f"{option_name} is now enabled for this channel.")
            elif value.lower() in ["false", "no", "off", "0"]:
                self.history.set_option(channel, thread=None, option_name=option, option_value=False)
                self.client.send_message(channel, thread, f"{option_name} is now disabled for this channel.")
            else:
                self.client.send_message(channel, thread, "Invalid value. Please use true, yes, on, 1, false, no, off, 0. Or do not provide a value to see the current status.")
    
    def _admin_enable_option_thread(self, channel, thread, option, option_name, value):
        self.history.init_history(channel, thread) # Ensure that the history is initialized for this channel and thread

        if value is None:
            self.client.send_message(channel, thread, f"{option_name} is currently " + ("enabled" if self.history.get_option(channel, thread, option) else "disabled") + f" for this thread.")
        else:
            if value.lower() in ["true", "yes", "on", "1"]:
                self.history.set_option(channel, thread, option, True)
                self.client.send_message(channel, thread, f"{option_name} is now enabled for this thread.")
            elif value.lower() in ["false", "no", "off", "0"]:
                self.history.set_option(channel, thread, option, False)
                self.client.send_message(channel, thread, f"{option_name} is now disabled for this thread.")
            else:
                self.client.send_message(channel, thread, "Invalid value. Please use true, yes, on, 1, false, no, off, 0. Or do not provide a value to see the current status.")

    def _admin_set_option_channel(self, channel, thread, option, option_name, value, valid_values=None, min_value=None, max_value=None):
        self.history.init_history(channel, thread) # Ensure that the history is initialized for this channel and thread

        if value is None:
            self.client.send_message(channel, thread, f"{option_name} is currently " + str(self.history.get_option(channel, thread=None, option_name=option)) + f" for this channel.")
        else:
            try:
                if (valid_values is not None and value not in valid_values) or (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
                    raise ValueError
                
                self.history.set_option(channel, thread=None, option_name=option, option_value=value)
                self.client.send_message(channel, thread, f"{option_name} is now {value} for this channel.")
            except:
                valid_values_text = ""
                if valid_values is not None:
                    valid_values_text = " The set of valid values is:\n " + "\n".join(valid_values) + "."
                elif min_value is not None and max_value is not None:
                    valid_values_text = f" The valid range is from {min_value} to {max_value}."                   
            
                self.client.send_message(channel, thread, f"Invalid value. Please use a valid value for the option. Or do not provide a value to see the current status.{valid_values_text}")
    
    def _admin_set_option_thread(self, channel, thread, option, option_name, value, valid_values=None, min_value=None, max_value=None):
        self.history.init_history(channel, thread) # Ensure that the history is initialized for this channel and thread

        if value is None:
            self.client.send_message(channel, thread, f"{option_name} is currently " + str(self.history.get_option(channel, thread, option)) + f" for this thread.")
        else:
            try:
                if (valid_values is not None and value not in valid_values) or (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
                    raise ValueError

                self.history.set_option(channel, thread, option, value)
                self.client.send_message(channel, thread, f"{option_name} is now {value} for this thread.")
            except:
                valid_values_text = ""
                if valid_values is not None:
                    valid_values_text = " The set of valid values is:\n " + "\n".join(valid_values) + "."
                elif min_value is not None and max_value is not None:
                    valid_values_text = f" The valid range is from {min_value} to {max_value}."
                self.client.send_message(channel, thread, f"Invalid value. Please use a valid value for the option. Or do not provide a value to see the current status.{valid_values_text}")

    def admin_enable_history_channel(self, channel, thread, value=None, *args):
        self._admin_enable_option_channel(channel, thread, "history_enabled", "History", value)

    def admin_enable_history_thread(self, channel, thread, value=None, *args):
        self._admin_enable_option_thread(channel, thread, "history_enabled", "History", value)
    
    def admin_enable_save_usernames_channel(self, channel, thread, value=None, *args):
        self._admin_enable_option_channel(channel, thread, "save_users_enabled", "Saving usernames", value)

    def admin_enable_save_usernames_thread(self, channel, thread, value=None, *args):
        self._admin_enable_option_thread(channel, thread, "save_users_enabled", "Saving usernames", value)
    
    def admin_set_engine_channel(self, channel, thread, value=None, *args):
        self._admin_set_option_channel(channel, thread, "engine", "Engine", value, valid_values=self.valid_engines)

    def admin_set_engine_thread(self, channel, thread, value=None, *args):
        self._admin_set_option_thread(channel, thread, "engine", "Engine", value, valid_values=self.valid_engines)

    def admin_set_temperature_channel(self, channel, thread, value=None, *args):
        self._admin_set_option_channel(channel, thread, "temperature", "Temperature", value, min_value=self.min_temperature, max_value=self.max_temperature)

    def admin_set_temperature_thread(self, channel, thread, value=None, *args):
        self._admin_set_option_thread(channel, thread, "temperature", "Temperature", value, min_value=self.min_temperature, max_value=self.max_temperature)

    

