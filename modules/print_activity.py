import datetime
import EventManager

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot

        events.on("received.message.channel").hook(
            self.channel_message, priority=EventManager.PRIORITY_HIGH)
        events.on("self.message.channel").hook(
            self.self_channel_message)

        events.on("received.notice.channel").hook(
            self.channel_notice, priority=EventManager.PRIORITY_HIGH)
        events.on("received.notice.private").hook(
            self.private_notice, priority=EventManager.PRIORITY_HIGH)
        events.on("received.server-notice").hook(
            self.server_notice, priority=EventManager.PRIORITY_HIGH)

        events.on("received.join").hook(self.join)
        events.on("self.join").hook(self.self_join)

        events.on("received.part").hook(self.part)
        events.on("self.part").hook(self.self_part)

        events.on("received.nick").hook(self.on_nick)
        events.on("self.nick").hook(self.on_nick)

        events.on("received.quit").hook(self.on_quit)

        events.on("received.kick").hook(self.kick)
        events.on("self.kick").hook(self.self_kick)

        events.on("received.topic").hook(self.on_topic)
        events.on("received.numeric.333").hook(self.on_333)

        events.on("received.mode.channel").hook(self.mode)

    def print_line(self, event, line, channel=None):
        timestamp = datetime.datetime.now().isoformat()
        target = str(event["server"])
        if not channel == None:
            target += channel
        self.bot.log.info("%s | %s", [target, line])

    def _on_message(self, event, nickname):
        if not self.bot.args.verbose:
            if event["action"]:
                self.print_line(event, "* %s %s" % (
                    nickname, event["message"]),
                    channel=event["channel"].name)
            else:
                self.print_line(event, "<%s> %s" % (
                    nickname, event["message"]),
                    channel=event["channel"].name)
    def channel_message(self, event):
        self._on_message(event, event["user"].nickname)
    def self_channel_message(self, event):
        self._on_message(event, event["server"].nickname)

    def _on_notice(self, event, target):
        self.print_line(event, "(notice->%s) <%s> %s" % (
            target, event["user"].nickname, event["message"]))
    def channel_notice(self, event):
        self._on_notice(event, event["channel"].name)
    def private_notice(self, event):
        self._on_notice(event, event["server"].nickname)
    def server_notice(self, event):
        self.print_line(event, "(server notice) %s" % event["message"])

    def _on_join(self, event, nickname):
        if not self.bot.args.verbose:
            self.print_line(event, "%s joined %s" % (nickname,
                event["channel"].name))
    def join(self, event):
        self._on_join(event, event["user"].nickname)
    def self_join(self, event):
        self._on_join(event, event["server"].nickname)

    def _on_part(self, event, nickname):
        if not self.bot.args.verbose:
            self.print_line(event, "%s left %s%s" % (nickname,
                event["channel"].name, "" if not event[
                "reason"] else " (%s)" % event["reason"]))
    def part(self, event):
        self._on_part(event, event["user"].nickname)
    def self_part(self, event):
        self._on_part(event, event["server"].nickname)

    def on_nick(self, event):
        if not self.bot.args.verbose:
            self.print_line(event, "%s changed nickname to %s" % (
                event["old_nickname"], event["new_nickname"]))

    def on_quit(self, event):
        if not self.bot.args.verbose:
            self.print_line(event, "%s quit%s" % (event["user"].nickname,
                "" if not event["reason"] else " (%s)" % event["reason"]))

    def _on_kick(self, event, nickname):
        if not self.bot.args.verbose:
            self.print_line(event, "%s kicked %s from %s%s" % (
                event["user"].nickname, nickname, event["channel"].name,
                "" if not event["reason"] else " (%s)" % event["reason"]))
    def kick(self, event):
        self._on_kick(event, event["target_user"].nickname)
    def self_kick(self, event):
        self._on_kick(event, event["server"].nickname)

    def _on_topic(self, event, setter, action, topic, channel):
        self.print_line(event, "topic %s by %s: %s" % (action, setter,
            topic), channel=channel.name)
    def on_topic(self, event):
        self._on_topic(event, event["user"].nickname, "changed",
            event["topic"], event["channel"])
    def on_333(self, event):
        self._on_topic(event, event["setter"], "set",
            event["channel"].topic, event["channel"])

    def mode(self, event):
        args = " ".join(event["mode_args"])
        if args:
            args = " %s" % args
        self.print_line(event, "%s set mode %s%s" % (
            event["user"].nickname, "".join(event["modes"]),
            args), channel=event["channel"].name)
