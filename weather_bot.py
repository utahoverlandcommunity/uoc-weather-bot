# weather_bot.py (SMOKE TEST v2)
import os, sys, asyncio
import discord
from discord.ext import commands

MARKER = "=== UOC WEATHER DEBUG v2 ==="
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("WEATHER_CHANNEL_ID", "0"))

if not TOKEN or len(TOKEN.split(".")) != 3:
    sys.exit("FATAL: DISCORD_TOKEN missing/malformed.")
if not CHANNEL_ID:
    sys.exit("FATAL: WEATHER_CHANNEL_ID not set.")

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{MARKER} Logged in as {bot.user} (ID {bot.user.id})")
    print(f"{MARKER} Env WEATHER_CHANNEL_ID = {CHANNEL_ID}")
    try:
        ch = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
        print(f"{MARKER} Resolved channel: {ch} (type: {ch.__class__.__name__})")
        await ch.send("🔔 Smoke test v2: if you can read this, the bot can post here.")
        print(f"{MARKER} Smoke test message sent to {CHANNEL_ID}.")
    except discord.Forbidden:
        print(f"{MARKER} ERR: Forbidden (no View/Send in that channel).")
    except Exception as e:
        print(f"{MARKER} ERR: Send failed: {e}")

    # keep process alive on Render
    while True:
        await asyncio.sleep(3600)

bot.run(TOKEN)
