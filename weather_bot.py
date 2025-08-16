# weather_bot.py — UOC Weather Bot (grouped, readable format)
import os
import sys
import asyncio
import datetime as dt
from typing import Dict, Tuple, List, OrderedDict
import aiohttp
import discord
from discord.ext import tasks, commands
from collections import OrderedDict as OD

# ===== ENV =====
TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_CHANNEL_ID = int(os.getenv("WEATHER_CHANNEL_ID", "0"))
UPDATE_INTERVAL_MIN = int(os.getenv("UPDATE_INTERVAL_MIN", "240"))  # 240 = 4 hours
NWS_USER_AGENT = os.getenv("NWS_USER_AGENT", "UOC-WeatherBot (contact: admin@example.com)")

if not TOKEN or len(TOKEN.split(".")) != 3:
    sys.exit("FATAL: DISCORD_TOKEN missing/malformed.")
if not WEATHER_CHANNEL_ID:
    sys.exit("FATAL: WEATHER_CHANNEL_ID not set.")

# ===== REGIONS (lat, lon) =====
REGIONS: Dict[str, Tuple[float, float]] = {
    # Wasatch Front & Canyons
    "Salt Lake City (Wasatch Front)": (40.7608, -111.8910),
    "Bountiful/Layton":               (40.8787, -111.9020),
    "Ogden":                          (41.2230, -111.9738),
    "Logan/Cache Valley":             (41.7355, -111.8344),
    "Park City":                      (40.6461, -111.4980),
    "Heber/Midway":                   (40.5070, -111.4127),
    "Alta/Snowbird (LCC)":            (40.5885, -111.6350),
    "Brighton/Solitude (BCC)":        (40.6075, -111.5916),
    "Powder Mountain":                (41.3789, -111.7818),
    "Snowbasin":                      (41.2137, -111.8573),

    # Utah County & Central Wasatch
    "Provo/Orem":                     (40.2338, -111.6585),
    "Spanish Fork/Nephi":             (39.7106, -111.8350),

    # West Desert / Tooele / Salt Flats
    "Tooele/Grantsville":             (40.6097, -112.4636),
    "Bonneville Salt Flats (Wendover)": (40.7377, -114.0353),

    # Uinta Mountains & NE Utah
    "Mirror Lake Hwy (Uintas)":       (40.6022, -110.8897),
    "Vernal/Uintah Basin":            (40.4556, -109.5287),
    "Roosevelt/Duchesne":             (40.2991, -110.0090),
    "Bear Lake (Garden City)":        (41.9460, -111.3966),

    # Castle Country / Central
    "Price/Helper":                   (39.5994, -110.8107),
    "Emery/Green River":              (38.9952, -110.1587),
    "Hanksville":                     (38.3736, -110.7137),

    # Moab & Canyon Country
    "Moab":                           (38.5733, -109.5498),
    "Arches National Park":           (38.7331, -109.5925),
    "Canyonlands (Island in the Sky)":(38.3897, -109.8866),
    "Monticello/Blanding":            (37.8714, -109.3426),
    "Bluff/Monument Valley (UT side)":(37.2890, -109.5510),

    # Capitol Reef / Boulder Mtn / Escalante
    "Torrey/Capitol Reef":            (38.3006, -111.4165),
    "Boulder Mountain (Aquarius)":    (38.9256, -111.5796),
    "Escalante":                      (37.7705, -111.6023),

    # Bryce / Panguitch / Cedar Mountain
    "Bryce Canyon":                   (37.5930, -112.1871),
    "Panguitch":                      (37.8225, -112.4358),
    "Duck Creek/Cedar Mtn":           (37.5419, -112.6702),

    # SW Utah / Zion / St. George
    "Cedar City":                     (37.6775, -113.0619),
    "Zion (Springdale)":              (37.2019, -112.9963),
    "Hurricane/La Verkin":            (37.1753, -113.2899),
    "St. George/Washington":          (37.0965, -113.5684),
    "Kanab":                          (37.0475, -112.5250),
    "Big Water/Lake Powell (UT)":     (37.0774, -111.6505),

    # San Rafael / Dirty Devil / Remote
    "Goblin Valley":                  (38.5722, -110.7130),
    "San Rafael Swell (Temple Mtn)":  (38.6656, -110.6621),
    "Caineville Factory Butte":       (38.3750, -110.8820),
}

