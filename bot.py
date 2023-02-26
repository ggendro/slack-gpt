
import re
import json

from client_interface import ClientInterface, OpenaiInterface

class SlackBot():

    def __init__(self, client: ClientInterface, openai_client: OpenaiInterface):
        self.client = client
        self.openai_client = openai_client
        self.id = self.client.get_id()

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
        self.default_save_users = False

        self.default_engine = "text-davinci-003"
        self.valid_engines = [
            "text-davinci-003",
            "text-davinci-002",
            "text-davinci-001",
            "text-curie-001",
            "text-babbage-001",
            "text-ada-001",
            "davinci",
            "curie",
            "babbage",
            "ada",
            "code-davinci-002",
            "code-cushman-001",
        ]
        self.default_temperature = 0.5
        self.min_temperature = 0.0
        self.max_temperature = 1.0

        self.history = {}
        self.default_save_history = True
        self.history_load_path = "history.json"
        self.load_history()

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

    def tag_user(self, user):
        return f"<@{user}>"

    def ping(self, channel, thread, message, user):
        self.client.send_message(channel, thread, f"Hi {self.tag_user(user)}, I'm here! :robot_face:")

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
        users_enabled = (channel not in self.history and self.default_save_users) \
            or (channel in self.history and \
                ((thread not in self.history[channel]["threads"] and self.history[channel]["save_users_enabled"]) 
                 or (thread in self.history[channel]["threads"] and self.history[channel]["threads"][thread]["save_users_enabled"])))
        
        if users_enabled:
            prompt = f"{self.tag_user(user)}: {prompt}"

        if (channel not in self.history and self.default_save_history) \
            or (channel in self.history and \
                ((thread not in self.history[channel]["threads"] and self.history[channel]["history_enabled"]) 
                 or (thread in self.history[channel]["threads"] and self.history[channel]["threads"][thread]["history_enabled"]))):
            self.add_to_history(channel, thread, prompt)
            prompt = "\n".join(self.get_history(channel, thread))
        
        if users_enabled:
            prompt = f"{prompt}\n{self.tag_user(self.id)}: "

        reply = self.openai_client.prompt_chat_gpt(prompt, engine=self.history[channel]["threads"][thread]["engine"], temperature=self.history[channel]["threads"][thread]["temperature"])
        reply = re.sub(r"^\n+", "", reply)
        
        self.client.send_message(channel, thread, reply)

        if self.history[channel]["threads"][thread]["history_enabled"]:
            if users_enabled:
                reply = f"{self.tag_user(self.id)}: {reply}"
            self.add_to_history(channel, thread, reply)


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

        if  (channel not in self.history or thread not in self.history[channel]["threads"] or len(self.history[channel]["threads"][thread]["history"]) < 2):
            self.client.send_message(channel, thread, "No history found for this thread.")
            return
        
        if (not self.history[channel]["threads"][thread]["history_enabled"]):
            self.client.send_message(channel, thread, "History is not enabled for this thread.")
            return
        
        prompt = "\n".join(self.get_history(channel, thread)[:-1])

        if self.history[channel]["threads"][thread]["save_users_enabled"]:
            prompt = f"{prompt}\n{self.tag_user(self.id)}: "

        replies = self.openai_client.prompt_chat_gpt_top_k(prompt, top_k=k, engine=self.history[channel]["threads"][thread]["engine"], temperature=self.history[channel]["threads"][thread]["temperature"])
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

        if self.history[channel]["threads"][thread]["save_users_enabled"]:
            message = f"{self.tag_user(self.id)}: {message}"

        self.get_history(channel, thread)[-1] = message


    def prompt_dalle2(self, channel, thread, prompt, user):
        image_url = self.openai_client.prompt_dalle2(prompt)
        self.client.send_image(channel, thread, image_url)


    def prompt_history(self, channel, thread, *args):
        self.client.send_message(channel, thread, "Here is my current available history:\n" + "".join(self.get_history(channel, thread)))

    def get_history(self, channel, thread):
        if channel not in self.history:
            return []
        if thread not in self.history[channel]["threads"]:
            return []
        return self.history[channel]["threads"][thread]["history"]
    
    def init_history(self, channel, thread):
        if channel not in self.history:
            self.history[channel] = {
                "threads" : {},
                "history_enabled" : self.default_save_history,
                "save_users_enabled" : self.default_save_users,
                "engine" : self.default_engine,
                "temperature" : self.default_temperature,
            }
        if thread not in self.history[channel]["threads"]:
            self.history[channel]["threads"][thread] = {
                "history" : [],
                "history_enabled" : self.history[channel]["history_enabled"],
                "save_users_enabled" : self.history[channel]["save_users_enabled"],
                "engine" : self.history[channel]["engine"],
                "temperature" : self.history[channel]["temperature"],
            }
    
    def add_to_history(self, channel, thread, message):
        self.init_history(channel, thread)
        self.history[channel]["threads"][thread]["history"].append(message)
    
    def save_history(self):
        try:
            print("Saving history...")
            with open(self.history_load_path, "w") as f:
                json.dump(self.history, f)
        except Exception as e:
            print("Failed saving history:", e)
        
    def load_history(self):
        try: 
            print("Loading history...")
            with open(self.history_load_path, "r") as f:
                self.history = json.load(f)
        except Exception as e:
            print("Failed loading history:", e)

    
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
    
    def admin_enable_option_channel(self, channel, thread, option, option_name, value):
        self.init_history(channel, thread)

        if value is None:
            self.client.send_message(channel, thread, f"{option_name} is currently " + ("enabled" if self.history[channel][option] else "disabled") + f" for this channel.")
        else:
            if value.lower() in ["true", "yes", "on", "1"]:
                self.history[channel][option] = True
                self.client.send_message(channel, thread, f"{option_name} is now enabled for this channel.")
            elif value.lower() in ["false", "no", "off", "0"]:
                self.history[channel][option] = False
                self.client.send_message(channel, thread, f"{option_name} is now disabled for this channel.")
            else:
                self.client.send_message(channel, thread, "Invalid value. Please use true, yes, on, 1, false, no, off, 0. Or do not provide a value to see the current status.")
    
    def admin_enable_option_thread(self, channel, thread, option, option_name, value):
        self.init_history(channel, thread)

        if value is None:
            self.client.send_message(channel, thread, f"{option_name} is currently " + ("enabled" if self.history[channel]["threads"][thread][option] else "disabled") + f" for this thread.")
        else:
            if value.lower() in ["true", "yes", "on", "1"]:
                self.history[channel]["threads"][thread][option] = True
                self.client.send_message(channel, thread, f"{option_name} is now enabled for this thread.")
            elif value.lower() in ["false", "no", "off", "0"]:
                self.history[channel]["threads"][thread][option] = False
                self.client.send_message(channel, thread, f"{option_name} is now disabled for this thread.")
            else:
                self.client.send_message(channel, thread, "Invalid value. Please use true, yes, on, 1, false, no, off, 0. Or do not provide a value to see the current status.")

    def admin_set_option_channel(self, channel, thread, option, option_name, value, set_valid_values=None, min_value=None, max_value=None):
        self.init_history(channel, thread)

        if value is None:
            self.client.send_message(channel, thread, f"{option_name} is currently " + str(self.history[channel][option]) + f" for this channel.")
        else:
            try:
                self.history[channel][option] = value
                self.client.send_message(channel, thread, f"{option_name} is now {value} for this channel.")
            except:
                valid_values_text = ""
                if set_valid_values is not None:
                    valid_values_text = " The set of valid values is:\n " + "\n".join(set_valid_values) + "."
                elif min_value is not None and max_value is not None:
                    valid_values_text = f" The valid range is from {min_value} to {max_value}."                   
            
                self.client.send_message(channel, thread, f"Invalid value. Please use a valid value for the option. Or do not provide a value to see the current status.{valid_values_text}")
    
    def admin_set_option_thread(self, channel, thread, option, option_name, value, valid_values=None, min_value=None, max_value=None):
        self.init_history(channel, thread)

        if value is None:
            self.client.send_message(channel, thread, f"{option_name} is currently " + str(self.history[channel]["threads"][thread][option]) + f" for this thread.")
        else:
            try:
                self.history[channel]["threads"][thread][option] = value
                self.client.send_message(channel, thread, f"{option_name} is now {value} for this thread.")
            except:
                valid_values_text = ""
                if valid_values is not None:
                    valid_values_text = " The set of valid values is:\n " + "\n".join(valid_values) + "."
                elif min_value is not None and max_value is not None:
                    valid_values_text = f" The valid range is from {min_value} to {max_value}."
                self.client.send_message(channel, thread, f"Invalid value. Please use a valid value for the option. Or do not provide a value to see the current status.{valid_values_text}")

    def admin_enable_history_channel(self, channel, thread, value=None, *args):
        self.admin_enable_option_channel(channel, thread, "history_enabled", "History", value)

    def admin_enable_history_thread(self, channel, thread, value=None, *args):
        self.admin_enable_option_thread(channel, thread, "history_enabled", "History", value)
    
    def admin_enable_save_usernames_channel(self, channel, thread, value=None, *args):
        self.admin_enable_option_channel(channel, thread, "save_users_enabled", "Saving usernames", value)

    def admin_enable_save_usernames_thread(self, channel, thread, value=None, *args):
        self.admin_enable_option_thread(channel, thread, "save_users_enabled", "Saving usernames", value)
    
    def admin_set_engine_channel(self, channel, thread, value=None, *args):
        self.admin_set_option_channel(channel, thread, "engine", "Engine", value, set_valid_values=self.valid_engines)

    def admin_set_engine_thread(self, channel, thread, value=None, *args):
        self.admin_set_option_thread(channel, thread, "engine", "Engine", value, valid_values=self.valid_engines)

    def admin_set_temperature_channel(self, channel, thread, value=None, *args):
        self.admin_set_option_channel(channel, thread, "temperature", "Temperature", value, min_value=self.min_temperature, max_value=self.max_temperature)

    def admin_set_temperature_thread(self, channel, thread, value=None, *args):
        self.admin_set_option_thread(channel, thread, "temperature", "Temperature", value, min_value=self.min_temperature, max_value=self.max_temperature)

    

