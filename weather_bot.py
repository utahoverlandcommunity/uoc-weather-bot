# weather_bot.py — PERMISSION PROBE
import os, sys, asyncio
import discord
from discord.ext import commands

MARKER = "=== UOC WEATHER PERM PROBE v1 ==="
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("WEATHER_CHANNEL_ID", "0"))

if not TOKEN or len((TOKEN or "").split(".")) != 3:
    sys.exit("FATAL: DISCORD_TOKEN missing/malformed.")
if not CHANNEL_ID:
    sys.exit("FATAL: WEATHER_CHANNEL_ID not set.")

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{MARKER} Logged in as {bot.user} (ID {bot.user.id})")
    print(f"{MARKER} WEATHER_CHANNEL_ID={CHANNEL_ID}")

    # Resolve the channel
    ch = bot.get_channel(CHANNEL_ID)
    if ch is None:
        try:
            ch = await bot.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"{MARKER} ERR: fetch_channel failed for {CHANNEL_ID}: {e}")
            return
    print(f"{MARKER} Resolved channel: {ch} (type: {ch.__class__.__name__})")

    # If this is a Forum channel, plain send() won’t work
    if ch.__class__.__name__ == "ForumChannel":
        print(f"{MARKER} ERR: Channel is a ForumChannel. Use a normal text channel or forum-post code.")
        return

    # Compute the bot's permissions in this channel
    try:
        guild = ch.guild
        me = guild.get_member(bot.user.id) or await guild.fetch_member(bot.user.id)
        perms = ch.permissions_for(me)
        print(f"{MARKER} Perms — view:{perms.view_channel} send:{perms.send_messages} "
              f"embed:{perms.embed_links} history:{perms.read_message_history} manage:{perms.manage_messages}")
    except Exception as e:
        print(f"{MARKER} ERR: could not compute permissions: {e}")

    # Try to send a test message
    try:
        await ch.send("🔧 Perm probe: if you can read this, the bot can post here.")
        print(f"{MARKER} OK: test message sent.")
    except discord.Forbidden:
        print(f"{MARKER} ERR: Forbidden — bot lacks send/view permission in this channel.")
    except discord.HTTPException as e:
        print(f"{MARKER} ERR: HTTPException while sending: {e}")
    except Exception as e:
        print(f"{MARKER} ERR: Unexpected send error: {e}")

    # Keep process alive so logs stay open
    while True:
        await asyncio.sleep(3600)

bot.run(TOKEN)
