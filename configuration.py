import json

class Configuration:
    def __init__(self, configurationLocation=""):
        self.admin = {}
        self.steamcmd_path = ""
        self.server_path = ""
        self.token = ""
        self.mainGuild = 0
        self.mainChannel = 0

        if len(configurationLocation):
            f = open(configurationLocation)
            try:
                data = json.load(f)
                self.admin = data["admins"]
                self.steamcmd_path = data["steamcmd_path"]
                self.server_path = data["server_path"]
                self.token = data["token"]
                self.mainGuild = data["guild"]
                self.mainChannel = data["channel"]
            finally:
                f.close()


