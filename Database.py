import json, os, sqlite3, threading, time

class Table(object):
    def __init__(self, database):
        self.database = database

class Servers(Table):
    def add(self, alias, hostname, port, password, ipv4, tls, nickname,
            username=None, realname=None):
        username = username or nickname
        realname = realname or nickname
        self.database.execute(
            """INSERT INTO servers (alias, hostname, port, password, ipv4,
            tls, nickname, username, realname) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?)""",
            [hostname, port, password, ipv4, tls, nickname, username, realname])
    def get_all(self):
        return self.database.execute_fetchall(
            "SELECT server_id, alias FROM servers")
    def get(self, id):
        return self.database.execute_fetchone(
            """SELECT server_id, alias, hostname, port, password, ipv4,
            tls, nickname, username, realname FROM servers WHERE
            server_id=?""",
            [id])

class Channels(Table):
    def add(self, server_id, name):
        self.database.execute("""INSERT OR IGNORE INTO channels
            (server_id, name) VALUES (?, ?)""",
            [server_id, name.lower()])
    def delete(self, channel_id):
        self.database.execute("DELETE FROM channels WHERE channel_id=?",
            [channel_id])
    def get_id(self, server_id, name):
        value = self.database.execute_fetchone("""SELECT channel_id FROM
            channels WHERE server_id=? AND name=?""",
            [server_id, name.lower()])
        return value if value == None else value[0]

class Users(Table):
    def add(self, server_id, nickname):
        self.database.execute("""INSERT OR IGNORE INTO users
            (server_id, nickname) VALUES (?, ?)""",
            [server_id, nickname.lower()])
    def delete(self, user_id):
        self.database.execute("DELETE FROM users WHERE user_id=?",
            [user_id])
    def get_id(self, server_id, nickname):
        value = self.database.execute_fetchone("""SELECT user_id FROM
            users WHERE server_id=? and nickname=?""",
            [server_id, nickname.lower()])
        return value if value == None else value[0]

