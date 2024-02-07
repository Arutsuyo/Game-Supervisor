import discord
from discord.ext import tasks
from discord import app_commands
from queue import Queue
import asyncio
from configuration import Configuration
import responses as rsp
from server import ServerStatus, PalServer
import sys

# Initialize the configuration file
config = Configuration(r"configSecret.json")

# Discord Variables
intents = discord.Intents.default()
intents.message_content = True
intents.presences = False
intents.typing = False
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Managed Servers
SERVER_KILL_TIMER = 5 * 12 * 10 # 5s loop*12 = 1m * min target
palServer = PalServer()

# Send a message to the Eugene: pocket-pals channel
async def SendPocketPalMessage(message):
    palServer.msg_channel = client.get_channel(config.mainChannel)
    await palServer.msg_channel.send(message)


# Start the server
def CallServerStart(admin, voip):
    print("")
    if admin:
        print('Admin: ', end='')
    else:
        print('Starting Palworld Server')
    return palServer.StartServer(admin, voip)

# Stop the Server
def CallServerStop(userID):
    print("")
    if palServer.UserAuthorized(userID):
        print('Admin: ', end='')
    print('Attempting to stop server')
    return palServer.StopServer(userID)

#Main detection loop for server control
@tasks.loop(seconds=5)
async def main():
    # One Time Startup
    if palServer.msg_channel is None:
        print(f'We have logged in as {client.user}')
        print("Getting Channel Hook...")
        palServer.msg_channel = client.get_channel(config.mainChannel)
        await SendPocketPalMessage("Game SupOwOvisor Ready!")

    # Admin Control
    if palServer.admin_active:
        return

    # Check for monitored Channel
    if palServer.voip_id is None:
        await asyncio.sleep(1)
        return
    
    # Active Monitor Loop
    observedMembers = len(client.get_channel(palServer.voip_id).members)
    if palServer.status is ServerStatus.RUNNING:
        if observedMembers == 0:
            print("Empty VC... starting shutdown")
            await SendPocketPalMessage("No members detected, will close server after 10 minutes of inactivity")
            palServer.status = ServerStatus.DYING
            palServer.deathTimer = SERVER_KILL_TIMER
    elif palServer.status is ServerStatus.DYING:
        if observedMembers > 0:
            print("VOIP Detected, Aborting disconnect.")
            await SendPocketPalMessage("User detected, Aborting shutdown!")
            palServer.status = ServerStatus.RUNNING
        else:
            palServer.deathTimer -= 5
            print(f"Shutdown in {palServer.deathTimer}s")
            if palServer.deathTimer <= 0: # Minute Target * (12s * 5s loop = 1m)
                palServer.StopServer()
                await SendPocketPalMessage("PalServer Shutdown Complete")
    
    return


# Start the bot
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=config.mainGuild))
    print("Hooking Discord")
    await main.start()


@tree.command(
        name="palserver-start",
        description="Request to start the palworld server, requires user to be in a voice channel.",
        guild=discord.Object(id=config.mainGuild)
)
async def on_palServer_Start(message):
    # Early out if wrong Channel
    if message.channel.id != config.mainChannel:
        return

    if message.author.voice is None:
        await message.channel.send('No voice channel detected. Cannot start monitoring')
        return
    await message.channel.send('Starting server update check')
    if CallServerStart(False, message.author.voice.channel.id):
        await message.channel.send(rsp.GetResponseServerStart())
        await message.channel.send('Monitoring voice channel. Server will close when channel becomes inactive')
    else:
        await message.channel.send("Server Startup failed, Please check system logs")

@tree.command(
        name="palserver-stop",
        description="Request to stop the palworld server, requires appropriate guild permissions.",
        guild=discord.Object(id=config.mainGuild)
)
async def on_palServer_Stop(message):
    # Early out if wrong Channel
    if message.channel.id != config.mainChannel:
        return
    
    if palServer.status in ServerStatus.RUNNING:
        if palServer.UserAuthorized(message.author.id):
            await message.channel.send('Attempting to stop server...')
            if CallServerStop(message.author.id):
                await message.channel.send(rsp.GetResponseServerStop())
            else:
                await message.channel.send("Server Startup failed, Please check system logs")
        else:
            await message.channel.send(rsp.GetResponseUnauth())
            await message.channel.send('Please ask PalServer Admin to stop server or GTFO of VC')
            return
    elif palServer.status in ServerStatus.DYING:
        await message.channel.send(rsp.GetResponseYes())
        await message.channel.send('Server shut down triggered early.')
        palServer.deathTimer = 0
    else:
        await message.channel.send('Error 409: Palworld Server is not currently running')

@tree.command(
        name="palserver-status",
        description="Request the status of the server.",
        guild=discord.Object(id=config.mainGuild)
)
async def on_palServer_Status(message):
    # Early out if wrong Channel
    if message.channel.id != config.mainChannel:
        return
    
    await message.channel.send(f"Server Status Check: {palServer.status.name} - Detached mode: {palServer.admin_active}")

@tree.command(
        name="admin-start",
        description="Force the server to start without voice channel requirements.",
        guild=discord.Object(id=config.mainGuild)
)
async def on_admin_Start(message):
    # Early out if wrong Channel
    if message.channel.id != config.mainChannel:
        return

    if not palServer.UserAuthorized(message.author.id):
        await message.channel.send(rsp.GetResponseUnauth())
        return
    await message.channel.send("Admin start detected. Manually kill server when done.")
    if CallServerStart(True, None):
        await message.channel.send(rsp.GetResponseServerStart())
    else:
        await message.channel.send("Server Startup failed, Please check system logs")

@tree.command(
        name="admin-stop",
        description="Force the server to stop as soon as possible.",
        guild=discord.Object(id=config.mainGuild)
)
async def on_admin_Stop(message):
    # Early out if wrong Channel
    if message.channel.id != config.mainChannel:
        return

    if not palServer.UserAuthorized(message.author.id):
        await message.channel.send(rsp.GetResponseUnauth())
        return
    await message.channel.send("Admin Stop declared")
    if CallServerStop(message.author.id):
        await message.channel.send(rsp.GetResponseServerStop())
    else:
        await message.channel.send("Server Shutdown failed, Please check system logs")

@tree.command(
        name="admin-kill",
        description="Forces the bot to quit.",
        guild=discord.Object(id=config.mainGuild)
)
async def on_admin_Stop(message):
    # Early out if wrong Channel
    if message.channel.id != config.mainChannel:
        return
    
    if not palServer.SuperAuthorized(message.author.id):
        await message.channel.send(rsp.GetResponseUnauth())
        return
    await message.channel.send(rsp.GetResponseYes())
    if palServer.status in ServerStatus.ACTIVE:
        await message.channel.send("Killing Palworld Server. . .")
        if CallServerStop(message.author.id):
            await message.channel.send(rsp.GetResponseServerStop())
        else:
            await message.channel.send("Server Shutdown failed, Please check system logs")
    await message.channel.send(":vulcan:")
    sys.exit(0)

client.run(config.token)

