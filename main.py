import discord
from discord.ext import tasks
from queue import Queue
import asyncio

import tokenSecret
import responses as rsp
from server import ServerStatus, PalServer
import sys

# Discord Variables
intents = discord.Intents.default()
intents.message_content = True
intents.presences = False
intents.typing = False
client = discord.Client(intents=intents)

#Guild: Eugene
EUGENE_GUILD_ID = 123652157097508866 # Eugene
EUGENE_CHANNEL_POCKETPALS_ID = 939778829893910528 #packet-pals

# Managed Servers
SERVER_KILL_TIMER = 5 * 12 * 10 # 5s loop*12 = 1m * min target
palServer = PalServer()

# Send a message to the Eugene: pocket-pals channel
async def SendPocketPalMessage(message):
    palServer.msg_channel = client.get_channel(EUGENE_CHANNEL_POCKETPALS_ID)
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
        palServer.msg_channel = client.get_channel(EUGENE_CHANNEL_POCKETPALS_ID)
        await SendPocketPalMessage("Game SupOwOvisor Ready!")

    # Admin Control
    if palServer.admin_active:
        return

    # Check for monitored Channel
    if palServer.voip_id is None:
        await asyncio.sleep(1)
        return
    
    # Active Monitor Loop
    observedMembers = len(client.get_guild(EUGENE_GUILD_ID).get_channel(palServer.voip_id).members)
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
    print("Hooking Discord")
    await main.start()

# Reactions to messages
@client.event
async def on_message(message):
    # Early out if bot message
    if message.author == client.user:
        return

    # Early out if wrong Channel
    if message.channel.id != EUGENE_CHANNEL_POCKETPALS_ID:
        return

    if message.content.startswith('$help'):
        await message.channel.send("Available commands:\n- $palserver-start\n- $palserver-stop\n- $palserver-status")
        await message.channel.send("Admin commands:\n- $admin-start\n- $admin-stop\n- $admin-kill")
        return

    # Public: Start Server
    if message.content.startswith('$palserver-start'):
        if message.author.voice is None:
            await message.channel.send('No voice channel detected. Cannot start monitoring')
            return
        await message.channel.send('Starting server update check')
        if CallServerStart(False, message.author.voice.channel.id):
            await message.channel.send(rsp.GetResponseServerStart())
            await message.channel.send('Monitoring voice channel. Server will close when channel becomes inactive')
        else:
            await message.channel.send("Server Startup failed, Please check system logs")
        return

    # Public: Stop Server
    if message.content.startswith('$palserver-stop'):
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
        return
        
    # Public: Start Server
    if message.content.startswith('$palserver-status'):
        await message.channel.send(f"Server Status Check: {palServer.status.name}")
        return

    # Admin Start Server
    if message.content.startswith('$admin-start'):
        if not palServer.UserAuthorized(message.author.id):
            await message.channel.send(rsp.GetResponseUnauth())
            return
        await message.channel.send("Admin start detected. Manually kill server when done.")
        if CallServerStart(True, None):
            await message.channel.send(rsp.GetResponseServerStart())
        else:
            await message.channel.send("Server Startup failed, Please check system logs")
        return

    # Admin Stop Server
    if message.content.startswith('$admin-stop'):
        if not palServer.UserAuthorized(message.author.id):
            await message.channel.send(rsp.GetResponseUnauth())
            return
        await message.channel.send("Admin Stop declared")
        if CallServerStop(message.author.id):
            await message.channel.send(rsp.GetResponseServerStop())
        else:
            await message.channel.send("Server Shutdown failed, Please check system logs")
        return

    # Admin kill bot
    if message.content.startswith('$admin-kill'):
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
    # End Message Parse

client.run(tokenSecret.GetDiscordSecret())