# Group headers → ordered list of region names
GROUPS: "OrderedDict[str, List[str]]" = OD([
    ("Wasatch Front & Canyons", [
        "Salt Lake City (Wasatch Front)", "Bountiful/Layton", "Ogden", "Logan/Cache Valley",
        "Park City", "Heber/Midway", "Alta/Snowbird (LCC)", "Brighton/Solitude (BCC)",
        "Powder Mountain", "Snowbasin"
    ]),
    ("Utah County & Central Wasatch", [
        "Provo/Orem", "Spanish Fork/Nephi"
    ]),
    ("West Desert & Salt Flats", [
        "Tooele/Grantsville", "Bonneville Salt Flats (Wendover)"
    ]),
    ("Uintas & NE Utah", [
        "Mirror Lake Hwy (Uintas)", "Vernal/Uintah Basin", "Roosevelt/Duchesne", "Bear Lake (Garden City)"
    ]),
    ("Central Utah & Castle Country", [
        "Price/Helper", "Emery/Green River", "Hanksville"
    ]),
    ("Canyon Country & SE Utah", [
        "Moab", "Arches National Park", "Canyonlands (Island in the Sky)",
        "Monticello/Blanding", "Bluff/Monument Valley (UT side)"
    ]),
    ("Capitol Reef / Boulder / Escalante", [
        "Torrey/Capitol Reef", "Boulder Mountain (Aquarius)", "Escalante"
    ]),
    ("Bryce / Panguitch / Cedar Mtn", [
        "Bryce Canyon", "Panguitch", "Duck Creek/Cedar Mtn"
    ]),
    ("SW Utah & Zion", [
        "Cedar City", "Zion (Springdale)", "Hurricane/La Verkin", "St. George/Washington", "Kanab", "Big Water/Lake Powell (UT)"
    ]),
    ("San Rafael Swell & Remote", [
        "Goblin Valley", "San Rafael Swell (Temple Mtn)", "Caineville Factory Butte"
    ]),
])

# ===== DISCORD =====
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

def fmt_temp(t) -> str:
    try:
        return f"{round(float(t))}°F"
    except Exception:
        return "—"

def now_local() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().strftime("%b %d, %I:%M %p")

async def fetch_open_meteo(session: aiohttp.ClientSession, lat: float, lon: float):
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,apparent_temperature,precipitation_probability,"
                  "precipitation,weathercode,wind_speed_10m,wind_gusts_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
    }
    url = "https://api.open-meteo.com/v1/forecast"
    async with session.get(url, params=params, timeout=25) as r:
        r.raise_for_status()
        return await r.json()

async def fetch_ut_alerts(session: aiohttp.ClientSession) -> List[str]:
    url = "https://api.weather.gov/alerts/active?area=UT"
    headers = { "User-Agent": NWS_USER_AGENT, "Accept": "application/ld+json" }
    async with session.get(url, headers=headers, timeout=25) as r:
        if r.status != 200:
            return []
        data = await r.json()
    headlines = []
    for feat in data.get("features", []):
        props = feat.get("properties", {}) or {}
        headline = props.get("headline") or props.get("event")
        if headline:
            headlines.append(headline)
    seen = set(); uniq = []
    for h in headlines:
        if h not in seen:
            uniq.append(h); seen.add(h)
    return uniq[:12]

