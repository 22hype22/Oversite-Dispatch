import os
import io
import re
import wave
import time
import random
import asyncio
import difflib
import logging
import tempfile
from datetime import datetime, timezone

try:
    import audioop
except Exception:
    audioop = None

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

import aiohttp
import discord
import imageio_ffmpeg

logging.getLogger("discord.ext.voice_recv.reader").setLevel(logging.WARNING)
logging.getLogger("discord.ext.voice_recv.gateway").setLevel(logging.WARNING)
logging.getLogger("discord.ext.voice_recv.opus").setLevel(logging.ERROR)

try:
    from discord.ext import voice_recv
    from discord.ext.voice_recv.rtp import SilencePacket
    VOICE_RECV_AVAILABLE = True
except Exception as exc:
    voice_recv = None
    SilencePacket = ()
    VOICE_RECV_AVAILABLE = False
    print(f"voice receive extension not available: {exc}", flush=True)

try:
    import davey
    HAVE_DAVEY = True
except Exception:
    davey = None
    HAVE_DAVEY = False

_HERE = os.path.dirname(os.path.abspath(__file__))
OPUS_OK = False
for _cand in ("libopus.so.0", os.path.join(_HERE, "libopus.so.0"), "./libopus.so.0", "opus"):
    try:
        if not discord.opus.is_loaded():
            discord.opus.load_opus(_cand)
        if discord.opus.is_loaded():
            OPUS_OK = True
            print(f"loaded opus from {_cand}", flush=True)
            break
    except Exception:
        continue
if not OPUS_OK:
    print("opus not loaded — voice commands will stay off", flush=True)

BUILD = "nearest-unit-1"

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
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = os.environ.get("DISPATCH_AI_MODEL", "claude-haiku-4-5")
AI_ENABLED = bool(ANTHROPIC_KEY)
AI_CACHE_VARIANTS = int(os.environ.get("AI_CACHE_VARIANTS", "3"))
DISPATCH_REGION = os.environ.get("DISPATCH_REGION", "the United States").strip() or "the United States"
ALERT_TONES = os.environ.get("ALERT_TONES", "1").lower() not in ("0", "false", "no", "off")
DISPATCH_TZ = os.environ.get("DISPATCH_TZ", "UTC").strip() or "UTC"
MIN_UTTER_BYTES = int(os.environ.get("MIN_UTTERANCE_BYTES", "115200"))
SILENCE_RMS = int(os.environ.get("SILENCE_RMS", "350"))
TRAFFIC_STOP_RETURN = os.environ.get("TRAFFIC_STOP_RETURN", "1").lower() not in ("0", "false", "no", "off")
FLEE_SPEED = float(os.environ.get("FLEE_SPEED", "35"))
STOP_POLL_SECONDS = float(os.environ.get("STOP_POLL_SECONDS", "1"))
STOP_MAX_SECONDS = int(os.environ.get("STOP_MAX_SECONDS", "1800"))
CALLSIGN_NICK = os.environ.get("CALLSIGN_NICK", "0").lower() not in ("0", "false", "no", "off")
CALL_TEAMS = [t.strip().lower() for t in os.environ.get("CALL_TEAMS", "police,sheriff").split(",") if t.strip()]

VOICE_CMD_ENABLED = VOICE_COMMANDS and VOICE_RECV_AVAILABLE and OPUS_OK

ERLC_V2_BASE = "https://api.erlc.gg/v2"
XI_BASE = "https://api.elevenlabs.io/v1"
ANTHROPIC_BASE = "https://api.anthropic.com/v1"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
command_tree = discord.app_commands.CommandTree(client)
DISPATCH_GUILD = discord.Object(id=GUILD_ID)

play_queue = asyncio.Queue()
seen_keys = set()
boot_time = time.time()
commands_synced = False
voice_client = None
http = None
last_call = None
response_cache = {}
tone_path = None
status_board = {}
open_calls = {}
callsign_links = {}
active_stops = {}
nick_original = {}
_players_debugged = False
_call_debugged = False
IGNORE = object()


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


def _tz():
    if ZoneInfo is not None and DISPATCH_TZ.upper() != "UTC":
        try:
            return ZoneInfo(DISPATCH_TZ)
        except Exception:
            return None
    return None


def local_time_str():
    return datetime.now(_tz() or timezone.utc).strftime("%H:%M")


def stamp_time(epoch):
    if not epoch:
        return ""
    try:
        return datetime.fromtimestamp(float(epoch), _tz() or timezone.utc).strftime("%H:%M")
    except Exception:
        return ""


PRIORITY_WORDS = (
    "shot", "shots", "shooting", "gun", "firearm", "weapon", "armed", "stab",
    "robbery", "burglary", "hostage", "kidnap", "assault", "pursuit", "fight",
    "domestic", "fire", "explosion", "bomb", "overdose", "unconscious", "bleeding",
    "officer down", "10-99", "wounded", "homicide", "carjack",
)


def is_priority(call):
    blob = f"{call.get('Description') or ''} {call.get('Team') or ''}".lower()
    return any(w in blob for w in PRIORITY_WORDS)


def is_police_call(call):
    team = str(call.get("Team") or "").strip().lower()
    if not team:
        return True
    return any(t in team for t in CALL_TEAMS)


