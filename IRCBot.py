import os, select, sys, threading, time, traceback, uuid

import EventManager, Exports, IRCLineHandler, IRCServer, Logging
import ModuleManager, Timer

class Bot(object):
    def __init__(self):
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.args = None
        self.database = None
        self.config = None
        self.bot_directory = os.path.dirname(os.path.realpath(__file__))
        self.servers = {}
        self.running = True
        self.poll = select.epoll()
        self._events = EventManager.EventHook(self)
        self._exports = Exports.Exports()
        self.modules = ModuleManager.ModuleManager(self, self._events,
            self._exports)
        self.log = Logging.Log(self)
        self.line_handler = IRCLineHandler.LineHandler(self, self._events)
        self.timers = []
        self._events.on("timer.reconnect").hook(self.reconnect)
        self._events.on("boot.done").hook(self.setup_timers)

    def add_server(self, server_id, connect=True):
        (_, alias, hostname, port, password, ipv4, tls, nickname,
            username, realname) = self.database.servers.get(server_id)

        new_server = IRCServer.Server(self, self._events, server_id, alias,
            hostname, port, password, ipv4, tls, nickname, username,
            realname)
        if not new_server.get_setting("connect", True):
            return
        self._events.on("new.server").call(server=new_server)
        if connect and new_server.get_setting("connect", True):
            self.connect(new_server)
        return new_server
    def connect(self, server):
        try:
            server.connect()
        except:
            sys.stderr.write("Failed to connect to %s\n" % str(server))
            traceback.print_exc()
            return False
        self.servers[server.fileno()] = server
        self.poll.register(server.fileno(), select.EPOLLOUT)
        return True
    def setup_timers(self, event):
        for setting, value in self.find_settings("timer-%"):
            id = setting.split("timer-", 1)[1]
            self.add_timer(value["event-name"], value["delay"], value[
                "next-due"], id, **value["kwargs"])
    def timer_setting(self, timer):
        self.set_setting("timer-%s" % timer.id, {
            "event-name": timer.event_name, "delay": timer.delay,
            "next-due": timer.next_due, "kwargs": timer.kwargs})
    def timer_setting_remove(self, timer):
        self.timers.remove(timer)
        self.del_setting("timer-%s" % timer.id)
    def add_timer(self, event_name, delay, next_due=None, id=None, persist=True,
            **kwargs):
        id = id or uuid.uuid4().hex
        timer = Timer.Timer(id, self, self._events, event_name, delay,
            next_due, **kwargs)
        if id:
            timer.id = id
        elif persist:
            self.timer_setting(timer)
        self.timers.append(timer)
    def next_timer(self):
        next = None
        for timer in self.timers:
            time_left = timer.time_left()
            if next == None or time_left < next:
                next = time_left

        if next == None:
            return None
        if next < 0:
            return 0
        return next
    def call_timers(self):
        for timer in self.timers[:]:
            if timer.due():
                timer.call()
                if timer.done():
                    self.timer_setting_remove(timer)
    def next_send(self):
        next = None
        for server in self.servers.values():
            timeout = server.send_throttle_timeout()
            if server.waiting_send() and (next == None or timeout < next):
                next = timeout
        return next

    def next_ping(self):
        timeouts = []
        for server in self.servers.values():
            timeout = server.until_next_ping()
            if not timeout == None:
                timeouts.append(timeout)
        if not timeouts:
            return None
        return min(timeouts)
    def next_read_timeout(self):
        timeouts = []
        for server in self.servers.values():
            timeouts.append(server.until_read_timeout())
        if not timeouts:
            return None
        return min(timeouts)

    def get_poll_timeout(self):
        timeouts = []
        timeouts.append(self.next_timer())
        timeouts.append(self.next_send())
        timeouts.append(self.next_ping())
        timeouts.append(self.next_read_timeout())
        return min([timeout for timeout in timeouts if not timeout == None])

    def register_read(self, server):
        self.poll.modify(server.fileno(), select.EPOLLIN)
    def register_write(self, server):
        self.poll.modify(server.fileno(), select.EPOLLOUT)
    def register_both(self, server):
        self.poll.modify(server.fileno(),
            select.EPOLLIN|select.EPOLLOUT)

    def disconnect(self, server):
        try:
            self.poll.unregister(server.fileno())
        except FileNotFoundError:
            pass
        del self.servers[server.fileno()]

    def reconnect(self, event):
        server_details = self.database.servers.get(event["server_id"])
        server = self.add_server(*(server_details + (False,)))
        if self.connect(server):
            self.servers[server.fileno()] = server
        else:
            event["timer"].redo()

    def set_setting(self, setting, value):
        self.database.bot_settings.set(setting, value)
    def get_setting(self, setting, default=None):
        return self.database.bot_settings.get(setting, default)
    def find_settings(self, pattern, default=[]):
        return self.database.bot_settings.find(pattern, default)
    def find_settings_prefix(self, prefix, default=[]):
        return self.database.bot_settings.find_prefix(
            prefix, default)
    def del_setting(self, setting):
        self.database.bot_settings.delete(setting)

    def run(self):
        while self.running:
            self.lock.acquire()
            events = self.poll.poll(self.get_poll_timeout())
            self.call_timers()
            for fd, event in events:
                if fd in self.servers:
                    server = self.servers[fd]
                    if event & select.EPOLLIN:
                        lines = server.read()
                        for line in lines:
                            if self.args.verbose:
                                self.log.info("<%s | %s", [str(server), line])
                            else:
                                self.log.debug("%s (raw) | %s", [str(server),
                                    line])
                            server.parse_line(line)
                    elif event & select.EPOLLOUT:
                        server._send()
                        self.register_read(server)
                    elif event & select.EPULLHUP:
                        print("hangup")
                        server.disconnect()

            for server in list(self.servers.values()):
                if server.read_timed_out():
                    print("pingout from %s" % str(server))
                    server.disconnect()
                elif server.ping_due() and not server.ping_sent:
                    server.send_ping()
                    server.ping_sent = True
                if not server.connected:
                    self.disconnect(server)

                    reconnect_delay = self.config.get("reconnect-delay", 10)
                    self.add_timer("reconnect", reconnect_delay, None, None, False,
                        server_id=server.id)

                    print("disconnected from %s, reconnecting in %d seconds" % (
                        str(server), reconnect_delay))
                elif server.waiting_send() and server.throttle_done():
                    self.register_both(server)
            self.lock.release()
