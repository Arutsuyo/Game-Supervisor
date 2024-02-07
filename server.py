from enum import Flag, auto
import subprocess
from configuration import Configuration
import psutil
import os

class ServerStatus(Flag):
    DEAD = auto()
    RUNNING = auto()
    DYING = auto()
    ACTIVE = RUNNING | DYING
    INACTIVE = DEAD

class PalServer:
    def __main__(self, configurations: Configuration):
        # Sets the admins from the admin list in the configuration file
        self.admins = configurations.admin

        # Sets the palworld start arguments using the server path from the configuration file
        self.args_palworld = [
            os.path.join(configurations.server_path, "PalServer.exe"), 
            "-players=32", 
            "-port=25565", 
            "-useperfthreads", 
            "-NoAsyncLoadingThread", 
            "-UseMultithreadForDS"
        ]

        # Sets the steamcmd arguments using the steamcmd path from the configuration file
        self.args_steamcmd = [
            os.path.join(configurations.steamcmd_path, "steamcmd.exe"), 
            "+login", 
            "anonymous", 
            "+app_update", 
            "2394010", 
            "+quit"
        ]
    
    # Local variables
    admin_active = False
    pid = None
    status = ServerStatus.DEAD
    voip_id = None
    msg_channel = None

    def StartServer(self, admin, voip):
        if self.status in ServerStatus.INACTIVE:
            print("PalServer: Start")
            subprocess.Popen(self.args_steamcmd, cwd=self.path_steamcmd).wait()
            self.pid = subprocess.Popen(self.args_palworld, close_fds=True, cwd=self.path_server)
            self.status = ServerStatus.RUNNING
            self.admin_active = admin
            self.voip_id = voip
            return True
        else:
            print(f"PalServer: Server Status {self.status.name}")
            return False

    def StopServer(self, userID=None):
        killed = False
        if self.status in ServerStatus.ACTIVE:
            if self.admin_active and not self.UserAuthorized(userID):
                return killed

            print("PalServer: Killing")
            for proc in psutil.process_iter():
                if "PalServer-Win64-Test-Cmd" in proc.name():
                    proc.kill()
                    killed = True
                    print("PalServer: Dead")
                    self.pid = None
                    self.status = ServerStatus.DEAD
                    self.admin_active = False
                    self.voip_id = None
                    break
        else:
            print(f"PalServer: Server Status {self.status.name}")
        return killed
    
    def UserAuthorized(self, userID):
        for a_name, a_id in self.admins.items():
            if userID == a_id:
                print(f"{a_name} Authorized")
                return True
        print(f"Unauthorized Userid: {userID}")
        return False
    
    def SuperAuthorized(self, userID):
        if userID == self.admins['Nara']:
            print("Nara Authorized")
            return True
        print(f"Unauthorized Userid: {userID}")
        return False