def format_line(name: str, j: dict) -> str:
    """Compact, readable per-location line with graceful omissions."""
    try:
        hourly = j.get("hourly", {})
        daily = j.get("daily", {})

        t     = hourly.get("temperature_2m", [None])[0]
        feels = hourly.get("apparent_temperature", [None])[0]
        wind  = hourly.get("wind_speed_10m", [None])[0]
        gust  = hourly.get("wind_gusts_10m", [None])[0]
        pop   = hourly.get("precipitation_probability", [None])[0]
        p1h   = hourly.get("precipitation", [None])[0]
        tmax  = daily.get("temperature_2m_max", [None])[0]
        tmin  = daily.get("temperature_2m_min", [None])[0]
        pday  = daily.get("precipitation_sum", [None])[0]

        bits = [f"• **{name}** —"]
        if t is not None and feels is not None:
            bits.append(f"🌡 {fmt_temp(t)} (feels {fmt_temp(feels)})")
        if wind is not None and gust is not None:
            bits.append(f"💨 {round(wind)} mph (G {round(gust)})")
        if pop is not None:
            bits.append(f"🌧 {int(pop)}%")
        if p1h is not None:
            bits.append(f"1h {float(p1h):.2f}\"")
        if tmax is not None and tmin is not None:
            # Keep Hi/Lo compact to reduce clutter
            bits.append(f"⬆️ {fmt_temp(tmax)} ⬇️ {fmt_temp(tmin)}")
        if pday is not None:
            bits.append(f"Day {float(pday):.2f}\"")

        return " | ".join(bits)
    except Exception:
        return f"• **{name}** — data unavailable"

async def build_bulletin_lines() -> List[str]:
    lines: List[str] = [f"📻 **UOC Weather Net — Utah** · {now_local()}"]

    async with aiohttp.ClientSession() as session:
        # Alerts
        alerts = await fetch_ut_alerts(session)
        if alerts:
            lines += ["", "🚨 **Active Watches/Warnings (NWS)**"]
            lines += [f"• {h}" for h in alerts]

        # Grouped regions
        lines += ["", "🗺️ **Regional Conditions**"]
        for header, names in GROUPS.items():
            lines.append(f"\n__{header}__")
            for name in names:
                lat, lon = REGIONS[name]
                try:
                    data = await fetch_open_meteo(session, lat, lon)
                    lines.append(format_line(name, data))
                    await asyncio.sleep(0.12)
                except Exception as e:
                    lines.append(f"• **{name}** — error: {e}")

    return lines

async def send_chunked(channel: discord.abc.Messageable, lines: List[str], hard_limit: int = 1900):
    """Split across multiple messages to stay under 2000 chars."""
    buf = ""
    for line in lines:
        add = line + "\n"
        if len(buf) + len(add) > hard_limit:
            if buf.strip():
                await channel.send(buf.rstrip())
            buf = add
        else:
            buf += add
    if buf.strip():
        await channel.send(buf.rstrip())

@tasks.loop(minutes=UPDATE_INTERVAL_MIN)
async def post_weather():
    ch = bot.get_channel(WEATHER_CHANNEL_ID)
    if not ch:
        try:
            ch = await bot.fetch_channel(WEATHER_CHANNEL_ID)
        except Exception as e:
            print(f"[ERR] Channel fetch failed for {WEATHER_CHANNEL_ID}: {e}")
            return
    try:
        lines = await build_bulletin_lines()
        await send_chunked(ch, lines)
        print("[OK] Posted weather bulletin.")
    except discord.Forbidden:
        print("[ERR] Forbidden: missing send/view permission in channel.")
    except discord.HTTPException as e:
        print(f"[ERR] HTTPException while sending: {e}")
    except Exception as e:
        print(f"[ERR] Unexpected while sending: {e}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID {bot.user.id})")
    # Post once immediately on startup
    try:
        ch = bot.get_channel(WEATHER_CHANNEL_ID) or await bot.fetch_channel(WEATHER_CHANNEL_ID)
        lines = await build_bulletin_lines()
        await send_chunked(ch, lines)
        print("[OK] Initial weather bulletin posted.")
    except Exception as e:
        print(f"[ERR] Startup post failed: {e}")
        return

    if not post_weather.is_running():
        await asyncio.sleep(5)
        post_weather.start()

bot.run(TOKEN)