def build_call_line(call, nearest=""):
    desc = autocorrect((call.get("Description") or "").strip())
    loc = (call.get("PositionDescriptor") or "").strip()
    team = (call.get("Team") or "").strip()
    number = call.get("CallNumber")

    parts = ["Attention units."]

    if desc and loc:
        parts.append(f"{desc}, at {loc}.")
    elif desc:
        parts.append(f"{desc}.")
    elif loc:
        parts.append(f"Report of an incident at {loc}.")
    else:
        parts.append("Report of an incident, details to follow.")

    if nearest:
        parts.append(f"Unit {nearest}, you are the closest unit, respond Code 3.")
    elif team:
        parts.append(f"{team} units respond Code 3.")
    else:
        parts.append("Units respond Code 3.")

    if number:
        parts.append(f"Incident number {number}.")

    parts.append(f"Time, {local_time_str()}.")

    return " ".join(parts)


def make_tone():
    try:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        args = [
            FFMPEG_EXE, "-y", "-f", "lavfi", "-i",
            "sine=frequency=947:sample_rate=48000:duration=0.4",
            "-f", "lavfi", "-i",
            "sine=frequency=1270:sample_rate=48000:duration=0.4",
            "-filter_complex",
            "[0:a][1:a]concat=n=2:v=0:a=1,volume=0.35,afade=t=out:st=0.75:d=0.05[a]",
            "-map", "[a]", "-ac", "2", "-ar", "48000", path,
        ]
        import subprocess
        result = subprocess.run(args, capture_output=True)
        if result.returncode == 0 and os.path.getsize(path) > 0:
            return path
        print(f"tone generation failed: {result.stderr[:200]!r}", flush=True)
    except Exception as exc:
        print(f"tone generation error: {exc}", flush=True)
    return None


async def erlc_get(path):
    try:
        async with http.get(f"{ERLC_V2_BASE}{path}", headers={"Server-Key": ERLC_KEY}) as resp:
            if resp.status == 429:
                retry = float(resp.headers.get("Retry-After", "3"))
                print(f"erlc {path} -> 429 rate limited, waiting {retry}s", flush=True)
                await asyncio.sleep(min(retry, 10))
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


async def announce(text, title="911 Call", tone=False):
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
        if tone and ALERT_TONES and tone_path:
            await play_queue.put(tone_path)
        await play_queue.put(path)
        print("audio queued for playback", flush=True)


def pcm_to_wav(pcm):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(48000)
        handle.writeframes(pcm)
    return buf.getvalue()


async def transcribe(wav_bytes):
    form = aiohttp.FormData()
    form.add_field("model_id", STT_MODEL)
    form.add_field("file", wav_bytes, filename="audio.wav", content_type="audio/wav")
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


def build_dispatch_system(region):
    return (
        f"You are Oversite Dispatch, a professional emergency dispatcher working in "
        f"{region}, handling police and sheriff radio traffic. Talk exactly the way a "
        f"real dispatcher in {region} talks: use the real radio codes, signals, "
        f"phonetic alphabet, and calm, clipped cadence that agencies there actually "
        f"use. Answer with exactly one short radio transmission.\n"
        "Rules:\n"
        "- Keep every reply to ONE short sentence. Radio brevity. No preamble, no sign-off.\n"
        "- Do not include the unit's callsign in your reply; it is added automatically. "
        "Give only the dispatch response itself.\n"
        "- You are dispatch talking TO the unit. Never speak in the first person about "
        "the unit's status. Never say 'I am attached' or 'I'm en route'. Say 'show you "
        "attached' or 'copy, show you en route'.\n"
        "- Use the correct radio codes and phrasing for your region and echo status "
        "changes back to the unit, for example 'show you 10-8' or the local equivalent.\n"
        "- NEVER read back, list, or restate a call's details (location, description, "
        "caller, call number) unless the unit literally asks you to repeat or read back "
        "the call. When a unit attaches to a call, marks en route, or gives a status "
        "update, ONLY acknowledge the action. For example, if a unit says they are "
        "attaching to a call, reply exactly like 'copy, show you attached and en route' "
        "and nothing more. Do not mention what the call is about.\n"
        "- You cannot look up plates, warrants, names, or run records. If asked to run "
        "one, advise the unit the return is negative or to stand by, staying in character.\n"
        "- Only respond to genuine police, sheriff, or emergency radio traffic. If the "
        "transmission is off-topic, a joke, small talk, or a personal or non-police "
        "question (for example asking what you had for lunch), do NOT respond. In that "
        "case reply with the single word IGNORE and nothing else.\n"
        "- If it IS radio traffic for dispatch but you cannot make out what the unit is "
        "saying or asking because it is garbled or cut off, do NOT guess a response. "
        "Ask them to repeat, for example '10-9, say again' or 'you are unreadable, say "
        "again'.\n"
        "- Never break character, never say you are an AI, never use markdown or emojis.\n"
        "- Output only the words dispatch would speak over the radio."
    )


def build_call_system(region):
    return (
        f"You are a professional police and emergency dispatcher working in {region}. "
        f"You are handed a computer-aided-dispatch (CAD) record for a new emergency "
        f"call and must broadcast it to units over the radio, exactly the way a real "
        f"dispatcher in {region} would, using that region's real radio codes, priority "
        f"language, and calm cadence.\n"
        "Rules:\n"
        "- One broadcast, two or three short sentences at most.\n"
        "- State the nature of the call and the location. Say the location only once, "
        "do not repeat it.\n"
        "- Direct the appropriate units to respond with the correct priority code.\n"
        "- If a closest available unit is provided, assign that exact unit by callsign "
        "to respond, for example 'Unit 1-Sam-32, you are closest, respond Code 3'.\n"
        "- End by stating the time exactly as given in the record.\n"
        "- Do not invent any detail that is not in the record. Do not add a call-taker "
        "name, phone number, or facts you were not given.\n"
        "- No markdown, no emojis, no preamble, no sign-off.\n"
        "- Output only the words dispatch would speak over the air."
    )


