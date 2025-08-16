# weather_bot.py (SMOKE TEST)
import os, sys, asyncio
import discord
from discord.ext import commands

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
    print(f"=== UOC WEATHER DEBUG v1 === Logged in as {bot.user} (ID {bot.user.id})")
    try:
        ch = bot.get_channel(CHANNEL_ID)
        if ch is None:
            ch = await bot.fetch_channel(CHANNEL_ID)
        print(f"[DBG] Resolved channel: {ch} (type: {ch.__class__.__name__})")
        await ch.send("🔔 Smoke test: if you can read this, the bot can post here.")
        print("[OK] Smoke test message sent.")
    except discord.Forbidden:
        print("[ERR] Forbidden: missing View/Send in this channel.")
    except Exception as e:
        print(f"[ERR] Send failed: {e}")

    # keep the process alive so Render doesn't exit
    while True:
        await asyncio.sleep(3600)

bot.run(TOKEN)
