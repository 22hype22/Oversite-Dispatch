import os
import re
import time
import struct
import asyncio
import difflib
import logging
import tempfile

import aiohttp
import discord
import imageio_ffmpeg

logging.getLogger("discord.ext.voice_recv.reader").setLevel(logging.WARNING)
logging.getLogger("discord.ext.voice_recv.gateway").setLevel(logging.WARNING)

try:
    from discord.ext import voice_recv
    VOICE_RECV_AVAILABLE = True
except Exception as exc:
    voice_recv = None
    VOICE_RECV_AVAILABLE = False
    print(f"voice receive extension not available: {exc}", flush=True)

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
SPEED = float(os.environ.get("DISPATCH_SPEED", "1.25"))
VOICE_COMMANDS = os.environ.get("VOICE_COMMANDS", "1").lower() not in ("0", "false", "no", "off")
STT_MODEL = os.environ.get("ELEVENLABS_STT_MODEL", "scribe_v1")

VOICE_CMD_ENABLED = VOICE_COMMANDS and VOICE_RECV_AVAILABLE

ERLC_V2_BASE = "https://api.erlc.gg/v2"
XI_BASE = "https://api.elevenlabs.io/v1"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

play_queue = asyncio.Queue()
seen_keys = set()
boot_time = time.time()
voice_client = None
http = None
last_call = None


DISPATCH_WORDS = [
    "suspicious", "suspect", "suspects", "robbery", "burglary", "theft", "larceny",
    "assault", "battery", "homicide", "murder", "manslaughter", "kidnapping", "abduction",
    "hostage", "arson", "vandalism", "trespassing", "shoplifting", "carjacking", "hijacking",
    "shooting", "shots", "stabbing", "fight", "altercation", "disturbance", "domestic",
    "overdose", "suicide", "accident", "collision", "crash", "pursuit", "chase", "fleeing",
    "speeding", "reckless", "intoxicated", "drunk", "impaired", "prowler", "loitering",
    "breaking", "entering", "armed", "unarmed", "weapon", "weapons", "firearm", "firearms",
    "handgun", "pistol", "revolver", "rifle", "shotgun", "knife", "machete", "explosive",
    "bomb", "threat", "threatening", "wanted", "fugitive", "warrant", "felony", "misdemeanor",
    "narcotics", "drugs", "attempted", "progress", "pedestrian", "vehicle", "vehicles",
    "motorcycle", "truck", "sedan", "victim", "victims", "witness", "injured", "unconscious",
    "bleeding", "wounded", "fatality", "deceased", "backup", "ambulance", "paramedic",
    "medical", "emergency", "priority", "officer", "deputy", "sheriff", "trooper", "hostile",
    "aggressive", "violent", "brandishing", "concealed", "vandalizing", "burglar", "intruder",
    "gunshots", "gunfire", "gunman", "abandoned", "highway", "intersection", "residence",
    "apartment", "business", "parking", "northbound", "southbound", "eastbound", "westbound",
    "detain", "arrest", "transport", "surveillance", "harassment", "menacing", "kidnapped",
    "carjacked", "robbed", "assaulted", "stabbed", "shot", "wounded", "gun",
    "situation", "possible", "building", "individual", "subject", "description",
    "location", "direction", "male", "female", "hoodie", "running",
]
DISPATCH_SET = set(DISPATCH_WORDS)
PROTECTED_WORDS = {
    "the", "and", "for", "with", "was", "are", "his", "her", "him", "she", "they", "them",
    "there", "here", "near", "front", "back", "side", "guy", "man", "men", "woman", "women",
    "kid", "boy", "girl", "person", "people", "someone", "somebody", "outside", "inside",
    "street", "road", "house", "store", "bank", "corner", "away", "into", "just", "that",
    "this", "then", "some", "have", "will", "keep", "come", "went", "said", "says", "yelling",
    "screaming", "running", "walking", "driving", "trying", "started", "help", "please",
    "wearing", "swerving", "riding", "hearing", "hiding", "mask", "masked", "yelling",
}


def match_case(original, corrected):
    if original.isupper():
        return corrected.upper()
    if original[:1].isupper():
        return corrected.capitalize()
    return corrected


def correct_word(word):
    lower = word.lower()
    if len(lower) < 4 or lower in PROTECTED_WORDS or lower in DISPATCH_SET:
        return word
    matches = difflib.get_close_matches(lower, DISPATCH_WORDS, n=1, cutoff=0.78)
    if matches and matches[0] != lower:
        return match_case(word, matches[0])
    return word


def autocorrect(text):
    return re.sub(r"[A-Za-z]+", lambda m: correct_word(m.group(0)), text)


OPENERS = [
    "Attention all units",
    "All units, all units",
    "Dispatch to all units",
    "County wide, all units stand by for emergency traffic",
]

CLOSERS = [
    "Any available unit, mark en route and advise",
    "Any available unit to respond, please advise",
    "Units in the area, respond and advise your status",
]


