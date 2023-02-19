
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
            "dalle2": self.prompt_dalle2,
            "history": self.prompt_history
        }
        self.default_mode = "prompt"
        self.save_users = False

        self.history = {}
        self.save_history = True


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

    def admin(self, channel, thread, *args):
        pass

    def help(self, channel, thread, *args):
        message = "The help command provides you with a list of available commands and their functions. Commands: \n"\
                    + "ping: I'm here! :robot_face: \n"\
                    + "help: This message \n"\
                    + "admin: Admin commands \n"\
                    + "prompt: Create a prompt for ChatGPT \n"\
                    + "dalle2: Create a prompt for DALLE2 [NOT READY] \n"\
                    + "history: View history of conversations"
        
        self.client.send_message(channel, thread, message)

    def prompt_chat_gpt(self, channel, thread, prompt):
        if self.save_history:
            self.add_to_history(channel, thread, prompt)
            prompt = "".join(self.get_history(channel, thread))
            
        reply = self.openai_client.prompt_chat_gpt(prompt)

        if self.save_history:
            self.add_to_history(channel, thread, reply)

        self.client.send_message(channel, thread, reply)

    def prompt_dalle2(self, channel, thread, prompt):
        pass


    def prompt_history(self, channel, thread, *args):
        self.client.send_message(channel, thread, "Here is my current available history:\n" + "".join(self.get_history(channel, thread)))

    def get_history(self, channel, thread):
        if channel not in self.history:
            return []
        if thread not in self.history[channel]:
            return []
        return self.history[channel][thread]
    
    def add_to_history(self, channel, thread, message):
        if channel not in self.history:
            self.history[channel] = {}
        if thread not in self.history[channel]:
            self.history[channel][thread] = []
        self.history[channel][thread].append(message)