DISPATCH_SYSTEM = build_dispatch_system(DISPATCH_REGION)
CALL_SYSTEM = build_call_system(DISPATCH_REGION)


def set_region(region):
    global DISPATCH_REGION, DISPATCH_SYSTEM, CALL_SYSTEM
    DISPATCH_REGION = region
    DISPATCH_SYSTEM = build_dispatch_system(region)
    CALL_SYSTEM = build_call_system(region)


async def safe_respond(interaction, text):
    try:
        await interaction.response.send_message(text, ephemeral=True)
    except Exception as exc:
        print(f"interaction response failed: {exc}", flush=True)


@command_tree.command(
    name="region",
    description="Set the real-world area dispatch talks like (state, country, or city)",
    guild=DISPATCH_GUILD,
)
@discord.app_commands.describe(area="For example: Texas, Alaska, Dubai, United Kingdom")
@discord.app_commands.default_permissions(manage_guild=True)
async def region_command(interaction, area: str):
    area = " ".join(area.split()).strip()
    if not area:
        await safe_respond(interaction, "Give me an area, like Texas, Alaska, or Dubai.")
        return
    set_region(area)
    print(f"region changed to {DISPATCH_REGION} by {interaction.user}", flush=True)
    await safe_respond(interaction,
        f"Dispatch is now running as **{DISPATCH_REGION}**. New calls and radio "
        f"replies will use that area's codes and style.")


@command_tree.command(
    name="link",
    description="Set your radio callsign (and Roblox name if it differs from your Discord name)",
    guild=DISPATCH_GUILD,
)
@discord.app_commands.describe(
    callsign="Your radio callsign, e.g. 1S-32",
    roblox="Your Roblox username — only needed if it is different from your Discord name")
async def link_command(interaction, callsign: str, roblox: str = ""):
    callsign = " ".join(callsign.split()).strip()
    roblox = roblox.strip()
    if not callsign:
        await safe_respond(interaction, "Give me your callsign, like 1S-32.")
        return
    callsign_links[interaction.user.id] = {"callsign": callsign, "roblox": roblox}
    print(f"{interaction.user} linked callsign {callsign} roblox '{roblox}'", flush=True)
    extra = f", matching in-game name **{roblox}**" if roblox else " (matching by your Discord name)"
    await safe_respond(interaction,
        f"Linked. Callsign **{callsign}**{extra}. When you call a traffic stop, dispatch "
        f"will pull you back automatically if the subject flees.")


@command_tree.command(
    name="clear",
    description="Clear from your traffic stop and return to the main channel",
    guild=DISPATCH_GUILD,
)
async def clear_command(interaction):
    active_stops.pop(interaction.user.id, None)
    moved = await move_member(interaction.user, VOICE_CHANNEL_ID)
    note = " and returned you to the main channel" if moved else ""
    await safe_respond(interaction, f"10-4, showing you clear{note}.")


