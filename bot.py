
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
            "history": self.history
        }
        self.default_mode = "prompt"
        self.save_users = False
        self.save_history = False


    def receive_message(self, channel, thread, message):
        if message.startswith("/"):
            mode = message.split(" ")[0][1:]
            message = " ".join(message.split(" ")[1:])

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
                    + "history: View history of conversations \n"
        
        self.client.send_message(channel, thread, message)

    def prompt_chat_gpt(self, channel, thread, prompt):
        reply = self.openai_client.prompt_chat_gpt(prompt)
        self.client.send_message(channel, thread, reply)

    def history(self, channel, thread, *args):
        pass