def pick(options, number):
    try:
        return options[int(number) % len(options)]
    except (TypeError, ValueError):
        return options[0]


def build_call_line(call):
    desc = autocorrect((call.get("Description") or "").strip())
    loc = (call.get("PositionDescriptor") or "").strip()
    team = (call.get("Team") or "").strip()
    number = call.get("CallNumber")

    parts = [f"{pick(OPENERS, number)}.", "Priority call."]

    if desc and loc:
        parts.append(f"Caller reports, {desc}, at {loc}.")
    elif desc:
        parts.append(f"Caller reports, {desc}.")
    elif loc:
        parts.append(f"Reported incident at {loc}.")
    else:
        parts.append("Details to follow.")

    if team:
        parts.append(f"{team} units, respond Code 3.")
    else:
        parts.append("Respond Code 3.")

    parts.append("Be advised, use caution.")

    closer = pick(CLOSERS, number)
    if number:
        parts.append(f"{closer}. This is call number {number}.")
    else:
        parts.append(f"{closer}.")

    return " ".join(parts)


async def erlc_get(path):
    try:
        async with http.get(f"{ERLC_V2_BASE}{path}", headers={"Server-Key": ERLC_KEY}) as resp:
            if resp.status == 429:
                retry = float(resp.headers.get("Retry-After", "5"))
                print(f"erlc {path} -> 429 rate limited, waiting {retry}s", flush=True)
                await asyncio.sleep(min(retry, 30))
                return None
            if resp.status != 200:
                body = await resp.text()
                print(f"erlc {path} -> {resp.status}: {body[:200]}", flush=True)
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
        "voice_settings": {"stability": 0.65, "similarity_boost": 0.85, "style": 0.0, "use_speaker_boost": True},
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


async def announce(text, title="911 Call"):
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