class BotSettings(Table):
    def set(self, setting, value):
        self.database.execute(
            "INSERT OR REPLACE INTO bot_settings VALUES (?, ?)",
            [setting.lower(), json.dumps(value)])
    def get(self, setting, default=None):
        value = self.database.execute_fetchone(
            "SELECT value FROM bot_settings WHERE setting=?",
            [setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def find(self, pattern, default=[]):
        values = self.database.execute_fetchall(
            "SELECT setting, value FROM bot_settings WHERE setting LIKE ?",
            [pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_prefix(self, prefix, default=[]):
        return self.find_bot_settings("%s%" % prefix, default)
    def delete(self, setting):
        self.database.execute(
            "DELETE FROM bot_settings WHERE setting=?",
            [setting.lower()])

class ServerSettings(Table):
    def set(self, server_id, setting, value):
        self.database.execute(
            "INSERT OR REPLACE INTO server_settings VALUES (?, ?, ?)",
            [server_id, setting.lower(), json.dumps(value)])
    def get(self, server_id, setting, default=None):
        value = self.database.execute_fetchone(
            """SELECT value FROM server_settings WHERE
            server_id=? AND setting=?""",
            [server_id,setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def find(self, server_id, pattern, default=[]):
        values = self.database.execute_fetchall(
            """SELECT setting, value FROM server_settings WHERE
            server_id=? AND setting LIKE ?""",
            [server_id, pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_prefix(self, server_id, prefix, default=[]):
        return self.find_server_settings(server_id, "%s%" % prefix, default)
    def delete(self, server_id, setting):
        self.database.execute(
            "DELETE FROM server_settings WHERE server_id=? AND setting=?",
            [server_id, setting.lower()])

class ChannelSettings(Table):
    def set(self, channel_id, setting, value):
        self.database.execute(
            "INSERT OR REPLACE INTO channel_settings VALUES (?, ?, ?)",
            [channel_id, setting.lower(), json.dumps(value)])
    def get(self, channel_id, setting, default=None):
        value = self.database.execute_fetchone(
            """SELECT value FROM channel_settings WHERE
            channel_id=? AND setting=?""", [channel_id, setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def find(self, channel_id, pattern, default=[]):
        values = self.database.execute_fetchall(
            """SELECT setting, value FROM channel_settings WHERE
            channel_id=? setting LIKE '?'""", [channel_id, pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_prefix(self, channel_id, prefix, default=[]):
        return self.find_channel_settings(channel_id, "%s%" % prefix,
            default)
    def delete(self, channel_id, setting):
        self.database.execute(
            """DELETE FROM channel_settings WHERE channel_id=?
            AND setting=?""", [channel_id, setting.lower()])

class UserSettings(Table):
    def set(self, user_id, setting, value):
        self.database.execute(
            "INSERT OR REPLACE INTO user_settings VALUES (?, ?, ?)",
            [user_id, setting.lower(), json.dumps(value)])
    def get(self, user_id, setting, default=None):
        value = self.database.execute_fetchone(
            """SELECT value FROM user_settings WHERE
            user_id=? and setting=?""", [user_id, setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def find_all_by_setting(self, server_id, setting, default=[]):
        values = self.database.execute_fetchall(
            """SELECT users.nickname, user_settings.value FROM
            user_settings INNER JOIN users ON
            user_settings.user_id=users.user_id WHERE
            users.server_id=? AND user_settings.setting=?""",
            [server_id, setting])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find(self, user_id, pattern, default=[]):
        values = self.database.execute(
            """SELECT setting, value FROM user_settings WHERE
            user_id=? AND setting LIKE '?'""", [user_id, pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_prefix(self, user_id, prefix, default=[]):
        return self.find_user_settings(user_id, "%s%" % prefix, default)
    def delete(self, user_id, setting):
        self.database.execute(
            """DELETE FROM user_settings WHERE
            user_id=? AND setting=?""", [user_id, setting.lower()])

class UserChannelSettings(Table):
    def set(self, user_id, channel_id, setting, value):
        self.database.execute(
            """INSERT OR REPLACE INTO user_channel_settings VALUES
            (?, ?, ?, ?)""",
            [user_id, channel_id, setting.lower(), json.dumps(value)])
    def get(self, user_id, channel_id, setting, default=None):
        value = self.database.execute_fetchone(
            """SELECT value FROM user_channel_settings WHERE
            user_id=? AND channel_id=? AND setting=?""",
            [user_id, channel_id, setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def find(self, user_id, channel_id, pattern, default=[]):
        values = self.database.execute_fetchall(
            """SELECT setting, value FROM user_channel_settings WHERE
            user_id=? AND channel_id=? AND setting LIKE '?'""",
            [user_id, channel_id, pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_prefix(self, user_id, channel_id, prefix, default=[]):
        return self.find_user_settings(user_id, channel_id, "%s%" % prefix,
            default)
    def find_by_setting(self, user_id, setting, default=[]):
        values = self.database.execute_fetchall(
            """SELECT channels.name, user_channel_settings.value FROM
            user_channel_settings INNER JOIN channels ON
            user_channel_settings.channel_id=channels.channel_id
            WHERE user_channel_settings.setting=?
            AND user_channel_settings.user_id=?""", [setting, user_id])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_all_by_setting(self, server_id, setting, default=[]):
        values = self.database.execute_fetchall(
            """SELECT channels.name, users.nickname,
            user_channel_settings.value FROM
            user_channel_settings INNER JOIN channels ON
            user_channel_settings.channel_id=channels.channel_id
            INNER JOIN users on user_channel_settings.user_id=users.user_id
            WHERE user_channel_settings.setting=? AND
            users.server_id=?""", [setting, server_id])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], value[1], json.loads(value[2])
            return values
        return default
    def delete(self, user_id, channel_id, setting):
        self.database.execute(
            """DELETE FROM user_channel_settings WHERE
            user_id=? AND channel_id=? AND setting=?""",
            [user_id, channel_id, setting.lower()])

class Database(object):
    def __init__(self, bot, location="bot.db"):
        self.bot = bot
        self.location = location
        self.full_location = os.path.join(bot.bot_directory,
            self.location)
        self.database = sqlite3.connect(self.full_location,
            check_same_thread=False, isolation_level=None)
        self.database.execute("PRAGMA foreign_keys = ON")
        self._cursor = None

        self.make_servers_table()
        self.make_channels_table()
        self.make_users_table()
        self.make_bot_settings_table()
        self.make_server_settings_table()
        self.make_channel_settings_table()
        self.make_user_settings_table()
        self.make_user_channel_settings_table()

        self.servers = Servers(self)
        self.channels = Channels(self)
        self.users = Users(self)
        self.bot_settings = BotSettings(self)
        self.server_settings = ServerSettings(self)
        self.channel_settings = ChannelSettings(self)
        self.user_settings = UserSettings(self)
        self.user_channel_settings = UserChannelSettings(self)

    def cursor(self):
        if self._cursor == None:
            self._cursor = self.database.cursor()
        return self._cursor

    def _execute_fetch(self, query, fetch_func, params=[]):
        printable_query = " ".join(query.split())
        self.bot.log.debug("executing query: \"%s\" (params: %s)",
            [printable_query, params])
        start = time.monotonic()

        cursor = self.cursor()
        cursor.execute(query, params)
        value = fetch_func(cursor)

        end = time.monotonic()
        total_milliseconds = (end - start) * 1000
        self.bot.log.debug("executed in %fms", [total_milliseconds])

        return value
    def execute_fetchall(self, query, params=[]):
        return self._execute_fetch(query,
            lambda cursor: cursor.fetchall(), params)
    def execute_fetchone(self, query, params=[]):
        return self._execute_fetch(query,
            lambda cursor: cursor.fetchone(), params)
    def execute(self, query, params=[]):
        return self._execute_fetch(query, lambda cursor: None, params)

    def has_table(self, table_name):
        result = self.execute_fetchone("""SELECT COUNT(*) FROM
            sqlite_master WHERE type='table' AND name=?""",
            [table_name])
        return result[0] == 1

    def make_servers_table(self):
        if not self.has_table("servers"):
            self.execute("""CREATE TABLE servers
                (server_id INTEGER PRIMARY KEY, alias TEXT, hostname TEXT,
                port INTEGER,password TEXT,ipv4 BOOLEAN, tls BOOLEAN,
                nickname TEXT, username TEXT, realname TEXT)""")
    def make_channels_table(self):
        if not self.has_table("channels"):
            self.execute("""CREATE TABLE channels
                (channel_id INTEGER PRIMARY KEY, server_id INTEGER,
                name TEXT, FOREIGN KEY (server_id) REFERENCES
                servers (server_id) ON DELETE CASCADE,
                UNIQUE (server_id, name))""")
            self.execute("""CREATE INDEX channels_index
                on channels (server_id, name)""")
    def make_users_table(self):
        if not self.has_table("users"):
            self.execute("""CREATE TABLE users
                (user_id INTEGER PRIMARY KEY, server_id INTEGER,
                nickname TEXT, FOREIGN KEY (server_id) REFERENCES
                servers (server_id) ON DELETE CASCADE,
                UNIQUE (server_id, nickname))""")
            self.execute("""CREATE INDEX users_index
                on users (server_id, nickname)""")
    def make_bot_settings_table(self):
        if not self.has_table("bot_settings"):
            self.execute("""CREATE TABLE bot_settings
                (setting TEXT PRIMARY KEY, value TEXT)""")
            self.execute("""CREATE INDEX bot_settings_index
                ON bot_settings (setting)""")
    def make_server_settings_table(self):
        if not self.has_table("server_settings"):
            self.execute("""CREATE TABLE server_settings
                (server_id INTEGER, setting TEXT, value TEXT,
                FOREIGN KEY(server_id) REFERENCES
                servers(server_id) ON DELETE CASCADE,
                PRIMARY KEY (server_id, setting))""")
            self.execute("""CREATE INDEX server_settings_index
                ON server_settings (server_id, setting)""")
    def make_channel_settings_table(self):
        if not self.has_table("channel_settings"):
            self.execute("""CREATE TABLE channel_settings
                (channel_id INTEGER, setting TEXT, value TEXT,
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
                ON DELETE CASCADE, PRIMARY KEY (channel_id, setting))""")
            self.execute("""CREATE INDEX channel_settings_index
                ON channel_settings (channel_id, setting)""")
    def make_user_settings_table(self):
        if not self.has_table("user_settings"):
            self.execute("""CREATE TABLE user_settings
                (user_id INTEGER, setting TEXT, value TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
                ON DELETE CASCADE, PRIMARY KEY (user_id, setting))""")
            self.execute("""CREATE INDEX user_settings_index ON
                user_settings (user_id, setting)""")
    def make_user_channel_settings_table(self):
        if not self.has_table("user_channel_settings"):
            self.execute("""CREATE TABLE user_channel_settings
                (user_id INTEGER, channel_id INTEGER, setting TEXT,
                value TEXT, FOREIGN KEY (user_id) REFERENCES
                users(user_id) ON DELETE CASCADE, FOREIGN KEY
                (channel_id) REFERENCES channels(channel_id) ON
                DELETE CASCADE, PRIMARY KEY (user_id, channel_id,
                setting))""")
            self.execute("""CREATE INDEX user_channel_settings_index
                ON user_channel_settings (user_id, channel_id, setting)""")
