import hashlib

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.command.hash").hook(self.hash, min_args=2,
            help="Hash a string", usage="<algo> <string>")

    def hash(self, event):
        algorithm = event["args_split"][0].lower()
        if algorithm in hashlib.algorithms_available:
            phrase = " ".join(event["args_split"][1:])
            cipher_text = hashlib.new(algorithm, phrase.encode("utf8")
                ).hexdigest()
            event["stdout"].write("%s -> %s" % (phrase, cipher_text))
        else:
            event["stderr"].write("Unknown algorithm provided")