_CRC_TABLE = []
for _n in range(256):
    _c = _n << 24
    for _ in range(8):
        _c = ((_c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if _c & 0x80000000 else (_c << 1) & 0xFFFFFFFF
    _CRC_TABLE.append(_c)


def _ogg_crc(data):
    crc = 0
    for byte in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CRC_TABLE[((crc >> 24) ^ byte) & 0xFF]
    return crc


def _ogg_page(header_type, granule, serial, seqno, packet):
    segtable = bytearray()
    n = len(packet)
    while n >= 255:
        segtable.append(255)
        n -= 255
    segtable.append(n)
    header = bytearray(b"OggS")
    header.append(0)
    header.append(header_type)
    header += struct.pack("<q", granule)
    header += struct.pack("<I", serial)
    header += struct.pack("<I", seqno)
    header += b"\x00\x00\x00\x00"
    header.append(len(segtable))
    header += segtable
    page = bytes(header) + packet
    crc = _ogg_crc(page)
    return page[:22] + struct.pack("<I", crc) + page[26:]


def opus_frames_to_ogg(frames, serial=1):
    out = bytearray()
    channels = 2 if (frames and (frames[0][0] & 0x04)) else 1
    head = b"OpusHead" + struct.pack("<BBHIHB", 1, channels, 0, 48000, 0, 0)
    out += _ogg_page(0x02, 0, serial, 0, head)
    vendor = b"oversite"
    tags = b"OpusTags" + struct.pack("<I", len(vendor)) + vendor + struct.pack("<I", 0)
    out += _ogg_page(0x00, 0, serial, 1, tags)
    granule = 0
    for i, frame in enumerate(frames):
        granule += 960
        header_type = 0x04 if i == len(frames) - 1 else 0x00
        out += _ogg_page(header_type, granule, serial, i + 2, frame)
    return bytes(out)


async def transcribe(ogg_bytes):
    form = aiohttp.FormData()
    form.add_field("model_id", STT_MODEL)
    form.add_field("file", ogg_bytes, filename="audio.ogg", content_type="audio/ogg")
    try:
        async with http.post(f"{XI_BASE}/speech-to-text", headers={"xi-api-key": XI_KEY}, data=form) as resp:
            if resp.status != 200:
                body = await resp.text()
                print(f"stt error {resp.status}: {body[:200]}", flush=True)
                return None
            data = await resp.json()
            return (data.get("text") or "").strip()
    except Exception as exc:
        print(f"stt request failed: {exc}", flush=True)
        return None


def wants_repeat(text):
    low = text.lower()
    if "say again" in low or "come again" in low:
        return True
    if "repeat" in low and ("call" in low or "last" in low or "that" in low or "again" in low):
        return True
    return False


async def handle_utterance(member, frames):
    if len(frames) < 25:
        return
    toc = frames[0][0] if frames[0] else 0
    print(f"utterance: {len(frames)} frames, first={len(frames[0])}b, toc=0x{toc:02x}, "
          f"channels={'stereo' if toc & 0x04 else 'mono'}", flush=True)
    text = await transcribe(opus_frames_to_ogg(frames))
    if not text:
        return
    who = getattr(member, "display_name", "unit")
    print(f"heard {who}: {text}", flush=True)
    if wants_repeat(text):
        if last_call is not None:
            await announce(build_call_line(last_call), title="Repeat")
        else:
            await announce("Dispatch. No active calls to repeat at this time.", title="Repeat")


if VOICE_RECV_AVAILABLE:

    class ListenSink(voice_recv.AudioSink):
        def __init__(self, loop):
            super().__init__()
            self.loop = loop
            self.buffers = {}

        def wants_opus(self):
            return True

        def write(self, user, data):
            if user is None:
                return
            packet = getattr(data, "opus", None)
            if packet:
                self.buffers.setdefault(user.id, []).append(packet)

        @voice_recv.AudioSink.listener()
        def on_voice_member_speaking_stop(self, member):
            frames = self.buffers.pop(member.id, None)
            if frames:
                asyncio.run_coroutine_threadsafe(handle_utterance(member, frames), self.loop)

        def cleanup(self):
            self.buffers.clear()


def start_listening():
    if not VOICE_CMD_ENABLED or voice_client is None:
        return
    try:
        if isinstance(voice_client, voice_recv.VoiceRecvClient) and not voice_client.is_listening():
            voice_client.listen(ListenSink(client.loop))
            print("voice commands active — say 'repeat the last call' in the VC", flush=True)
    except Exception as exc:
        print(f"could not start listening: {exc}", flush=True)


async def wait_for_voice(timeout=20):
    waited = 0
    while waited < timeout:
        if await ensure_voice() and voice_client is not None and voice_client.is_connected():
            return True
        await asyncio.sleep(1)
        waited += 1
    return False


async def playback_worker():
    while True:
        path = await play_queue.get()
        try:
            connected = await wait_for_voice()
            if connected and voice_client is not None:
                if voice_client.is_playing():
                    stopper = getattr(voice_client, "stop_playing", voice_client.stop)
                    stopper()
                done = asyncio.Event()

                def after(_err):
                    client.loop.call_soon_threadsafe(done.set)

                options = f'-filter:a "atempo={SPEED}"' if SPEED and SPEED != 1.0 else None
                source = discord.FFmpegOpusAudio(path, executable=FFMPEG_EXE, options=options)
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


async def poll_calls():
    global last_call
    data = await erlc_get("/server?EmergencyCalls=true")
    if not isinstance(data, dict):
        return
    calls = data.get("EmergencyCalls")
    if not isinstance(calls, list):
        return
    for call in calls:
        number = call.get("CallNumber")
        started = call.get("StartedAt", 0)
        key = ("call", number)
        if started < boot_time or key in seen_keys:
            continue
        seen_keys.add(key)
        last_call = call
        await announce(build_call_line(call))


async def dispatch_loop():
    await client.wait_until_ready()
    print(f"dispatch loop started, polling emergency calls every {POLL_SECONDS}s", flush=True)
    while not client.is_closed():
        await poll_calls()
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
    if existing is not None:
        voice_client = existing
        if existing.is_connected():
            if existing.channel and existing.channel.id != VOICE_CHANNEL_ID:
                try:
                    await existing.move_to(channel)
                except Exception:
                    pass
            start_listening()
            return True
        return False
    try:
        if VOICE_CMD_ENABLED:
            voice_client = await channel.connect(self_deaf=False, reconnect=True, cls=voice_recv.VoiceRecvClient)
        else:
            voice_client = await channel.connect(self_deaf=True, reconnect=True)
        print(f"dispatch connected to voice channel {channel.name}", flush=True)
        start_listening()
        return True
    except Exception as exc:
        print(f"voice connect failed: {exc}", flush=True)
        voice_client = None
        return False


async def voice_guard():
    await client.wait_until_ready()
    stuck_since = None
    while not client.is_closed():
        guild = client.get_guild(GUILD_ID)
        vc = guild.voice_client if guild is not None else None
        if vc is not None and vc.is_connected():
            stuck_since = None
            start_listening()
        elif vc is None:
            await ensure_voice()
            stuck_since = None
        else:
            if stuck_since is None:
                stuck_since = time.time()
            elif time.time() - stuck_since > 60:
                print("voice stuck for 60s, forcing a fresh reconnect", flush=True)
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    pass
                await ensure_voice()
                stuck_since = None
        await asyncio.sleep(15)


@client.event
async def on_ready():
    global http
    if http is None:
        http = aiohttp.ClientSession()
    print(f"dispatch online as {client.user}", flush=True)
    if VOICE_CMD_ENABLED:
        print("voice commands: ENABLED", flush=True)
    else:
        reason = "disabled by config" if not VOICE_COMMANDS else "voice-recv extension missing"
        print(f"voice commands: OFF ({reason}) — 911 dispatch still runs normally", flush=True)
    await ensure_voice()
    client.loop.create_task(playback_worker())
    client.loop.create_task(dispatch_loop())
    client.loop.create_task(voice_guard())


client.run(TOKEN)
