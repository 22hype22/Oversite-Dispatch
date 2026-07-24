import os
import time
import asyncio
import tempfile

import aiohttp
import discord
import imageio_ffmpeg

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

TOKEN = os.environ["DISCORD_TOKEN"]
ERLC_KEY = os.environ["ERLC_SERVER_KEY"]
XI_KEY = os.environ["ELEVENLABS_API_KEY"]
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")
XI_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_turbo_v2")
GUILD_ID = int(os.environ["DISPATCH_GUILD_ID"])
VOICE_CHANNEL_ID = int(os.environ["DISPATCH_VOICE_CHANNEL_ID"])
TEXT_CHANNEL_ID = int(os.environ.get("DISPATCH_TEXT_CHANNEL_ID", "0"))
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "15"))
FEEDS = [f.strip() for f in os.environ.get("DISPATCH_FEEDS", "modcalls,killlogs").split(",") if f.strip()]

ERLC_BASE = "https://api.policeroleplay.community/v1"
XI_BASE = "https://api.elevenlabs.io/v1"

TEN_CODES = {
    "assist": "10-13, unit requesting assistance",
    "shots": "10-71, shots fired",
    "acknowledge": "10-4",
    "backup": "10-78, requesting backup",
    "responding": "10-76, en route",
    "clear": "10-8, in service",
}

intents = discord.Intents.default()
client = discord.Client(intents=intents)

play_queue = asyncio.Queue()
seen_keys = set()
boot_time = time.time()
voice_client = None
http = None


def clean_name(raw):
    if not raw:
        return "an unknown player"
    return str(raw).split(":", 1)[0].strip() or "an unknown player"


def build_modcall_line(caller):
    name = clean_name(caller)
    return (
        f"Attention all units. Dispatch has received a call for assistance from {name}. "
        f"Be advised, {TEN_CODES['assist']}. Any available unit, please respond and advise. {TEN_CODES['acknowledge']}."
    )


def build_kill_line(killer, killed):
    who = clean_name(killed)
    return (
        f"Dispatch to all units. {TEN_CODES['shots']}, reported involving {who}. "
        f"Units in the area, respond code three and advise on scene."
    )


async def erlc_get(path):
    try:
        async with http.get(f"{ERLC_BASE}{path}", headers={"Server-Key": ERLC_KEY}) as resp:
            if resp.status == 429:
                retry = float(resp.headers.get("Retry-After", "5"))
                await asyncio.sleep(min(retry, 30))
                return None
            if resp.status != 200:
                return None
            return await resp.json()
    except Exception as exc:
        print(f"erlc fetch failed for {path}: {exc}", flush=True)
        return None


async def synthesize(text):
    url = f"{XI_BASE}/text-to-speech/{VOICE_ID}"
    payload = {
        "text": text,
        "model_id": XI_MODEL,
        "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.15},
    }
    headers = {"xi-api-key": XI_KEY, "Content-Type": "application/json"}
    try:
        async with http.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                print(f"elevenlabs error {resp.status}: {body[:200]}", flush=True)
                return None
            audio = await resp.read()
    except Exception as exc:
        print(f"elevenlabs request failed: {exc}", flush=True)
        return None
    fd, path = tempfile.mkstemp(suffix=".mp3")
    with os.fdopen(fd, "wb") as handle:
        handle.write(audio)
    return path


async def announce(text):
    if TEXT_CHANNEL_ID:
        channel = client.get_channel(TEXT_CHANNEL_ID)
        if channel is not None:
            try:
                await channel.send(f"📻 {text}")
            except Exception as exc:
                print(f"text log failed: {exc}", flush=True)
    path = await synthesize(text)
    if path:
        await play_queue.put(path)


async def playback_worker():
    while True:
        path = await play_queue.get()
        try:
            if voice_client is not None and voice_client.is_connected():
                done = asyncio.Event()

                def after(_err):
                    client.loop.call_soon_threadsafe(done.set)

                source = discord.FFmpegPCMAudio(path, executable=FFMPEG_EXE)
                voice_client.play(source, after=after)
                await done.wait()
        except Exception as exc:
            print(f"playback failed: {exc}", flush=True)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
            play_queue.task_done()


async def poll_modcalls():
    data = await erlc_get("/server/modcalls")
    if not isinstance(data, list):
        return
    for item in data:
        ts = item.get("Timestamp", 0)
        caller = item.get("Caller")
        key = ("modcall", caller, ts)
        if ts < boot_time or key in seen_keys:
            continue
        seen_keys.add(key)
        await announce(build_modcall_line(caller))


async def poll_killlogs():
    data = await erlc_get("/server/killlogs")
    if not isinstance(data, list):
        return
    for item in data:
        ts = item.get("Timestamp", 0)
        killer = item.get("Killer")
        killed = item.get("Killed")
        key = ("kill", killer, killed, ts)
        if ts < boot_time or key in seen_keys:
            continue
        seen_keys.add(key)
        await announce(build_kill_line(killer, killed))


async def dispatch_loop():
    await client.wait_until_ready()
    handlers = {"modcalls": poll_modcalls, "killlogs": poll_killlogs}
    while not client.is_closed():
        for feed in FEEDS:
            handler = handlers.get(feed)
            if handler is not None:
                await handler()
        await asyncio.sleep(POLL_SECONDS)


async def connect_voice():
    global voice_client
    guild = client.get_guild(GUILD_ID)
    if guild is None:
        print("dispatch guild not found — check DISPATCH_GUILD_ID", flush=True)
        return
    channel = guild.get_channel(VOICE_CHANNEL_ID)
    if channel is None:
        print("voice channel not found — check DISPATCH_VOICE_CHANNEL_ID", flush=True)
        return
    try:
        voice_client = await channel.connect(self_deaf=True)
        print(f"dispatch connected to voice channel {channel.name}", flush=True)
    except Exception as exc:
        print(f"voice connect failed: {exc}", flush=True)


@client.event
async def on_ready():
    global http
    if http is None:
        http = aiohttp.ClientSession()
    print(f"dispatch online as {client.user}", flush=True)
    await connect_voice()
    client.loop.create_task(playback_worker())
    client.loop.create_task(dispatch_loop())


client.run(TOKEN)