async def anthropic_call(system, user_msg, max_tokens=200):
    if not AI_ENABLED:
        return None
    payload = {
        "model": AI_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_msg}],
    }
    headers = {
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        async with http.post(f"{ANTHROPIC_BASE}/messages", headers=headers, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                print(f"anthropic error {resp.status}: {body[:200]}", flush=True)
                return None
            data = await resp.json()
    except Exception as exc:
        print(f"anthropic request failed: {exc}", flush=True)
        return None
    for block in data.get("content") or []:
        if block.get("type") == "text":
            reply = (block.get("text") or "").strip()
            if reply:
                return reply
    return None


async def compose_dispatch(call, nearest=None):
    if not AI_ENABLED:
        return build_call_line(call, nearest or "")
    desc = autocorrect((call.get("Description") or "").strip())
    loc = (call.get("PositionDescriptor") or "").strip()
    team = (call.get("Team") or "").strip()
    number = call.get("CallNumber")
    record = (
        f"Nature of call: {desc or 'unknown'}\n"
        f"Location: {loc or 'unknown'}\n"
        f"Units requested: {team or 'any available'}\n"
        f"Incident number: {number}\n"
        f"Time: {local_time_str()} hours"
    )
    if nearest:
        record += f"\nClosest available unit: {nearest}"
    reply = await anthropic_call(CALL_SYSTEM, record, max_tokens=220)
    return reply or build_call_line(call, nearest or "")


async def dispatch_ai_reply(text, callsign):
    if not AI_ENABLED:
        return None
    user_msg = f"Unit {callsign} says: {text}" if callsign else text
    payload = {
        "model": AI_MODEL,
        "max_tokens": 200,
        "system": DISPATCH_SYSTEM,
        "messages": [{"role": "user", "content": user_msg}],
    }
    headers = {
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        async with http.post(f"{ANTHROPIC_BASE}/messages", headers=headers, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                print(f"anthropic error {resp.status}: {body[:200]}", flush=True)
                return None
            data = await resp.json()
    except Exception as exc:
        print(f"anthropic request failed: {exc}", flush=True)
        return None
    for block in data.get("content") or []:
        if block.get("type") == "text":
            reply = (block.get("text") or "").strip()
            if reply:
                return reply
    return None


def normalize_intent(text, callsign):
    low = text.lower()
    if callsign:
        low = low.replace(callsign.lower(), " ")
    low = low.replace("dispatch", " ")
    low = re.sub(r"[^a-z\s]", " ", low)
    low = re.sub(r"\s+", " ", low).strip()
    return low


def match_cached_intent(key):
    if not key:
        return None
    if key in response_cache:
        return key
    matches = difflib.get_close_matches(key, list(response_cache), n=1, cutoff=0.85)
    return matches[0] if matches else None


FALLBACK_REPLIES = {
    "foot pursuit": ["copy your foot pursuit, units en route to assist, advise your direction of travel"],
    "in pursuit": ["copy, you are in pursuit, all units clear the air for the pursuit",
                   "copy your pursuit, break, all units hold traffic for the primary unit"],
    "shots fired": ["copy shots fired, all available units respond Code 3",
                    "copy your shots fired, units en route Code 3, use caution"],
    "traffic stop": ["copy your traffic stop, advise if you need backup",
                     "copy, show you out on a traffic stop, advise plate and location"],
    "unavailable": ["copy, show you unavailable, 10-7",
                    "10-4, show you 10-7 and unavailable"],
    "available": ["copy, show you available and 10-8",
                  "10-4, show you back available and in service"],
    "out of service": ["copy, show you 10-7, out of service"],
    "in service": ["copy, show you 10-8, in service",
                   "10-4, show you back in service"],
    "attach": ["copy, show you attached to the call and en route, 10-76",
               "10-4, you are attached, show you en route"],
    "en route": ["copy, show you en route, 10-76"],
    "on scene": ["copy, show you on scene, 10-97",
                 "10-4, show you 10-23 on scene"],
    "scene secure": ["copy, Code 4, scene is secure"],
    "requesting backup": ["copy, backup en route to your location, Code 3"],
    "need backup": ["copy, backup en route to your location, Code 3"],
    "radio check": ["copy your radio check, you are loud and clear"],
    "show me clear": ["copy, show you clear and available"],
    "pursuit": ["copy, all units clear the air"],
    "copy": ["10-4"],
}


def fallback_reply(key):
    if not key:
        return None
    for phrase, replies in FALLBACK_REPLIES.items():
        if phrase in key:
            return random.choice(replies)
    matches = difflib.get_close_matches(key, list(FALLBACK_REPLIES), n=1, cutoff=0.82)
    if matches:
        return random.choice(FALLBACK_REPLIES[matches[0]])
    return None


async def dispatch_reply_body(text, callsign):
    key = normalize_intent(text, callsign)
    fb = fallback_reply(key)
    if fb:
        print(f"using built-in reply for '{key}' (no api call)", flush=True)
        return fb
    hit = match_cached_intent(key)
    if hit and len(response_cache[hit]) >= AI_CACHE_VARIANTS:
        print(f"reusing saved reply for '{hit}' (no api call)", flush=True)
        return random.choice(response_cache[hit])
    body = await dispatch_ai_reply(text, callsign)
    if body:
        if body.strip().strip(".!").upper() == "IGNORE":
            return IGNORE
        store = response_cache.setdefault(hit or key, [])
        if body not in store:
            store.append(body)
        print(f"saved reply for '{hit or key}' ({len(store)} variant(s))", flush=True)
        return body
    return None


REQUEST_WORDS = ("requesting", "request", "repeat", "say", "come", "can", "could",
                 "need", "asking", "asks", "please", "give", "what")


def is_for_dispatch(text):
    return "dispatch" in text.lower()


def wants_repeat(text):
    low = text.lower()
    if "attach" in low:
        return False
    triggers = ("repeat", "say again", "come again", "one more time",
                "read it back", "read back", "run it back", "go again",
                "what was the last", "what was that last", "what was that call")
    return any(t in low for t in triggers)


CALLSIGN_NUMS = {
    "zero", "oh", "o", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty",
    "fifty", "sixty", "seventy", "eighty", "ninety",
}
CALLSIGN_PHON = {
    "adam", "boy", "charlie", "david", "edward", "frank", "george", "henry", "ida",
    "john", "king", "lincoln", "mary", "nora", "ocean", "paul", "queen", "robert",
    "sam", "tom", "union", "victor", "william", "xray", "young", "zebra", "alpha",
    "bravo", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet", "kilo",
    "lima", "mike", "november", "oscar", "papa", "quebec", "romeo", "sierra", "tango",
    "uniform", "whiskey", "yankee", "zulu",
}


def is_callsign_token(tok):
    t = tok.lower().strip(",.-'")
    if not t:
        return False
    if t.isalnum() and any(c.isdigit() for c in t) and len(t) <= 6:
        return True
    if t.isalpha() and len(t) <= 2:
        return True
    return t in CALLSIGN_NUMS or t in CALLSIGN_PHON


def extract_callsign(text):
    match = re.search(r"dispatch\w*", text.lower())
    if match is None:
        return ""
    rest = text[match.end():].strip(" ,.-")
    tokens = re.split(r"\s+", rest)
    parts = []
    for tok in tokens:
        if tok.lower().strip(",.-") in REQUEST_WORDS:
            break
        if not is_callsign_token(tok):
            break
        parts.append(tok.strip(",.-"))
        if len(parts) >= 6 or tok[-1:] in ".?!":
            break
    has_number = any(any(c.isdigit() for c in p) or p.lower() in CALLSIGN_NUMS for p in parts)
    callsign = " ".join(parts).strip(" ,.-")
    if not callsign or len(callsign) > 24 or not has_number:
        return ""
    return callsign


def strip_callsign_echo(body):
    s = body.lstrip()
    start = len("unit ") if s.lower().startswith("unit ") else 0
    comma = s.find(",", start)
    if comma == -1:
        return body
    head = [t for t in re.split(r"\s+", s[start:comma]) if t]
    if head and all(is_callsign_token(t) for t in head):
        return s[comma + 1:].lstrip()
    return body


STATUS_MAP = [
    ("out of service", "10-7, out of service"),
    ("unavailable", "unavailable"),
    ("in service", "10-8, in service"),
    ("back available", "10-8, available"),
    ("available", "available"),
    ("foot pursuit", "in a foot pursuit"),
    ("in pursuit", "in pursuit"),
    ("en route", "en route"),
    ("responding", "en route"),
    ("on scene", "on scene"),
    ("on a traffic stop", "on a traffic stop"),
    ("traffic stop", "on a traffic stop"),
    ("vehicle stop", "on a traffic stop"),
    ("on a stop", "on a traffic stop"),
    ("attached", "on a call"),
    ("show me clear", "clear"),
    ("clearing", "clear"),
    ("meal break", "10-7, meal break"),
]


def _flat(text):
    return text.lower().replace("’", "").replace("'", "")


def detect_status(text):
    low = _flat(text)
    for phrase, label in STATUS_MAP:
        if phrase in low:
            return label
    return None


def wants_status_board(text):
    low = _flat(text)
    triggers = ("unit status", "status board", "roll call", "status check",
                "who is available", "whos available", "who is on", "whos on",
                "units available", "unit check", "status of units", "all units status")
    return any(t in low for t in triggers)


def wants_calls_holding(text):
    low = _flat(text)
    triggers = ("calls holding", "call holding", "calls are holding", "any active calls",
                "active calls", "any calls", "calls waiting", "pending calls",
                "calls in queue", "what calls")
    return any(t in low for t in triggers)


def wants_clear_stop(text):
    low = _flat(text)
    triggers = ("clear", "concluded", "conclude", "done", "finished", "complete",
                "wrapping up", "wrap up", "resuming patrol", "back in service",
                "in service", "available", "10-8", "ten eight")
    return any(t in low for t in triggers)


def read_status_board(callsign=""):
    now = time.time()
    entries = [(cs, v["status"]) for cs, v in status_board.items() if now - v["time"] < 10800]
    ack = f"Unit {callsign}, " if callsign else ""
    if not entries:
        return f"{ack}no unit statuses on file at this time."
    parts = [f"{ack}current unit status."]
    for cs, st in entries[:12]:
        parts.append(f"Unit {cs} shows {st}.")
    return " ".join(parts)


def read_calls_holding(callsign=""):
    calls = list(open_calls.values())
    ack = f"Unit {callsign}, " if callsign else ""
    if not calls:
        return f"{ack}no calls holding at this time, all quiet."
    word = "call" if len(calls) == 1 else "calls"
    parts = [f"{ack}you have {len(calls)} {word} holding."]
    for c in calls[:6]:
        num = c.get("CallNumber")
        desc = autocorrect((c.get("Description") or "").strip())
        loc = (c.get("PositionDescriptor") or "").strip()
        seg = f"Call {num}" if num is not None else "Call"
        if desc:
            seg += f", {desc}"
        if loc:
            seg += f", at {loc}"
        ts = stamp_time(c.get("StartedAt"))
        if ts:
            seg += f", received {ts}"
        parts.append(seg + ".")
    return " ".join(parts)


def norm_callsign(cs):
    return re.sub(r"[^a-z0-9]", "", str(cs or "").lower())


def clean_name(name):
    cleaned = re.sub(r"[\(\[][^\)\]]*[\)\]]", "", str(name or "")).strip()
    return cleaned or str(name or "").strip()


def _num(d, *keys):
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
    return None


def extract_player_pos(player):
    loc = player.get("Location") if isinstance(player.get("Location"), dict) else {}
    x = _num(loc, "LocationX", "X")
    z = _num(loc, "LocationZ", "Z")
    if x is None:
        x = _num(player, "LocationX", "X")
    if z is None:
        z = _num(player, "LocationZ", "Z")
    if x is None or z is None:
        return None
    return (x, z)


def extract_street(player):
    loc = player.get("Location") if isinstance(player.get("Location"), dict) else {}
    return (loc.get("StreetName") or player.get("StreetName") or "").strip()


async def player_positions():
    global _players_debugged
    data = await erlc_get("/server?Players=true")
    out = {}
    if isinstance(data, dict):
        players = data.get("Players")
        if isinstance(players, list):
            if players and not _players_debugged:
                _players_debugged = True
                print(f"players API sample: {players[0]}", flush=True)
            for p in players:
                info = (extract_player_pos(p), extract_street(p))
                name = str(p.get("Player") or "").split(":")[0]
                for ident in (name, p.get("Callsign")):
                    k = norm_callsign(ident)
                    if k:
                        out[k] = info
    elif data is not None:
        print(f"players API returned unexpected shape: {str(data)[:200]}", flush=True)
    return out


def extract_call_pos(call):
    pos = call.get("Position") if isinstance(call.get("Position"), dict) else None
    if pos is not None:
        x = _num(pos, "X", "LocationX")
        z = _num(pos, "Z", "LocationZ")
        if x is not None and z is not None:
            return (x, z)
    x = _num(call, "X", "LocationX")
    z = _num(call, "Z", "LocationZ")
    if x is not None and z is not None:
        return (x, z)
    return None


async def duty_units():
    data = await erlc_get("/server?Players=true")
    out = []
    if isinstance(data, dict) and isinstance(data.get("Players"), list):
        for p in data["Players"]:
            cs = str(p.get("Callsign") or "").strip()
            team = str(p.get("Team") or "").lower()
            pos = extract_player_pos(p)
            if cs and pos and any(t in team for t in CALL_TEAMS):
                out.append((cs, pos))
    return out


def pick_nearest(call, units):
    cpos = extract_call_pos(call)
    if cpos is None or not units:
        return None
    best, best_d = None, None
    for cs, pos in units:
        d = ((pos[0] - cpos[0]) ** 2 + (pos[1] - cpos[1]) ** 2) ** 0.5
        if best_d is None or d < best_d:
            best, best_d = cs, d
    return best


async def move_member(member, channel_id):
    if not channel_id or member is None or member.voice is None:
        return False
    if member.voice.channel is not None and member.voice.channel.id == channel_id:
        return True
    channel = member.guild.get_channel(channel_id)
    if channel is None:
        return False
    try:
        await member.move_to(channel)
        return True
    except Exception as exc:
        print(f"could not move {getattr(member, 'display_name', '?')}: {exc}", flush=True)
        return False


async def start_traffic_stop(member, spoken_callsign=""):
    who = getattr(member, "display_name", "?")
    if not TRAFFIC_STOP_RETURN:
        return
    link = callsign_links.get(member.id) or {}
    idents = []
    if link.get("roblox"):
        idents.append(link["roblox"])
    for attr in ("name", "global_name", "display_name"):
        v = getattr(member, attr, None)
        if v:
            idents.append(v)
    if link.get("callsign"):
        idents.append(link["callsign"])
    positions = await player_positions()
    key = None
    for ident in idents:
        nk = norm_callsign(ident)
        if nk and nk in positions:
            key = nk
            break
    radio_cs = link.get("callsign") or spoken_callsign or clean_name(who)
    if key is None:
        print(f"traffic stop: could not match {who} to an in-game player. "
              f"tried {[norm_callsign(i) for i in idents]}, available {sorted(positions)}", flush=True)
        return
    pos = positions[key][0]
    now = time.time()
    active_stops[member.id] = {"key": key, "member": member, "last": pos, "last_time": now,
                               "since": now, "callsign": radio_cs}
    print(f"traffic stop started: {who} matched '{key}' at {pos}", flush=True)


async def clear_traffic_stop(member, callsign=""):
    active_stops.pop(member.id, None)
    await move_member(member, VOICE_CHANNEL_ID)
    print(f"traffic stop cleared for {getattr(member, 'display_name', '?')}", flush=True)
    ack = f"Unit {callsign}, " if callsign else ""
    await announce(f"{ack}10-4, showing you clear of the traffic stop.", title="Clear")


def duty_idents(member):
    link = callsign_links.get(member.id) or {}
    idents = []
    if link.get("roblox"):
        idents.append(link["roblox"])
    for attr in ("name", "global_name", "display_name"):
        v = getattr(member, attr, None)
        if v:
            idents.append(v)
    return {norm_callsign(i) for i in idents if i}


async def get_ingame_callsign(member):
    wanted = duty_idents(member)
    data = await erlc_get("/server?Players=true")
    if not isinstance(data, dict):
        return None
    players = data.get("Players")
    if not isinstance(players, list):
        return None
    for p in players:
        uname = norm_callsign(str(p.get("Player") or "").split(":")[0])
        if uname and uname in wanted:
            return str(p.get("Callsign") or "").strip() or None
    return None


async def apply_duty_nick(member):
    cs = await get_ingame_callsign(member)
    if not cs:
        print(f"nick: {member.display_name} joined RTO but no in-game callsign found", flush=True)
        return
    base = re.sub(r"^\[[^\]]*\]\s*", "", member.display_name).strip()
    new_nick = f"[{cs}] {base}"[:32]
    try:
        if member.id not in nick_original:
            nick_original[member.id] = member.nick
        await member.edit(nick=new_nick, reason="On-duty callsign")
        print(f"nick: set {member.display_name} -> {new_nick}", flush=True)
    except discord.Forbidden:
        print(f"nick: cannot rename {member.display_name} (server owner, or their role is above the bot)", flush=True)
    except Exception as exc:
        print(f"nick: failed for {member.display_name}: {exc}", flush=True)


async def revert_duty_nick(member):
    if member.id not in nick_original:
        return
    original = nick_original.pop(member.id)
    try:
        await member.edit(nick=original, reason="Off duty")
        print(f"nick: reverted {member.display_name}", flush=True)
    except Exception as exc:
        print(f"nick: revert failed for {member.display_name}: {exc}", flush=True)


async def nick_watch_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        if CALLSIGN_NICK and nick_original:
            data = await erlc_get("/server?Players=true")
            players = data.get("Players") if isinstance(data, dict) else None
            if isinstance(players, list):
                on_duty = set()
                for p in players:
                    uname = norm_callsign(str(p.get("Player") or "").split(":")[0])
                    if uname and str(p.get("Callsign") or "").strip():
                        on_duty.add(uname)
                guild = client.get_guild(GUILD_ID)
                for uid in list(nick_original.keys()):
                    member = guild.get_member(uid) if guild is not None else None
                    if member is None:
                        nick_original.pop(uid, None)
                        continue
                    if not (duty_idents(member) & on_duty):
                        await revert_duty_nick(member)
        await asyncio.sleep(20)


async def end_stop_pursuit(uid, stop, street):
    active_stops.pop(uid, None)
    await move_member(stop["member"], VOICE_CHANNEL_ID)
    cs = stop["callsign"]
    where = f" near {street}" if street else ""
    await announce(
        f"All units, Unit {cs} is in pursuit, subject fleeing a traffic stop{where}. "
        f"Clear the air.", title="Pursuit", tone=True)
    print(f"pursuit triggered for {cs}", flush=True)


async def stop_watch_loop():
    await client.wait_until_ready()
    print("traffic-stop watch active", flush=True)
    while not client.is_closed():
        if active_stops:
            positions = await player_positions()
            now = time.time()
            for uid, stop in list(active_stops.items()):
                if now - stop["since"] > STOP_MAX_SECONDS:
                    active_stops.pop(uid, None)
                    continue
                entry = positions.get(stop["key"])
                if entry is None:
                    continue
                pos, street = entry
                if pos is None:
                    continue
                last = stop.get("last")
                last_time = stop.get("last_time")
                stop["last"] = pos
                stop["last_time"] = now
                if last is None or last_time is None:
                    continue
                dt = now - last_time
                if dt <= 0:
                    continue
                dist = ((pos[0] - last[0]) ** 2 + (pos[1] - last[1]) ** 2) ** 0.5
                speed = dist / dt
                if speed >= 3:
                    print(f"stop {stop['callsign']}: {speed:.0f} units/sec (flee at {FLEE_SPEED})", flush=True)
                if FLEE_SPEED <= speed < 500:
                    await end_stop_pursuit(uid, stop, street)
        await asyncio.sleep(STOP_POLL_SECONDS)


def has_real_words(text):
    cleaned = re.sub(r"\[[^\]]*\]", " ", text)
    return len(re.findall(r"\w{2,}", cleaned)) >= 1


FILLERS = {"um", "umm", "uh", "uhh", "uhm", "erm", "hmm", "mhm", "eh"}


def clean_transcript(text):
    tokens = text.split()
    out = []
    for tok in tokens:
        bare = tok.lower().strip(",.!?-'’")
        if bare in FILLERS:
            continue
        if "-" in tok:
            segs = [s for s in tok.split("-") if s]
            if len(segs) > 1:
                last = segs[-1]
                if all(len(s) <= 3 and last.lower().startswith(s.lower()) for s in segs[:-1]):
                    tok = last
        if out and out[-1].lower().strip(",.!?") == tok.lower().strip(",.!?"):
            continue
        out.append(tok)
    return " ".join(out) if out else text


async def handle_utterance(member, pcm):
    if len(pcm) < MIN_UTTER_BYTES:
        return
    if audioop is not None:
        try:
            if audioop.rms(pcm, 2) < SILENCE_RMS:
                return
        except Exception:
            pass
    text = await transcribe(pcm_to_wav(pcm))
    if not text or not has_real_words(text):
        return
    text = clean_transcript(text)
    who = getattr(member, "display_name", "unit")
    print(f"heard {who}: {text}", flush=True)
    if not is_for_dispatch(text):
        return
    callsign = extract_callsign(text)
    if wants_repeat(text):
        if last_call is not None:
            ack = f"Unit {callsign}, copy. " if callsign else "Copy. "
            await announce(ack + build_call_line(last_call), title="Repeat")
        else:
            ack = f"Unit {callsign}, " if callsign else ""
            await announce(f"{ack}dispatch has no active calls to repeat at this time.", title="Repeat")
        return
    if wants_status_board(text):
        await announce(read_status_board(callsign), title="Unit Status")
        return
    if wants_calls_holding(text):
        await announce(read_calls_holding(callsign), title="Calls Holding")
        return
    status = detect_status(text)
    clearing = wants_clear_stop(text)
    if clearing and member.id in active_stops:
        await clear_traffic_stop(member, callsign)
        if callsign:
            status_board[callsign] = {"status": "10-8, in service", "time": time.time()}
        return
    if status:
        if callsign:
            status_board[callsign] = {"status": status, "time": time.time()}
            print(f"status board: {callsign} -> {status}", flush=True)
        if "traffic stop" in status and not clearing:
            await start_traffic_stop(member, callsign)
    if not status and not normalize_intent(text, callsign):
        ack = f"Unit {callsign}, " if callsign else ""
        await announce(f"{ack}you are unreadable, say again.", title="Say Again")
        return
    body = await dispatch_reply_body(text, callsign)
    if body is IGNORE:
        print("ignored off-topic transmission", flush=True)
        return
    if body:
        if callsign:
            await announce(f"Unit {callsign}, " + strip_callsign_echo(body), title="Dispatch")
        else:
            await announce(body, title="Dispatch")
    else:
        ack = f"Unit {callsign}, " if callsign else ""
        await announce(f"{ack}dispatch copies, 10-4.", title="Dispatch")


if VOICE_RECV_AVAILABLE:

    class ListenSink(voice_recv.AudioSink):
        def __init__(self, loop):
            super().__init__()
            self.loop = loop
            self.buffers = {}
            self.decoders = {}

        def wants_opus(self):
            return True

        def _dave_decrypt(self, user_id, opus):
            if not HAVE_DAVEY:
                return opus
            vc = self.voice_client
            conn = getattr(vc, "_connection", None) if vc is not None else None
            sess = getattr(conn, "dave_session", None) if conn is not None else None
            if sess is None or not getattr(sess, "ready", False):
                return opus
            try:
                if sess.can_passthrough(user_id):
                    return opus
                return sess.decrypt(user_id, davey.MediaType.audio, opus)
            except Exception:
                return None

        def write(self, user, data):
            if user is None:
                return
            if isinstance(data.packet, SilencePacket):
                return
            opus = getattr(data, "opus", None)
            if not opus:
                return
            opus = self._dave_decrypt(user.id, opus)
            if not opus:
                return
            dec = self.decoders.get(user.id)
            if dec is None:
                dec = discord.opus.Decoder()
                self.decoders[user.id] = dec
            try:
                pcm = dec.decode(bytes(opus), fec=False)
            except Exception:
                return
            if pcm:
                self.buffers.setdefault(user.id, bytearray()).extend(pcm)

        @voice_recv.AudioSink.listener()
        def on_voice_member_speaking_stop(self, member):
            pcm = self.buffers.pop(member.id, None)
            self.decoders.pop(member.id, None)
            if pcm:
                asyncio.run_coroutine_threadsafe(handle_utterance(member, bytes(pcm)), self.loop)

        def cleanup(self):
            self.buffers.clear()
            self.decoders.clear()


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

                is_tone = path == tone_path
                options = None if is_tone else (
                    f'-filter:a "atempo={SPEED}"' if SPEED and SPEED != 1.0 else None)
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
            if path != tone_path:
                try:
                    os.remove(path)
                except OSError:
                    pass
            play_queue.task_done()


async def poll_calls():
    global last_call, _call_debugged
    data = await erlc_get("/server?EmergencyCalls=true")
    if not isinstance(data, dict):
        return
    calls = data.get("EmergencyCalls")
    if not isinstance(calls, list):
        return
    calls = [c for c in calls if is_police_call(c)]
    if calls and not _call_debugged:
        _call_debugged = True
        print(f"call API sample: {calls[0]}", flush=True)
    open_calls.clear()
    for call in calls:
        number = call.get("CallNumber")
        if number is not None:
            open_calls[number] = call
    pending = []
    for call in calls:
        number = call.get("CallNumber")
        started = call.get("StartedAt", 0)
        key = ("call", number)
        if started < boot_time or key in seen_keys:
            continue
        seen_keys.add(key)
        pending.append(call)
    units = await duty_units() if pending else []
    for call in pending:
        last_call = call
        nearest = pick_nearest(call, units)
        line = await compose_dispatch(call, nearest)
        if len(open_calls) > 1:
            line = f"{line} Be advised, you now have {len(open_calls)} calls holding."
        await announce(line, tone=is_priority(call))


async def dispatch_loop():
    await client.wait_until_ready()
    print(f"dispatch loop started, polling emergency calls every {POLL_SECONDS}s", flush=True)
    while not client.is_closed():
        await poll_calls()
        await asyncio.sleep(max(POLL_SECONDS, 15) if active_stops else POLL_SECONDS)


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


async def sync_commands():
    global commands_synced
    if commands_synced:
        return
    try:
        await command_tree.sync()
        await command_tree.sync(guild=DISPATCH_GUILD)
        commands_synced = True
        print("slash commands synced — /region ready, old commands removed", flush=True)
    except Exception as exc:
        print(f"command sync failed: {exc}", flush=True)


@client.event
async def on_voice_state_update(member, before, after):
    if not CALLSIGN_NICK or member.bot:
        return
    joined = after.channel is not None and (
        before.channel is None or before.channel.id != after.channel.id)
    if joined and member.id not in nick_original:
        await apply_duty_nick(member)


@client.event
async def on_ready():
    global http, tone_path
    if http is None:
        http = aiohttp.ClientSession()
    print(f"dispatch online as {client.user}", flush=True)
    print(f"running build: {BUILD}", flush=True)
    print(f"region: {DISPATCH_REGION}", flush=True)
    await sync_commands()
    if VOICE_CMD_ENABLED:
        print("voice commands: ENABLED", flush=True)
    else:
        reason = "disabled by config" if not VOICE_COMMANDS else (
            "voice-recv extension missing" if not VOICE_RECV_AVAILABLE else "libopus not loaded")
        print(f"voice commands: OFF ({reason}) — 911 dispatch still runs normally", flush=True)
    if AI_ENABLED:
        print(f"ai responses: ENABLED (model {AI_MODEL})", flush=True)
    else:
        print("ai responses: OFF (set ANTHROPIC_API_KEY to let dispatch answer radio traffic)", flush=True)
    if ALERT_TONES and tone_path is None:
        tone_path = await client.loop.run_in_executor(None, make_tone)
        print(f"alert tones: {'ready' if tone_path else 'unavailable'}", flush=True)
    if TRAFFIC_STOP_RETURN:
        print(f"traffic-stop auto-return: ON (flee speed {FLEE_SPEED}/sec, needs Move Members perm + /link)", flush=True)
    else:
        print("traffic-stop auto-return: OFF (set TRAFFIC_STOP_RETURN=1 to enable)", flush=True)
    if CALLSIGN_NICK:
        print("on-duty callsign nicknames: ON (needs Manage Nicknames perm; cannot rename the server owner)", flush=True)
    await ensure_voice()
    client.loop.create_task(playback_worker())
    client.loop.create_task(dispatch_loop())
    client.loop.create_task(voice_guard())
    client.loop.create_task(stop_watch_loop())
    client.loop.create_task(nick_watch_loop())


client.run(TOKEN)
