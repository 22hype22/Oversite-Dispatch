import os
import re
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
FEEDS = [f.strip() for f in os.environ.get("DISPATCH_FEEDS", "emergencycalls,modcalls,killlogs").split(",") if f.strip()]

ERLC_BASE = "https://api.policeroleplay.community/v1"
ERLC_V2_BASE = "https://api.policeroleplay.community/v2"
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
    name = str(raw).split(":", 1)[0].strip()
    name = re.sub(r"\([^)]*\)", "", name).strip()
    return name or "an unknown player"


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


def build_erlc_call_line(call):
    desc = (call.get("Description") or "").strip()
    loc = (call.get("PositionDescriptor") or "").strip()
    team = (call.get("Team") or "").strip()
    number = call.get("CallNumber")
    line = "Attention all units. Emergency call"
    if number:
        line += f", number {number}"
    line += "."
    if loc:
        line += f" Location, {loc}."
    if desc:
        line += f" Caller states, {desc}."
    if team:
        line += f" {team} response requested."
    line += " Any available unit, please respond and advise."
    return line


async def erlc_get(path, base=ERLC_BASE):
    try:
        async with http.get(f"{base}{path}", headers={"Server-Key": ERLC_KEY}) as resp:
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
    print(f"synthesized {len(audio)} bytes of audio", flush=True)
    return path


async def announce(text, title="Dispatch"):
    print(f"announce: {text[:80]}", flush=True)
    if TEXT_CHANNEL_ID:
        channel = client.get_channel(TEXT_CHANNEL_ID)
        if channel is not None:
            try:
                embed = discord.Embed(title=f"📻 {title}", description=text, color=0x3B82F6)
                await channel.send(embed=embed)
            except Exception as exc:
                print(f"text log failed: {exc}", flush=True)
    path = await synthesize(text)
    if path:
        await play_queue.put(path)
        print("audio queued for playback", flush=True)


async def playback_worker():
    while True:
        path = await play_queue.get()
        try:
            connected = await ensure_voice()
            if connected and voice_client is not None:
                if voice_client.is_playing():
                    voice_client.stop()
                done = asyncio.Event()

                def after(_err):
                    client.loop.call_soon_threadsafe(done.set)

                source = discord.FFmpegOpusAudio(path, executable=FFMPEG_EXE)
                voice_client.play(source, after=after)
                print("playing audio in voice channel", flush=True)
                await done.wait()
                print("finished playing", flush=True)
            else:
                print("dropping audio — not connected to voice", flush=True)
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
        await announce(build_modcall_line(caller), title="Incoming Call")


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
        await announce(build_kill_line(killer, killed), title="Shots Fired")


async def poll_erlc_emergency():
    data = await erlc_get("/server?EmergencyCalls=true", base=ERLC_V2_BASE)
    if not isinstance(data, dict):
        return
    calls = data.get("EmergencyCalls")
    if not isinstance(calls, list):
        return
    for call in calls:
        number = call.get("CallNumber")
        started = call.get("StartedAt", 0)
        key = ("erlccall", number)
        if started < boot_time or key in seen_keys:
            continue
        seen_keys.add(key)
        await announce(build_erlc_call_line(call), title="911 Call")


async def dispatch_loop():
    await client.wait_until_ready()
    handlers = {
        "modcalls": poll_modcalls,
        "killlogs": poll_killlogs,
        "emergencycalls": poll_erlc_emergency,
    }
    while not client.is_closed():
        for feed in FEEDS:
            handler = handlers.get(feed)
            if handler is not None:
                await handler()
        await asyncio.sleep(POLL_SECONDS)


async def ensure_voice():
    global voice_client
    guild = client.get_guild(GUILD_ID)
    if guild is None:
        print("dispatch guild not found — check DISPATCH_GUILD_ID", flush=True)
        return False
    channel = guild.get_channel(VOICE_CHANNEL_ID)
    if channel is None:
        print("voice channel not found — check DISPATCH_VOICE_CHANNEL_ID", flush=True)
        return False
    existing = guild.voice_client
    if existing is not None and existing.is_connected():
        voice_client = existing
        if existing.channel and existing.channel.id != VOICE_CHANNEL_ID:
            await existing.move_to(channel)
        return True
    if existing is not None:
        try:
            await existing.disconnect(force=True)
        except Exception:
            pass
    try:
        voice_client = await channel.connect(self_deaf=True, reconnect=True)
        print(f"dispatch connected to voice channel {channel.name}", flush=True)
        return True
    except Exception as exc:
        print(f"voice connect failed: {exc}", flush=True)
        voice_client = None
        return False


async def voice_guard():
    await client.wait_until_ready()
    while not client.is_closed():
        await ensure_voice()
        await asyncio.sleep(30)


@client.event
async def on_ready():
    global http
    if http is None:
        http = aiohttp.ClientSession()
    print(f"dispatch online as {client.user}", flush=True)
    await ensure_voice()
    client.loop.create_task(playback_worker())
    client.loop.create_task(dispatch_loop())
    client.loop.create_task(voice_guard())


client.run(TOKEN)
