import base64

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.cap.ls").hook(self.on_cap)
        events.on("received.cap.ack").hook(self.on_cap_ack)
        events.on("received.authenticate").hook(self.on_authenticate)
        events.on("received.numeric.903").hook(self.sasl_success)
        events.on("received.numeric.904").hook(self.sasl_failure)

        exports.add("serverset", {"setting": "sasl",
            "help": "Set the sasl username/password for this server",
            "validate": self._validate})

    def _validate(self, s):
        mechanism = s
        if " " in s:
            mechanism, arguments = s.split(" ", 1)
        return {"mechanism": mechanism, "args": arguments}

    def on_cap(self, event):
        has_sasl = "sasl" in event["capabilities"]
        our_sasl = event["server"].get_setting("sasl", None)

        do_sasl = False
        if has_sasl and our_sasl:
            if not event["capabilities"]["sasl"] == None:
                our_mechanism = our_sasl["mechanism"].upper()
                do_sasl = our_mechanism in event["capabilities"
                    ]["sasl"].split(",")
            else:
                do_sasl = True

        if do_sasl:
            event["server"].queue_capability("sasl")

    def on_cap_ack(self, event):
        if "sasl" in event["capabilities"]:
            sasl = event["server"].get_setting("sasl")
            event["server"].send_authenticate(sasl["mechanism"].upper())
            event["server"].wait_for_capability("sasl")

    def on_authenticate(self, event):
        if event["message"] != "+":
            event["server"].send_authenticate("*")
        else:
            sasl = event["server"].get_setting("sasl")
            mechanism = sasl["mechanism"].upper()

            if mechanism == "PLAIN":
                sasl_nick, sasl_pass = sasl["args"].split(":", 1)
                auth_text = "%s\0%s\0%s" % (sasl_nick, sasl_nick, sasl_pass)
            elif mechanism == "EXTERNAL":
                auth_text = "+"
            else:
                raise ValueError("unknown sasl mechanism '%s'" % mechanism)

            if not auth_text == "+":
                auth_text = base64.b64encode(auth_text.encode("utf8"))
                auth_text = auth_text.decode("utf8")
            event["server"].send_authenticate(auth_text)

    def _end_sasl(self, server):
        server.capability_done("sasl")
    def sasl_success(self, event):
        self._end_sasl(event["server"])
    def sasl_failure(self, event):
        self._end_sasl(event["server"])
