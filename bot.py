
import re

from client_interface import ClientInterface, OpenaiInterface

class SlackBot():

    def __init__(self, client: ClientInterface, openai_client: OpenaiInterface):
        self.client = client
        self.openai_client = openai_client

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

        self.history = {}
        self.default_save_history = True

        self.admin_commands = {
            "help" : self.admin_help,
            "history_channel_enabled" : self.admin_enable_history_channel,
            "history_thread_enabled" : self.admin_enable_history_thread,
        }


    def receive_message(self, channel, thread, message, mode=None):
        if mode is not None:
            if mode in self.modes:
                print("mode: ", mode)
                self.modes[mode](channel, thread, message)
            else:
                print("mode: ", mode, "(unrecognised mode).")
                self.client.send_message(channel, thread, "Command not found. Type /help for a list of commands.")
            
        else:
            print("No mode, using default: ", self.default_mode)
            self.modes[self.default_mode](channel, thread, message)


    def ping(self, channel, thread, *args):
        self.client.send_message(channel, thread, "I'm here! :robot_face:")

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


    def prompt_chat_gpt(self, channel, thread, prompt):
        if (channel not in self.history and self.default_save_history) \
            or (channel in self.history and \
                ((thread not in self.history[channel]["threads"] and self.history[channel]["history_enabled"]) 
                 or (thread in self.history[channel]["threads"] and self.history[channel]["threads"][thread]["history_enabled"]))):
            self.add_to_history(channel, thread, prompt)
            prompt = "\n".join(self.get_history(channel, thread))

        reply = self.openai_client.prompt_chat_gpt(prompt)
        reply = re.sub(r"^\n+", "", reply)

        if self.history[channel]["threads"][thread]["history_enabled"]:
            self.add_to_history(channel, thread, reply)

        self.client.send_message(channel, thread, reply)

    def top_k(self, channel, thread, k=5, *args):
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
        replies = self.openai_client.prompt_chat_gpt_top_k(prompt, top_k=k)
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
        self.get_history(channel, thread)[-1] = message
        self.client.send_message(channel, thread, message)

    def prompt_dalle2(self, channel, thread, prompt):
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
            }
        if thread not in self.history[channel]["threads"]:
            self.history[channel]["threads"][thread] = {
                "history" : [],
                "history_enabled" : self.history[channel]["history_enabled"],
            }
    
    def add_to_history(self, channel, thread, message):
        self.init_history(channel, thread)
        self.history[channel]["threads"][thread]["history"].append(message)

    
    def admin(self, channel, thread, prompt):
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
                + "history_thread_enabled: Enable or disable history for the current thread."
        
        self.client.send_message(channel, thread, message)

    def admin_enable_history_channel(self, channel, thread, value=None, *args):
        self.init_history(channel, thread)

        if value is None:
            self.client.send_message(channel, thread, "History is currently " + ("enabled" if self.history[channel]["history_enabled"] else "disabled") + " for this channel.")
        else:
            if value.lower() in ["true", "yes", "on", "1"]:
                self.history[channel]["history_enabled"] = True
                self.client.send_message(channel, thread, "History is now enabled for this channel.")
            elif value.lower() in ["false", "no", "off", "0"]:
                self.history[channel]["history_enabled"] = False
                self.client.send_message(channel, thread, "History is now disabled for this channel.")
            else:
                self.client.send_message(channel, thread, "Invalid value. Please use true, yes, on, 1, false, no, off, 0. Or do not provide a value to see the current status.")

    def admin_enable_history_thread(self, channel, thread, value=None, *args):
        self.init_history(channel, thread)

        if value is None:
            self.client.send_message(channel, thread, "History is currently " + ("enabled" if self.history[channel]["threads"][thread]["history_enabled"] else "disabled") + " for this thread.")
        else:
            if value.lower() in ["true", "yes", "on", "1"]:
                self.history[channel]["threads"][thread]["history_enabled"] = True
                self.client.send_message(channel, thread, "History is now enabled for this thread.")
            elif value.lower() in ["false", "no", "off", "0"]:
                self.history[channel]["threads"][thread]["history_enabled"] = False
                self.client.send_message(channel, thread, "History is now disabled for this thread.")
            else:
                self.client.send_message(channel, thread, "Invalid value. Please use true, yes, on, 1, false, no, off, 0. Or do not provide a value to see the current status.")


