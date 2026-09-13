import os
import io
import re
import json
import wave
import time
import random
import asyncio
import traceback
import signal
from array import array
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

BUILD = "memory-4"
_BOOT_T0 = time.time()

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

TOKEN = os.environ["DISCORD_TOKEN"]
ERLC_KEY = os.environ.get("ERLC_SERVER_KEY", "")
BOT_ORDER_ID = os.environ.get("BOT_ORDER_ID", "")
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
XI_KEY = os.environ["ELEVENLABS_API_KEY"]
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")
XI_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5")  # the lowest-latency voice model
GUILD_ID = int(os.environ.get("DISPATCH_GUILD_ID", "0") or "0")
VOICE_CHANNEL_ID = int(os.environ.get("DISPATCH_VOICE_CHANNEL_ID", "0") or "0")
TEXT_CHANNEL_ID = int(os.environ.get("DISPATCH_TEXT_CHANNEL_ID", "0"))
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "5"))
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
STATUS_CHECKS = os.environ.get("STATUS_CHECKS", "1").lower() not in ("0", "false", "no", "off")
STATUS_CHECK_SECONDS = int(os.environ.get("STATUS_CHECK_SECONDS", "420"))
STATUS_CHECK_GRACE = int(os.environ.get("STATUS_CHECK_GRACE", "120"))
STATUS_CHECK_MOVE = float(os.environ.get("STATUS_CHECK_MOVE", "8"))
CALLSIGN_NICK = os.environ.get("CALLSIGN_NICK", "0").lower() not in ("0", "false", "no", "off")
OFFICER_DOWN = os.environ.get("OFFICER_DOWN", "1").lower() not in ("0", "false", "no", "off")
OFFICER_DOWN_POLL = float(os.environ.get("OFFICER_DOWN_POLL", "4"))
SUSPECT_RADIUS = float(os.environ.get("SUSPECT_RADIUS", "60"))
PURSUIT_END_SPEED = float(os.environ.get("PURSUIT_END_SPEED", "10"))
PURSUIT_END_SECONDS = float(os.environ.get("PURSUIT_END_SECONDS", "8"))
PURSUIT_CALLOUT_SECONDS = float(os.environ.get("PURSUIT_CALLOUT_SECONDS", "25"))
CALL_TEAMS = [t.strip().lower() for t in os.environ.get("CALL_TEAMS", "police,sheriff").split(",") if t.strip()]
LOG_HEARD = os.environ.get("LOG_HEARD", "1").lower() not in ("0", "false", "no", "off")
LINK_FILE = os.environ.get("LINK_FILE", "callsign_links.json")
CALL_CLEARED = os.environ.get("CALL_CLEARED", "1").lower() not in ("0", "false", "no", "off")
BOLO_EXPIRE = int(os.environ.get("BOLO_EXPIRE", "3600"))
# How long dispatch waits after a transmission that stopped mid-thought before
# deciding the unit is done, so a stumble is never answered as if it were the
# whole message.
HOLD_SECONDS = float(os.environ.get("DISPATCH_HOLD_SECONDS", "3.0"))
# After "go ahead with that plate", the next transmission from that unit within
# this many seconds is the plate (or the name).
LOOKUP_WINDOW = float(os.environ.get("DISPATCH_LOOKUP_WINDOW", "45"))
# Spelling a plate comes through as several short transmissions. Dispatch
# collects them and waits this long after the unit stops before answering,
# instead of cutting in after the first letter or two.
LOOKUP_HOLD = float(os.environ.get("LOOKUP_HOLD_SECONDS", "3.0"))
# During a pursuit with an air unit up, how often the suspect's road is checked.
TRACK_POLL_SECONDS = float(os.environ.get("TRACK_POLL_SECONDS", "2"))
STATE_SAVE_SECONDS = int(os.environ.get("STATE_SAVE_SECONDS", "20"))
# When an officer calls a traffic stop while sitting in a "Traffic Stop"-style
# voice channel, prepend the nearest postal code to that channel's name, then
# restore the original name once the stop ends / everyone leaves. Needs the
# Manage Channels permission.
TS_CHANNEL_LABELS = os.environ.get("TS_CHANNEL_LABELS", "1").lower() not in ("0", "false", "no", "off")

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
cleared_calls = set()
callsign_links = {}
active_stops = {}
nick_original = {}
# channel_id -> original name, for voice channels currently postal-labelled
stop_channel_original = {}
# Discord limits channel NAME edits to 2 per 10 minutes PER channel. A single
# stop already spends both (one to label, one to restore), so a second stop in
# the SAME VC within 10 min can't be renamed — discord.py silently blocks for
# minutes waiting the limit out, which looks like "it just didn't work". We
# track our own budget and skip (non-blocking) when it's used up, and we defer
# the restore by a grace period so a quick follow-up stop in the same channel
# cancels it and reuses the existing label instead of churning renames.
_rename_history = {}          # channel_id -> [unix timestamps of our renames]
_pending_restores = {}        # channel_id -> asyncio.Task (deferred restore)
RENAME_LIMIT = 2
RENAME_WINDOW = 600.0         # Discord's 2-per-10-min name-edit window
RESTORE_GRACE = 90.0          # wait this long after a stop clears before reverting


def _rename_budget_left(channel_id):
    now = time.time()
    hist = [t for t in _rename_history.get(channel_id, []) if now - t < RENAME_WINDOW]
    _rename_history[channel_id] = hist
    return RENAME_LIMIT - len(hist)


def _record_rename(channel_id):
    _rename_history.setdefault(channel_id, []).append(time.time())


def _seconds_until_budget(channel_id):
    now = time.time()
    hist = sorted(t for t in _rename_history.get(channel_id, []) if now - t < RENAME_WINDOW)
    if len(hist) < RENAME_LIMIT:
        return 0.0
    return max(0.0, RENAME_WINDOW - (now - hist[0]) + 1.0)


def _cancel_pending_restore(channel_id):
    task = _pending_restores.pop(channel_id, None)
    if task is not None and not task.done():
        task.cancel()


def schedule_restore(channel, delay=RESTORE_GRACE):
    # Revert a labelled channel's name after `delay` seconds, unless a new stop
    # in the same channel cancels it first (see label_stop_channel). Guarantees
    # the name always changes back once the stop concludes, without racing the
    # rename limit.
    if channel is None or channel.id not in stop_channel_original:
        return
    _cancel_pending_restore(channel.id)

    async def _run():
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        _pending_restores.pop(channel.id, None)
        # Only revert if it's still labelled and nobody's using it.
        if channel.id in stop_channel_original and not channel_humans(channel):
            await restore_stop_channel(channel)

    _pending_restores[channel.id] = client.loop.create_task(_run())
# last-applied dashboard profile, so we only push actual changes
_last_presence = None
_last_bio = None
bolos = []
seen_kills = set()
officer_last_seen = {}
_players_debugged = False
_call_debugged = False
_kill_debugged = False
_veh_debugged = False
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

    if isinstance(nearest, (list, tuple)):
        nearest_units = [u for u in nearest if u]
    elif nearest:
        nearest_units = [nearest]
    else:
        nearest_units = []

    parts = ["Attention units."]

    if desc and loc:
        parts.append(f"{desc}, at {loc}.")
    elif desc:
        parts.append(f"{desc}.")
    elif loc:
        parts.append(f"Report of an incident at {loc}.")
    else:
        parts.append("Report of an incident, details to follow.")

    if len(nearest_units) == 1:
        parts.append(f"Unit {nearest_units[0]}, you are the closest unit, respond Code 3.")
    elif len(nearest_units) > 1:
        parts.append(
            f"Unit {nearest_units[0]}, you are the closest unit, respond Code 3. "
            f"Unit {nearest_units[1]}, respond as backup."
        )
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


async def fetch_bot_secret(key, diag=False):
    if not (SUPABASE_URL and SUPABASE_ANON_KEY and WORKER_TOKEN and BOT_ORDER_ID and http):
        if diag:
            print(
                f"secret[{key}]: prerequisites missing "
                f"SUPABASE_URL={'y' if SUPABASE_URL else 'n'} "
                f"ANON_KEY={'y' if SUPABASE_ANON_KEY else 'n'} "
                f"WORKER_TOKEN={'y' if WORKER_TOKEN else 'n'} "
                f"BOT_ORDER_ID={BOT_ORDER_ID!r}",
                flush=True,
            )
        return None
    url = f"{SUPABASE_URL}/rest/v1/rpc/runtime_get_bot_secret"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    body = {"_token": WORKER_TOKEN, "_bot_id": BOT_ORDER_ID, "_key": key}
    try:
        async with http.post(url, headers=headers, json=body) as resp:
            raw = await resp.text()
            if diag:
                shown = raw[:200] if resp.status != 200 else f"<{len(raw.strip().strip(chr(34)))} chars>"
                print(
                    f"secret[{key}]: bot_id={BOT_ORDER_ID!r} "
                    f"HTTP {resp.status} body={shown}",
                    flush=True,
                )
            if resp.status != 200:
                return None
            try:
                val = json.loads(raw)
            except Exception:
                val = raw
            return val.strip() if isinstance(val, str) and val.strip() else None
    except Exception as exc:
        print(f"config fetch failed for {key}: {exc}", flush=True)
        return None


async def load_region_from_dashboard(diag=False):
    """Pull the dashboard-chosen region and apply it.

    The dashboard is the source of truth: an owner picks a state/country on the
    site and the bot adopts it on startup and on each periodic refresh, with no
    redeploy. Region lives in bot_config via the dispatch-region edge function.
    """
    if not (SUPABASE_URL and SUPABASE_ANON_KEY and WORKER_TOKEN and BOT_ORDER_ID and http):
        return
    url = f"{SUPABASE_URL}/functions/v1/dispatch-region"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    body = {"botId": BOT_ORDER_ID, "workerToken": WORKER_TOKEN}
    try:
        async with http.post(url, headers=headers, json=body) as resp:
            raw = await resp.text()
            if resp.status != 200:
                if diag:
                    print(f"region load HTTP {resp.status} body={raw[:200]!r}", flush=True)
                return
            data = json.loads(raw)
            val = data.get("region") if isinstance(data, dict) else None
            if val:
                prev = DISPATCH_REGION
                set_region(val)
                if DISPATCH_REGION != prev:
                    print(f"region loaded from dashboard: {DISPATCH_REGION}", flush=True)
    except Exception as exc:
        print(f"load_region failed (non-fatal): {exc}", flush=True)


async def persist_region(region):
    """Write a /region change back so the dashboard reflects it too (two-way sync)."""
    if not (SUPABASE_URL and SUPABASE_ANON_KEY and WORKER_TOKEN and BOT_ORDER_ID and http):
        return
    url = f"{SUPABASE_URL}/functions/v1/dispatch-region"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    body = {"botId": BOT_ORDER_ID, "workerToken": WORKER_TOKEN, "region": region}
    try:
        async with http.post(url, headers=headers, json=body) as resp:
            await resp.text()
    except Exception as exc:
        print(f"persist_region failed (non-fatal): {exc}", flush=True)


def _key_fingerprint(name, val):
    raw = os.environ.get(name, "")
    stripped = raw.strip()
    print(
        f"env[{name}]: len={len(raw)} stripped_len={len(stripped)} "
        f"first6={stripped[:6]!r} last6={stripped[-6:]!r} "
        f"has_ws={'YES' if raw != stripped or ' ' in raw else 'no'} "
        f"startswith_eyJ={'yes' if stripped.startswith('eyJ') else 'NO'}",
        flush=True,
    )


async def fetch_dispatch_voice_channel(diag=False):
    """Read the dashboard-chosen voice channel using only the anon key.

    The voice channel id is not sensitive, so it goes through a dedicated
    tokenless RPC (runtime_get_dispatch_voice_channel) instead of the
    worker-token-gated secret path. This makes the dashboard picker drive the
    bot on every dispatch bot with no per-bot worker token to configure.
    """
    if not (SUPABASE_URL and SUPABASE_ANON_KEY and BOT_ORDER_ID and http):
        return None
    url = f"{SUPABASE_URL}/rest/v1/rpc/runtime_get_dispatch_voice_channel"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    body = {"_bot_id": BOT_ORDER_ID}
    try:
        async with http.post(url, headers=headers, json=body) as resp:
            raw = await resp.text()
            if diag:
                print(f"voice-channel read: HTTP {resp.status} body={raw[:120]!r}", flush=True)
            if resp.status != 200:
                return None
            try:
                val = json.loads(raw)
            except Exception:
                val = raw
            return val.strip() if isinstance(val, str) and val.strip() else None
    except Exception as exc:
        print(f"voice-channel read failed: {exc}", flush=True)
        return None


async def fetch_dispatch_presence():
    """Read the dashboard-chosen status, status message and About Me (all
    public profile fields) using only the anon key — same tokenless pattern as
    the voice channel. Returns a dict or None."""
    if not (SUPABASE_URL and SUPABASE_ANON_KEY and BOT_ORDER_ID and http):
        return None
    url = f"{SUPABASE_URL}/rest/v1/rpc/runtime_get_dispatch_presence"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with http.post(url, headers=headers, json={"_bot_id": BOT_ORDER_ID}) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data if isinstance(data, dict) else None
    except Exception as exc:
        print(f"presence read failed: {exc}", flush=True)
        return None


_STATUS_MAP = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
    "do_not_disturb": discord.Status.dnd,
    "invisible": discord.Status.invisible,
    "offline": discord.Status.invisible,
}
_ACTIVITY_MAP = {
    "playing": discord.ActivityType.playing,
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "competing": discord.ActivityType.competing,
    "streaming": discord.ActivityType.streaming,
}


async def apply_presence(presence, act_type, act_text):
    status = _STATUS_MAP.get(str(presence or "online").lower().replace(" ", "_"),
                             discord.Status.online)
    text = str(act_text or "").strip()
    activity = None
    if text:
        at = str(act_type or "playing").lower()
        if at == "custom":
            activity = discord.CustomActivity(name=text)
        else:
            activity = discord.Activity(type=_ACTIVITY_MAP.get(at, discord.ActivityType.playing),
                                        name=text)
    await client.change_presence(status=status, activity=activity)


async def apply_about_me(bio):
    """Set the bot's About Me = the application description via the current
    Discord endpoint (PATCH /applications/@me), authorised with the bot's own
    token. Discord genuinely supports this now — no manual portal step."""
    if not http:
        return
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    body = {"description": str(bio or "")[:400]}
    try:
        async with http.patch("https://discord.com/api/v10/applications/@me",
                              headers=headers, json=body) as resp:
            if resp.status in (200, 201):
                print("about me (application description) updated", flush=True)
            else:
                txt = await resp.text()
                print(f"about-me update failed: HTTP {resp.status} {txt[:140]}", flush=True)
    except Exception as exc:
        print(f"about-me update error: {exc}", flush=True)


async def identity_watch_loop():
    """Live-sync the dashboard's status / status message / About Me onto the
    bot. Applies each only when it actually changes, so we never spam the
    gateway or the /applications/@me endpoint."""
    global _last_presence, _last_bio
    await client.wait_until_ready()
    print("identity watcher: ON (syncs status & About Me from the dashboard)", flush=True)
    while not client.is_closed():
        try:
            data = await fetch_dispatch_presence()
            if data:
                pres = (data.get("presence"), data.get("activity_type"), data.get("activity_text"))
                if pres != _last_presence:
                    _last_presence = pres
                    await apply_presence(*pres)
                    print(f"status applied: {pres}", flush=True)
                bio = data.get("bio")
                if bio != _last_bio:
                    _last_bio = bio
                    await apply_about_me(bio)
        except Exception as exc:
            print(f"identity watcher error (continuing): {exc}", flush=True)
        await asyncio.sleep(15)


async def refresh_runtime_config():
    global ERLC_KEY, VOICE_CHANNEL_ID
    _key_fingerprint("WORKER_TOKEN", WORKER_TOKEN)
    key = await fetch_bot_secret("ERLC_SERVER_KEY", diag=True)
    if key:
        ERLC_KEY = key
    # Adopt the dashboard-chosen region (state/country) on startup + each refresh.
    await load_region_from_dashboard()
    vc = await fetch_dispatch_voice_channel(diag=True)
    print(f"config refresh: ERLC_secret={'read' if key else 'env/none'} "
          f"DISPATCH_VOICE_CHANNEL_ID={vc!r} -> VOICE_CHANNEL_ID={VOICE_CHANNEL_ID}", flush=True)
    if vc:
        try:
            VOICE_CHANNEL_ID = int(vc)
        except ValueError:
            print(f"could not parse voice channel id: {vc!r}", flush=True)


async def erlc_get(path):
    if not ERLC_KEY:
        return None
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


async def erlc_command(command):
    try:
        async with http.post(f"{ERLC_V2_BASE}/server/command",
                             headers={"Server-Key": ERLC_KEY},
                             json={"command": command}) as resp:
            if resp.status in (200, 201, 204):
                return True
            body = await resp.text()
            print(f"erlc command '{command[:40]}' -> {resp.status}: {body[:200]}", flush=True)
            return False
    except Exception as exc:
        print(f"erlc command failed: {exc}", flush=True)
        return False


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

    async def _log():
        if not TEXT_CHANNEL_ID:
            return
        channel = client.get_channel(TEXT_CHANNEL_ID)
        if channel is None:
            return
        try:
            embed = discord.Embed(title=f"📻 {title}", description=text, color=0x3B82F6)
            await channel.send(embed=embed)
        except Exception as exc:
            print(f"text log failed: {exc}", flush=True)

    # The text log and the voice are produced at the same time.
    path, _ = await asyncio.gather(synthesize(text), _log())
    if path:
        if tone and ALERT_TONES and tone_path:
            await play_queue.put(tone_path)
        await play_queue.put(path)
        print("audio queued for playback", flush=True)


def pcm_to_wav(pcm):
    """Left channel only: half the bytes to upload, nothing lost from a mono
    microphone, so the transcript comes back sooner."""
    try:
        samples = array("h")
        samples.frombytes(pcm[: len(pcm) - (len(pcm) % 4)])
        data, channels = samples[0::2].tobytes(), 1
    except Exception:
        data, channels = pcm, 2
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(48000)
        handle.writeframes(data)
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


# ============================================================================
# Region engine — all 50 US states + countries, each with a real radio-code
# reference the AI is given so it uses accurate codes instead of guessing.
# ============================================================================

NATO_PHONETIC = (
    "Alpha Bravo Charlie Delta Echo Foxtrot Golf Hotel India Juliet Kilo Lima "
    "Mike November Oscar Papa Quebec Romeo Sierra Tango Uniform Victor Whiskey "
    "X-ray Yankee Zulu"
)

# The APCO-derived 10-codes the large majority of US agencies actually use.
US_TEN_CODES = (
    "10-4 acknowledged; 10-6 busy; 10-7 out of service; 10-8 in service/available; "
    "10-9 say again; 10-19 return to station; 10-20 location; 10-23 on scene/stand by; "
    "10-27 license check; 10-28 registration check; 10-29 wants/warrants check; "
    "10-32 person with a gun; 10-50 traffic accident; 10-76 en route; 10-97 arrived; "
    "10-98 assignment complete; 10-99 officer needs emergency help; Code 4 no further "
    "assistance needed; Signal 100 hold the air for emergency traffic"
)

# Response/priority codes common across US agencies.
US_RESPONSE_CODES = (
    "Code 1 routine (no lights/siren); Code 2 urgent (no siren); "
    "Code 3 emergency (lights and siren)"
)

# Region-specific real additions layered ON TOP of the common US set.
STATE_EXTRAS = {
    "California": (
        "California agencies also use Penal Code call types on the air: 187 homicide, "
        "207 kidnapping, 211 robbery, 240 assault, 245 assault with a deadly weapon, "
        "459 burglary, 484 theft, 415 disturbance, 5150 mental-health hold, "
        "23152 DUI. CHP uses '11-' codes: 11-80 accident major injury, 11-99 officer "
        "needs help."
    ),
    "New York": (
        "New York (NYPD-style) uses its own 10-codes: 10-13 officer needs assistance, "
        "10-30 robbery in progress, 10-31 burglary in progress, 10-34 assault, "
        "10-52 dispute, 10-53 vehicle accident, 10-85 need backup at scene."
    ),
    "Florida": (
        "Many Florida agencies use Signal codes: Signal 4 accident, Signal 7 dead body, "
        "Signal 20 mentally ill, Signal 34 robbery, Signal 43 subject with a weapon."
    ),
}

# Country profiles for non-US regions (real conventions, no fake 10-codes).
COUNTRY_PROFILES = {
    "United Kingdom": (
        "UK police do NOT use 10-codes. Control (not 'dispatch') speaks mostly plain "
        "English with NATO phonetics. Use response grades: Grade 1 immediate/emergency, "
        "Grade 2 prompt, Grade 3 scheduled. Say 'received' not '10-4', 'show me on "
        "scene', 'making' (en route). Identity/IC codes (IC1-IC6) may describe people. "
        "Use 'RTC' for road traffic collision and 'PNC check' for records."
    ),
    "Canada": (
        "Canadian agencies largely use the same 10-codes as the US (10-4, 10-7, 10-8, "
        "10-20, etc.); RCMP also uses plain language. Use NATO phonetics."
    ),
    "Australia": (
        "Australian police use plain-language status calls and VKG-style procedure "
        "rather than US 10-codes: 'received', 'en route', 'on scene', 'code 1' urgent, "
        "'signal 1' understood. Use NATO phonetics."
    ),
    "Germany": (
        "German police use plain radio procedure with NATO phonetics (German variant "
        "possible). No US 10-codes; keep it terse and professional."
    ),
    "Mexico": (
        "Mexican agencies commonly use 'clave' codes and plain Spanish/English radio "
        "procedure; no US 10-codes. Keep transmissions short and professional."
    ),
}

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming",
]

COUNTRIES = [
    "the United States", "United Kingdom", "Canada", "Australia",
    "Germany", "Mexico",
]

# The full picker/autocomplete catalog: countries first, then all 50 states.
REGION_CATALOG = COUNTRIES + US_STATES


def canonical_region(name):
    """Match free-text input to a catalog entry (case/space-insensitive)."""
    n = " ".join((name or "").split()).strip()
    if not n:
        return "the United States"
    low = n.lower().lstrip("the ").strip()
    for entry in REGION_CATALOG:
        if entry.lower().lstrip("the ").strip() == low:
            return entry
    # Unknown but non-empty (e.g. a city) — keep it as typed; the AI still gets
    # a sensible default code reference below.
    return n


def _is_us_region(region):
    r = region.lower().lstrip("the ").strip()
    return r == "united states" or region in US_STATES


def code_reference_for(region):
    """A concise, accurate radio-code block to hand the AI for this region."""
    lines = [f"Phonetic alphabet (NATO): {NATO_PHONETIC}."]
    if region in COUNTRY_PROFILES:
        lines.append(COUNTRY_PROFILES[region])
    elif _is_us_region(region):
        lines.append(f"Radio codes: {US_TEN_CODES}.")
        lines.append(f"Response codes: {US_RESPONSE_CODES}.")
        if region in STATE_EXTRAS:
            lines.append(STATE_EXTRAS[region])
        else:
            lines.append(
                "Some agencies here have moved to plain language; mirror whatever "
                "codes the unit uses and stay consistent."
            )
    else:
        # Unknown region: give the common US set as a baseline but tell the AI to
        # adapt to that area's real conventions.
        lines.append(
            f"Use the real radio codes, signals, and procedure that police in "
            f"{region} actually use. If unsure, default to standard 10-codes "
            f"(10-4 acknowledged, 10-20 location, 10-97 on scene) and NATO phonetics."
        )
    return " ".join(lines)


def build_dispatch_system(region):
    return (
        f"You are Oversite Dispatch, a professional emergency dispatcher working in "
        f"{region}, handling police and sheriff radio traffic. Talk exactly the way a "
        f"real dispatcher in {region} talks: use the real radio codes, signals, "
        f"phonetic alphabet, and calm, clipped cadence that agencies there actually "
        f"use. Answer with exactly one short radio transmission.\n"
        f"Radio-code reference for {region} — use these, do not invent others: "
        f"{code_reference_for(region)}\n"
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
        "- A traffic stop or self-initiated stop is DIFFERENT from attaching to a call: "
        "when a unit calls one out and states their OWN location and/or a vehicle "
        "description, briefly acknowledge it back, for example 'copy, show you out with "
        "the black SUV on Highway 55, advise if you need backup'. NEVER ask a unit to "
        "advise a plate, location, or description they have already given. Only ask for "
        "a plate or location when the unit gave none at all.\n"
        "- Plates, names, and records checks are run against a REAL database by another "
        "part of dispatch, not by you. NEVER invent a return, a registered owner, a "
        "warrant, or a license status — a made-up return would contradict the real one. "
        "NEVER say 'stand by', 'give me a second', or that you will get back to them. If a "
        "unit asks for a plate, name, or records check and has not yet given the plate or "
        "the name, reply with exactly 'go ahead with that plate' or 'go ahead with that "
        "name' and nothing else.\n"
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
        f"Radio-code reference for {region} — use these, do not invent others: "
        f"{code_reference_for(region)}\n"
        "Rules:\n"
        "- One broadcast, two or three short sentences at most.\n"
        "- State the nature of the call and the location. Say the location only once, "
        "do not repeat it.\n"
        "- Direct the appropriate units to respond with the correct priority code.\n"
        "- If closest available unit(s) are provided, assign the nearest one as the "
        "primary unit by callsign, for example 'Unit 1-Sam-32, you are the closest unit, "
        "respond Code 3'. If a second unit is provided, you may also assign it as backup "
        "for serious calls, for example 'Unit 2-Adam-14, respond to assist'. Only use the "
        "callsigns provided; never invent one.\n"
        "- End by stating the time exactly as given in the record.\n"
        "- Do not invent any detail that is not in the record. Do not add a call-taker "
        "name, phone number, or facts you were not given.\n"
        "- No markdown, no emojis, no preamble, no sign-off.\n"
        "- Output only the words dispatch would speak over the air."
    )


# Normalize whatever came in from the env/dashboard to a catalog entry.
DISPATCH_REGION = canonical_region(DISPATCH_REGION)
DISPATCH_SYSTEM = build_dispatch_system(DISPATCH_REGION)
CALL_SYSTEM = build_call_system(DISPATCH_REGION)


def set_region(region):
    global DISPATCH_REGION, DISPATCH_SYSTEM, CALL_SYSTEM
    DISPATCH_REGION = canonical_region(region)
    DISPATCH_SYSTEM = build_dispatch_system(DISPATCH_REGION)
    CALL_SYSTEM = build_call_system(DISPATCH_REGION)


async def safe_respond(interaction, text):
    try:
        await interaction.response.send_message(text, ephemeral=True)
    except Exception as exc:
        print(f"interaction response failed: {exc}", flush=True)


async def region_autocomplete(interaction, current: str):
    cur = " ".join((current or "").split()).lower().lstrip("the ").strip()
    if cur:
        matches = [r for r in REGION_CATALOG if cur in r.lower()]
    else:
        # Empty box: show countries first, then the first states.
        matches = REGION_CATALOG
    return [discord.app_commands.Choice(name=r, value=r) for r in matches[:25]]


@command_tree.command(
    name="region",
    description="Set the real-world area dispatch talks like (state or country)",
    guild=DISPATCH_GUILD,
)
@discord.app_commands.describe(area="Pick a state or country — for example Texas, California, United Kingdom")
@discord.app_commands.autocomplete(area=region_autocomplete)
@discord.app_commands.default_permissions(manage_guild=True)
async def region_command(interaction, area: str):
    area = " ".join(area.split()).strip()
    if not area:
        await safe_respond(interaction, "Pick a state or country from the list.")
        return
    set_region(area)
    # Best-effort persist so the dashboard reflects it and it survives a restart.
    await persist_region(DISPATCH_REGION)
    print(f"region changed to {DISPATCH_REGION} by {interaction.user}", flush=True)
    await safe_respond(interaction,
        f"Dispatch is now running as **{DISPATCH_REGION}**. New calls and radio "
        f"replies will use that area's real codes and style.")


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
    remember_callsign(callsign)
    save_links()
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
    if isinstance(nearest, str):
        nearest_units = [nearest] if nearest else []
    else:
        nearest_units = [u for u in (nearest or []) if u]
    if not AI_ENABLED:
        return build_call_line(call, nearest_units)
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
    if len(nearest_units) == 1:
        record += f"\nClosest available unit: {nearest_units[0]}"
    elif len(nearest_units) > 1:
        record += f"\nClosest available units, nearest first: {', '.join(nearest_units)}"
    reply = await anthropic_call(CALL_SYSTEM, record, max_tokens=220)
    return reply or build_call_line(call, nearest_units)


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


# Strong signals that a unit already gave a location and/or a vehicle
# description in their transmission, so dispatch shouldn't ask for it again.
_STOP_LOCATION_RE = re.compile(
    r"\b(highway|hwy|freeway|interstate|route|boulevard|blvd|avenue|ave|"
    r"street|road|lane|parkway|pkwy|drive|court|exit|intersection|block|"
    r"postal|mile\s*marker|north\s*bound|south\s*bound|east\s*bound|west\s*bound)\b",
    re.I)
_STOP_VEHICLE_RE = re.compile(
    r"\b(black|white|red|blue|silver|gray|grey|green|yellow|orange|brown|tan|"
    r"gold|maroon|purple|suv|sedan|truck|pickup|van|coupe|hatchback|motorcycle|"
    r"jeep|convertible|plate|license)\b",
    re.I)


def has_stop_details(text):
    t = str(text or "")
    return bool(_STOP_LOCATION_RE.search(t) or _STOP_VEHICLE_RE.search(t))


async def dispatch_reply_body(text, callsign):
    key = normalize_intent(text, callsign)
    # A traffic stop where the unit already stated a location and/or vehicle:
    # don't fire the canned "advise plate and location" — let the AI reply
    # acknowledge what they said instead of re-asking for it.
    detailed_stop = bool(key) and "traffic stop" in key and has_stop_details(text)

    if not detailed_stop:
        fb = fallback_reply(key)
        if fb:
            if LOG_HEARD:
                print(f"using built-in reply for '{key}' (no api call)", flush=True)
            return fb
        hit = match_cached_intent(key)
        if hit and len(response_cache[hit]) >= AI_CACHE_VARIANTS:
            if LOG_HEARD:
                print(f"reusing saved reply for '{hit}' (no api call)", flush=True)
            return random.choice(response_cache[hit])
    else:
        hit = None

    body = await dispatch_ai_reply(text, callsign)
    if body:
        if body.strip().strip(".!").upper() == "IGNORE":
            return IGNORE
        store = response_cache.setdefault(hit or key, [])
        if body not in store:
            store.append(body)
        if LOG_HEARD:
            print(f"saved reply for '{hit or key}' ({len(store)} variant(s))", flush=True)
        return body
    # AI unavailable but the unit gave details — acknowledge without re-asking.
    if detailed_stop:
        return "copy, show you out on the traffic stop, advise if you need backup"
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


_NUM_ONES = {"zero": "0", "oh": "0", "o": "0", "one": "1", "two": "2", "three": "3",
             "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9"}
_NUM_TEEN = {"ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
             "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19"}
_NUM_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
             "seventy": 70, "eighty": 80, "ninety": 90}
_PHON = {"adam": "a", "boy": "b", "charlie": "c", "david": "d", "edward": "e", "frank": "f",
         "george": "g", "henry": "h", "ida": "i", "john": "j", "king": "k", "lincoln": "l",
         "mary": "m", "nora": "n", "ocean": "o", "paul": "p", "queen": "q", "robert": "r",
         "sam": "s", "tom": "t", "union": "u", "victor": "v", "william": "w", "xray": "x",
         "young": "y", "zebra": "z", "alpha": "a", "bravo": "b", "delta": "d", "echo": "e",
         "foxtrot": "f", "golf": "g", "hotel": "h", "india": "i", "juliet": "j", "kilo": "k",
         "lima": "l", "mike": "m", "november": "n", "oscar": "o", "papa": "p", "quebec": "q",
         "romeo": "r", "sierra": "s", "tango": "t", "uniform": "u", "whiskey": "w",
         "yankee": "y", "zulu": "z"}


def spoken_compact(text):
    tokens = [t for t in re.split(r"[\s-]+", text.lower()) if t]
    out = []
    i = 0
    while i < len(tokens):
        t = tokens[i].strip(",.")
        if t in _NUM_TENS:
            val = _NUM_TENS[t]
            if i + 1 < len(tokens):
                nxt = tokens[i + 1].strip(",.")
                if nxt in _NUM_ONES and nxt not in ("zero", "oh", "o"):
                    val += int(_NUM_ONES[nxt])
                    i += 1
            out.append(str(val))
        elif t in _NUM_TEEN:
            out.append(_NUM_TEEN[t])
        elif t in _NUM_ONES:
            out.append(_NUM_ONES[t])
        elif t in _PHON:
            out.append(_PHON[t])
        elif t.isalnum():
            out.append(t)
        i += 1
    return "".join(out)


def resolve_callsign(spoken, member=None):
    """Snap what was heard to a callsign dispatch knows: units on the map right
    now, every callsign it has ever seen or been told, and the speaker's own.
    "one S zero three two" heard as "one S zero thirty two" still lands on
    1S-032, and a unit that only mumbled its number is still recognised by
    the tag on its own nickname."""
    own = member_callsign(member)
    if not spoken:
        return own or spoken
    target = spoken_compact(spoken)
    if not target:
        return own or spoken
    active = {norm_callsign(v[0]): v[0] for v in officer_last_seen.values() if v and v[0]}
    known = dict(known_callsigns)
    known.update(active)
    if own:
        known.setdefault(norm_callsign(own), own)
    if target in known:
        return known[target]
    best, best_r = None, 0.0
    for nk, disp in known.items():
        r = difflib.SequenceMatcher(None, target, nk).ratio()
        if nk in active:
            r += 0.08  # a unit on the map right now is the likelier match
        if r > best_r:
            best_r, best = r, disp
    if own and best_r < 0.9 and difflib.SequenceMatcher(None, target, norm_callsign(own)).ratio() >= 0.45:
        return own
    if best is not None and best_r >= 0.6:
        if norm_callsign(best) != target:
            print(f"callsign: heard {spoken!r}, going with {best}", flush=True)
        return best
    return spoken


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


def wants_roster(text):
    low = _flat(text)
    triggers = ("roster", "how many units", "units on patrol", "units on duty",
                "on patrol", "current units", "how many on duty", "how many are on",
                "units in service", "whos on patrol", "who is on patrol")
    return any(t in low for t in triggers)


async def read_roster(callsign=""):
    data = await erlc_get("/server?Players=true")
    units = []
    if isinstance(data, dict) and isinstance(data.get("Players"), list):
        for p in data["Players"]:
            team = str(p.get("Team") or "").lower()
            if any(t in team for t in CALL_TEAMS):
                pname = str(p.get("Player") or "").split(":")[0]
                units.append(str(p.get("Callsign") or "").strip() or pname)
    ack = f"Unit {callsign}, " if callsign else ""
    if not units:
        return f"{ack}no units are currently on patrol."
    word = "unit" if len(units) == 1 else "units"
    return f"{ack}current roster, {len(units)} {word} on patrol. {', '.join(units[:12])}."


def wants_clear_stop(text):
    low = _flat(text)
    triggers = ("clear", "concluded", "conclude", "done", "finished", "complete",
                "wrapping up", "wrap up", "resuming patrol", "back in service",
                "in service", "available", "10-8", "ten eight")
    return any(t in low for t in triggers)


def wants_backup(text):
    low = _flat(text)
    if "backup" in low or "back up" in low:
        return True
    request = any(w in low for w in ("need", "request", "send", "start", "get me", "require", "want"))
    if "additional" in low and (request or "unit" in low or "officer" in low):
        return True
    return any(t in low for t in ("another unit", "another officer", "second unit", "more units"))


def wants_bolo_read(text):
    low = _flat(text)
    return any(t in low for t in ("any bolos", "active bolos", "current bolos",
                                  "read bolos", "read the bolos", "list bolos", "what bolos"))


def extract_bolo(text):
    low = text.lower()
    markers = ("be on the lookout for", "be on the lookout on", "on the lookout for",
               "put out a bolo for", "put out a bolo on", "put out a bolo",
               "bolo out for", "bolo out on", "bolo for", "bolo on",
               "b.o.l.o. for", "b.o.l.o. on", "lookout for", "look out for",
               "lookout on", "look out on", "bulletin for", "bulletin on")
    for marker in markers:
        idx = low.find(marker)
        if idx >= 0:
            desc = text[idx + len(marker):].strip(" ,.-")
            if desc:
                return autocorrect(desc)
    idx = low.find("bolo")
    if idx >= 0:
        desc = text[idx + 4:].strip(" ,.-")
        if len(desc) >= 3:
            return autocorrect(desc)
    return ""


def add_bolo(desc, callsign):
    bolos.append({"desc": desc, "callsign": callsign, "time": time.time()})
    cutoff = time.time() - BOLO_EXPIRE
    bolos[:] = [b for b in bolos if b["time"] >= cutoff][-8:]
    print(f"bolo logged: '{desc}' per {callsign or 'unknown'} (active: {len(bolos)})", flush=True)


def read_bolos(callsign=""):
    cutoff = time.time() - BOLO_EXPIRE
    active = [b for b in bolos if b["time"] >= cutoff]
    ack = f"Unit {callsign}, " if callsign else ""
    if not active:
        return f"{ack}no active B O L Os at this time."
    parts = [f"{ack}current B O L Os."]
    for i, b in enumerate(active[-6:], 1):
        parts.append(f"{i}. {b['desc']}.")
    return " ".join(parts)


def available_units(exclude=None):
    now = time.time()
    ex = norm_callsign(exclude) if exclude else None
    out = []
    for cs, v in status_board.items():
        if now - v.get("time", 0) >= 10800:
            continue
        st = str(v.get("status") or "").lower()
        if "10-8" in st or "available" in st or "in service" in st:
            if ex and norm_callsign(cs) == ex:
                continue
            out.append(cs)
    return out


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


def wants_call_cleared(text):
    low = _flat(text)
    if "in custody" in low:
        return True
    if "call" not in low:
        return False
    words = ("clear", "cancel", "conclud", "disregard", "complete", "done", "close", "void")
    return any(w in low for w in words)


def extract_call_number(text):
    match = re.search(r"call\s*(?:number\s*)?(\d{1,6})", text.lower())
    return int(match.group(1)) if match else None


def mark_call_cleared(number):
    if number is None:
        return False
    cleared_calls.add(number)
    open_calls.pop(number, None)
    return True


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


def name_match_keys(member):
    """Ordered normalized identifiers to try against in-game player names.

    People decorate their Discord name with tags — "(Don't Ping) 22HYPE22",
    "D 22HYPE22", "[PD] 22Hype22" — so a whole-string match misses. We also
    match each individual word (>=3 chars), longest first, so the distinctive
    username still resolves to the in-game player. Link data and whole-string
    matches are tried before word tokens to avoid a short common word (e.g.
    "ping") winning over the real name.
    """
    link = callsign_links.get(member.id) or {}
    raw = []
    if link.get("roblox"):
        raw.append(str(link["roblox"]))
    if link.get("callsign"):
        raw.append(str(link["callsign"]))
    for attr in ("name", "global_name", "display_name"):
        v = getattr(member, attr, None)
        if v:
            raw.append(str(v))

    out, seen = [], set()

    def add(s):
        nk = norm_callsign(s)
        if nk and nk not in seen:
            seen.add(nk)
            out.append(nk)

    tokens = []
    for r in raw:
        add(r)               # whole string
        add(clean_name(r))   # with (…) / […] tags stripped
        for tok in re.split(r"[^A-Za-z0-9]+", r):
            if len(tok) >= 3:
                tokens.append(tok)
    # Word tokens after the whole-string candidates, longest (most distinctive)
    # first.
    for tok in sorted(set(tokens), key=len, reverse=True):
        add(tok)
    return out


def save_links():
    try:
        with open(LINK_FILE, "w") as handle:
            json.dump({str(k): v for k, v in callsign_links.items()}, handle)
    except Exception as exc:
        print(f"could not save callsign links: {exc}", flush=True)


def load_links():
    try:
        if not os.path.exists(LINK_FILE):
            return
        with open(LINK_FILE) as handle:
            data = json.load(handle)
        for k, v in data.items():
            try:
                if isinstance(v, dict):
                    callsign_links[int(k)] = v
            except (TypeError, ValueError):
                continue
        print(f"loaded {len(callsign_links)} saved callsign link(s)", flush=True)
    except Exception as exc:
        print(f"could not load callsign links: {exc}", flush=True)



# ============================================================================
# Durable memory. Everything the units have told dispatch (statuses, BOLOs,
# links, learned callsigns, active stops, remembered plates) is written to the
# dashboard's store whenever it changes and once more right before a redeploy
# stops the process, then read back on boot. A redeploy no longer forgets.
# ============================================================================

known_callsigns = {}   # normalised -> as written; every callsign dispatch has seen or been told
voice_callsigns = {}   # Discord member id -> {"callsign", "at"}: who this voice is, learned from what they said
plate_memory = {}      # normalised plate -> {"vehicle", "owner", "callsign", "at"}
wanted_persons = {}    # normalised name -> {"name", "reason", "callsign", "at"}
citations = {}         # normalised name -> [{"kind", "reason", "callsign", "at"}]: tickets and warnings
last_subject = {}      # Discord member id -> {"name", "plate", "at"}: who they just ran
_subject_any = {}      # the last person anyone ran, so any unit can follow up on it
air_manual_until = 0.0  # a unit said the air unit is up; real-time pursuit callouts until then
manual_tracks = {}     # normalised player name -> {"name", "callsign", "since", "street", "last_call"}
_last_state_blob = None
_state_loaded = False


def remember_callsign(cs):
    cs = str(cs or "").strip()
    nk = norm_callsign(cs)
    if nk and any(ch.isdigit() for ch in nk) and 2 <= len(nk) <= 12:
        known_callsigns[nk] = cs


def member_callsign(member):
    """The callsign dispatch already knows for this Discord member: their /link,
    or the [TAG] the bot put on their nickname when they came on duty."""
    if member is None:
        return ""
    uid = getattr(member, "id", 0)
    link = callsign_links.get(uid) or {}
    if link.get("callsign"):
        return str(link["callsign"])
    m = re.match(r"^\[([^\]]{1,12})\]", str(getattr(member, "display_name", "") or ""))
    if m and any(ch.isdigit() for ch in m.group(1)):
        return m.group(1).strip()
    heard = voice_callsigns.get(uid) or {}
    if heard.get("callsign") and time.time() - float(heard.get("at") or 0) < 12 * 3600:
        return str(heard["callsign"])
    return ""


async def learn_voice_callsign(member, spoken, callsign):
    """A unit that gave its callsign in a transmission is that callsign from
    then on: the next time this voice keys up without one, or with a garbled
    one, dispatch still knows who it is. Tags the nickname when that is on."""
    if not (spoken and callsign) or member is None:
        return
    prev = (voice_callsigns.get(member.id) or {}).get("callsign")
    voice_callsigns[member.id] = {"callsign": callsign, "at": time.time()}
    remember_callsign(callsign)
    if prev != callsign:
        print(f"voice: {getattr(member, 'display_name', member.id)} is {callsign}", flush=True)
        if CALLSIGN_NICK and not member_callsign(member) == callsign:
            try:
                await set_duty_nick(member, callsign)
            except Exception as exc:
                print(f"voice: nick tag failed: {exc}", flush=True)


def _state_snapshot():
    stops = {}
    for uid, st in active_stops.items():
        d = {k: v for k, v in st.items()
             if k != "member" and isinstance(v, (str, int, float, bool, type(None), list, dict, tuple))}
        d["uid"] = int(uid)
        stops[str(uid)] = d
    return {
        "status_board": dict(status_board),
        "bolos": list(bolos),
        "callsign_links": {str(k): v for k, v in callsign_links.items()},
        "cleared_calls": sorted(int(x) for x in cleared_calls if str(x).lstrip("-").isdigit()),
        "seen_keys": [list(k) for k in seen_keys if isinstance(k, tuple)],
        "seen_kills": sorted(str(k) for k in seen_kills),
        "nick_original": {str(k): v for k, v in nick_original.items()},
        "known_callsigns": dict(known_callsigns),
        "voice_callsigns": {str(k): v for k, v in voice_callsigns.items()},
        "plate_memory": dict(sorted(plate_memory.items(), key=lambda kv: -float((kv[1] or {}).get("at") or 0))[:500]),
        "wanted_persons": dict(wanted_persons),
        "citations": {k: v[-5:] for k, v in citations.items()},
        "response_cache": {k: v for k, v in response_cache.items() if isinstance(v, list)},
        "stop_channel_original": {str(k): v for k, v in stop_channel_original.items()},
        "active_stops": stops,
        "manual_tracks": dict(manual_tracks),
        "air_manual_until": air_manual_until,
        "saved_at": time.time(),
    }


async def _state_call(state=None):
    if not (SUPABASE_URL and SUPABASE_ANON_KEY and WORKER_TOKEN and BOT_ORDER_ID and http):
        return None
    url = f"{SUPABASE_URL}/functions/v1/dispatch-state"
    headers = {"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
               "Content-Type": "application/json"}
    body = {"botId": BOT_ORDER_ID, "workerToken": WORKER_TOKEN}
    if state is not None:
        body["state"] = state
    try:
        async with http.post(url, headers=headers, json=body) as resp:
            raw = await resp.text()
            if resp.status != 200:
                print(f"state {'save' if state is not None else 'load'} HTTP {resp.status}: {raw[:160]}", flush=True)
                return None
            return json.loads(raw)
    except Exception as exc:
        print(f"state call failed: {exc}", flush=True)
        return None


async def save_state(force=False, reason=""):
    global _last_state_blob
    if not _state_loaded:
        return  # never replace what is saved with an empty boot state
    snap = _state_snapshot()
    blob = json.dumps(snap, sort_keys=True, default=str)
    if not force and blob == _last_state_blob:
        return
    res = await _state_call(snap)
    if isinstance(res, dict) and res.get("ok"):
        _last_state_blob = blob
        if reason:
            print(f"state saved ({reason})", flush=True)


async def load_state():
    global _state_loaded, _last_state_blob, air_manual_until
    res = await _state_call()
    if not isinstance(res, dict) or not res.get("ok"):
        print("state: could not read the saved memory yet, will retry", flush=True)
        return
    _state_loaded = True
    st = res.get("state") or {}
    if not isinstance(st, dict) or not st:
        print("state: nothing saved yet", flush=True)
        return
    try:
        status_board.update({k: v for k, v in (st.get("status_board") or {}).items() if isinstance(v, dict)})
        for b in st.get("bolos") or []:
            if b not in bolos:
                bolos.append(b)
        for k, v in (st.get("callsign_links") or {}).items():
            if str(k).isdigit() and isinstance(v, dict):
                callsign_links[int(k)] = v
        cleared_calls.update(int(x) for x in (st.get("cleared_calls") or []) if str(x).lstrip("-").isdigit())
        for k in st.get("seen_keys") or []:
            if isinstance(k, list) and len(k) == 2:
                seen_keys.add((k[0], k[1]))
        seen_kills.update(str(k) for k in (st.get("seen_kills") or []))
        for k, v in (st.get("nick_original") or {}).items():
            if str(k).isdigit():
                nick_original[int(k)] = v
        known_callsigns.update({k: v for k, v in (st.get("known_callsigns") or {}).items()
                                if isinstance(k, str) and isinstance(v, str)})
        for k, v in (st.get("voice_callsigns") or {}).items():
            if str(k).isdigit() and isinstance(v, dict):
                voice_callsigns[int(k)] = v
        plate_memory.update({k: v for k, v in (st.get("plate_memory") or {}).items() if isinstance(v, dict)})
        wanted_persons.update({k: v for k, v in (st.get("wanted_persons") or {}).items() if isinstance(v, dict)})
        citations.update({k: v for k, v in (st.get("citations") or {}).items() if isinstance(v, list)})
        response_cache.update({k: v for k, v in (st.get("response_cache") or {}).items() if isinstance(v, list)})
        for k, v in (st.get("stop_channel_original") or {}).items():
            if str(k).isdigit():
                stop_channel_original[int(k)] = v
        manual_tracks.update({k: v for k, v in (st.get("manual_tracks") or {}).items() if isinstance(v, dict)})
        air_manual_until = float(st.get("air_manual_until") or 0)
        guild = client.get_guild(GUILD_ID) if GUILD_ID else (client.guilds[0] if client.guilds else None)
        restored_stops = 0
        for uid_s, d in (st.get("active_stops") or {}).items():
            if not (str(uid_s).isdigit() and isinstance(d, dict)):
                continue
            member = guild.get_member(int(uid_s)) if guild else None
            if member is None:
                continue
            d = dict(d)
            d.pop("uid", None)
            d["member"] = member
            if "last" in d and isinstance(d["last"], list):
                d["last"] = tuple(d["last"])
            active_stops[int(uid_s)] = d
            restored_stops += 1
    except Exception as exc:
        print(f"state: restore hit an error, continuing with what loaded: {exc!r}", flush=True)
    _last_state_blob = json.dumps(_state_snapshot(), sort_keys=True, default=str)
    print(f"state restored: {len(status_board)} unit status(es), {len(bolos)} BOLO(s), "
          f"{len(callsign_links)} link(s), {len(known_callsigns)} known callsign(s), "
          f"{restored_stops} active stop(s), {len(plate_memory)} plate(s), "
          f"{len(wanted_persons)} wanted, {sum(len(v) for v in citations.values())} citation(s)", flush=True)


async def state_save_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.sleep(STATE_SAVE_SECONDS)
        if not _state_loaded:
            await load_state()
            continue
        await save_state()


async def _graceful_shutdown():
    """Railway sends SIGTERM before a redeploy: save first, then go."""
    print("shutdown: saving dispatch memory before the redeploy", flush=True)
    try:
        await asyncio.wait_for(save_state(force=True, reason="shutdown"), 8)
    except Exception as exc:
        print(f"shutdown save failed: {exc}", flush=True)
    try:
        await client.close()
    except Exception:
        pass


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


def extract_postal(player):
    loc = player.get("Location") if isinstance(player.get("Location"), dict) else {}
    return str(loc.get("PostalCode") or player.get("PostalCode") or "").strip()


async def suspect_vehicle_near(officer_pos):
    global _veh_debugged
    data = await erlc_get("/server?Players=true&Vehicles=true")
    if not isinstance(data, dict) or officer_pos is None:
        return "", ""
    players = data.get("Players") or []
    vehicles = data.get("Vehicles") or []
    if vehicles and not _veh_debugged:
        _veh_debugged = True
        print(f"vehicle sample: {vehicles[0]}", flush=True)
    nearest_name, best_d = None, None
    for p in players:
        team = str(p.get("Team") or "").lower()
        if any(t in team for t in CALL_TEAMS):
            continue
        pos = extract_player_pos(p)
        if pos is None:
            continue
        d = ((pos[0] - officer_pos[0]) ** 2 + (pos[1] - officer_pos[1]) ** 2) ** 0.5
        if best_d is None or d < best_d:
            best_d, nearest_name = d, str(p.get("Player") or "").split(":")[0]
    if not nearest_name or best_d is None or best_d > SUSPECT_RADIUS:
        return "", ""
    nk = norm_callsign(nearest_name)
    for v in vehicles:
        if norm_callsign(str(v.get("Owner") or "")) == nk:
            return describe_vehicle(v), str(v.get("Plate") or "").strip()
    return "", ""


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
                name = str(p.get("Player") or "").split(":")[0]
                remember_callsign(p.get("Callsign"))
                info = (extract_player_pos(p), extract_street(p), name, extract_postal(p))
                for ident in (name, p.get("Callsign")):
                    k = norm_callsign(ident)
                    if k:
                        out[k] = info
    elif data is not None:
        print(f"players API returned unexpected shape: {str(data)[:200]}", flush=True)
    if not out:
        # Nothing to match against — surface why: no key, API failure, wrong
        # data shape, or genuinely nobody in-game.
        print(f"player_positions EMPTY: ERLC_KEY={'set' if ERLC_KEY else 'MISSING'} "
              f"raw={str(data)[:220]!r}", flush=True)
    return out


def extract_call_pos(call):
    raw = call.get("Position")
    if isinstance(raw, dict):
        x = _num(raw, "X", "LocationX")
        z = _num(raw, "Z", "LocationZ")
        if x is not None and z is not None:
            return (x, z)
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            if len(raw) >= 3:
                return (float(raw[0]), float(raw[2]))
            return (float(raw[0]), float(raw[1]))
        except (TypeError, ValueError):
            pass
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
                remember_callsign(cs)
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


def pick_nearest_units(call, units, count=2):
    cpos = extract_call_pos(call)
    if cpos is None or not units:
        return []
    ranked = sorted(units, key=lambda u: (u[1][0] - cpos[0]) ** 2 + (u[1][1] - cpos[1]) ** 2)
    picked = []
    for cs, _pos in ranked:
        if cs and cs not in picked:
            picked.append(cs)
        if len(picked) >= count:
            break
    return picked


async def move_member(member, channel_id):
    who = getattr(member, "display_name", "?") if member is not None else "?"
    if not channel_id:
        print(f"move skipped: no dispatch voice channel set (VOICE_CHANNEL_ID=0) — "
              f"pick one on the dashboard; can't pull {who} back", flush=True)
        return False
    if member is None:
        return False
    if member.voice is None:
        print(f"move skipped: {who} isn't connected to a Discord voice channel — "
              f"Discord can only move someone who's already in voice, so there's "
              f"nothing to drag back", flush=True)
        return False
    if member.voice.channel is not None and member.voice.channel.id == channel_id:
        return True
    channel = member.guild.get_channel(channel_id)
    if channel is None:
        print(f"move skipped: dispatch voice channel {channel_id} not found in this "
              f"server — is the bot in the right guild and the channel still there?", flush=True)
        return False
    try:
        await member.move_to(channel)
        print(f"pulled {who} back to the dispatch voice channel", flush=True)
        return True
    except Exception as exc:
        print(f"could not move {who}: {exc} — does the bot have the "
              f"Move Members permission on the dispatch voice channel?", flush=True)
        return False


async def start_traffic_stop(member, spoken_callsign=""):
    who = getattr(member, "display_name", "?")
    if not TRAFFIC_STOP_RETURN:
        return
    link = callsign_links.get(member.id) or {}
    positions = await player_positions()
    candidates = name_match_keys(member)
    key = None
    spoken_key = norm_callsign(spoken_callsign)
    if spoken_key and spoken_key in positions:
        key = spoken_key
    if key is None:
        key = next((c for c in candidates if c in positions), None)
    radio_cs = spoken_callsign or link.get("callsign") or clean_name(who)
    if key is None:
        print(f"traffic stop: could not match {who} to an in-game player. "
              f"spoken='{spoken_callsign}' tried {candidates} available {sorted(positions)} "
              f"(ERLC_KEY={'set' if ERLC_KEY else 'MISSING'}, "
              f"players_returned={len(positions)})", flush=True)
        return
    entry = positions[key]
    pos = entry[0]
    postal = entry[3] if len(entry) > 3 else ""
    now = time.time()
    active_stops[member.id] = {"key": key, "member": member, "last": pos, "last_time": now,
                               "since": now, "callsign": radio_cs, "postal": postal}
    print(f"traffic stop started: {who} matched '{key}' at {pos}", flush=True)
    # If they're already sitting in a Traffic Stop-style VC, label it now.
    await maybe_label_stop_for_member(member, postal)


async def assign_backup(member, spoken_callsign):
    data = await erlc_get("/server?Players=true")
    players = data.get("Players") if isinstance(data, dict) else None
    officers = []
    if isinstance(players, list):
        for p in players:
            team = str(p.get("Team") or "").lower()
            if not any(t in team for t in CALL_TEAMS):
                continue
            pname = str(p.get("Player") or "").split(":")[0]
            cs = str(p.get("Callsign") or "").strip() or pname
            officers.append({
                "name": norm_callsign(pname),
                "cs": cs,
                "cs_norm": norm_callsign(cs),
                "pos": extract_player_pos(p),
                "street": extract_street(p),
                "postal": extract_postal(p),
            })

    if not officers:
        await announce("Be advised, no units are currently active. No backup is available.", title="Backup")
        return

    req = None
    sk = norm_callsign(spoken_callsign)
    if sk:
        req = next((o for o in officers if o["cs_norm"] == sk or o["name"] == sk), None)
    if req is None:
        idents = duty_idents(member)
        req = next((o for o in officers if o["name"] in idents), None)
    req_cs = spoken_callsign or (req["cs"] if req else clean_name(getattr(member, "display_name", "unit")))

    others = [o for o in officers if not req or o["cs_norm"] != req["cs_norm"]]
    if not others:
        await announce(f"Unit {req_cs}, be advised, no other units are available for backup at this time.", title="Backup")
        return

    where_bits = []
    if req and req.get("postal"):
        where_bits.append(f"postal {req['postal']}")
    if req and req.get("street"):
        where_bits.append(req["street"])
    loc = ", ".join(where_bits)

    if loc:
        await announce(f"All units, Unit {req_cs} is requesting backup to {loc}.", title="Backup", tone=True)
    else:
        await announce(f"All units, Unit {req_cs} is requesting backup.", title="Backup", tone=True)

    with_pos = [o for o in others if o.get("pos")]
    if req and req.get("pos") and with_pos:
        nearest = min(with_pos, key=lambda o: (o["pos"][0] - req["pos"][0]) ** 2 + (o["pos"][1] - req["pos"][1]) ** 2)
        await announce(
            f"Unit {nearest['cs']}, you are the closest unit to the backup request, respond Code 3.",
            title="Backup")
        print(f"backup: {nearest['cs']} assigned to {req_cs}", flush=True)
    else:
        await announce(f"Any available unit, respond to assist Unit {req_cs}, Code 3.", title="Backup")
        print(f"backup: general call for {req_cs}", flush=True)


async def clear_traffic_stop(member, callsign=""):
    active_stops.pop(member.id, None)
    prev = member.voice.channel if getattr(member, "voice", None) else None
    await move_member(member, VOICE_CHANNEL_ID)
    # Moving the officer out fires on_voice_state_update which restores the
    # label when the channel empties; restore here too in case they were the
    # last one and the move already left it empty.
    if prev is not None and prev.id in stop_channel_original and not channel_humans(prev):
        schedule_restore(prev)
    print(f"traffic stop cleared for {getattr(member, 'display_name', '?')}", flush=True)
    ack = f"Unit {callsign}, " if callsign else ""
    await announce(f"{ack}10-4, showing you clear of the traffic stop.", title="Clear")


# ── Traffic-stop voice-channel postal labels ────────────────────────────────
# Match channels that look like a traffic-stop VC: "Traffic Stop 1", "TS 2",
# "T/S", "Vehicle Stop", etc. Emoji and separators (・ | - _ .) are ignored.
_TS_NAME_RE = re.compile(r"\btraffic\b|\bvehicle stop\b|\bts\b|\bt s\b|\btstop\b")


def is_traffic_stop_channel(name):
    if not name:
        return False
    n = str(name).lower()
    n = re.sub(r"[・|_\-–—.:/]+", " ", n)         # separators (incl. /) -> spaces
    n = re.sub(r"[^\w ]+", " ", n)               # drop emoji/symbols
    n = re.sub(r"\s+", " ", n).strip()
    return bool(_TS_NAME_RE.search(n))


def channel_humans(channel):
    return [m for m in getattr(channel, "members", []) if not getattr(m, "bot", False)]


async def officer_postal(member):
    positions = await player_positions()
    for ident in duty_idents(member):
        entry = positions.get(ident)
        if entry and len(entry) > 3 and entry[3]:
            return entry[3]
    return ""


async def label_stop_channel(channel, postal):
    if channel is None or not postal or not TS_CHANNEL_LABELS:
        return
    # A follow-up stop in this channel: cancel any pending revert so we reuse the
    # existing label instead of spending a restore + a relabel (which would blow
    # the 2-renames-per-10-min budget).
    _cancel_pending_restore(channel.id)
    if channel.id in stop_channel_original:
        return  # already labelled — reuse it, don't stack a second postal
    if _rename_budget_left(channel.id) <= 0:
        wait = int(_seconds_until_budget(channel.id))
        print(f"stop channel label skipped: Discord's 2-renames-per-10-min limit for "
              f"'{channel.name}' is used up (back-to-back stops in the same VC); it can "
              f"label again in ~{wait}s", flush=True)
        return
    original = channel.name
    new_name = f"[{postal}] {original}"[:100]
    stop_channel_original[channel.id] = original
    try:
        await channel.edit(name=new_name, reason="Traffic stop — nearest postal")
        _record_rename(channel.id)
        print(f"stop channel labelled: '{original}' -> '{new_name}'", flush=True)
    except discord.Forbidden:
        stop_channel_original.pop(channel.id, None)
        print("cannot rename stop channel — bot is missing the Manage Channels permission",
              flush=True)
    except Exception as exc:
        stop_channel_original.pop(channel.id, None)
        print(f"stop channel rename failed: {exc}", flush=True)


async def restore_stop_channel(channel):
    if channel is None or channel.id not in stop_channel_original:
        return
    # If we'd exceed Discord's name-edit limit, don't call edit() — it would
    # block for minutes. Defer until the window frees up; the name still reverts,
    # just a little later.
    if _rename_budget_left(channel.id) <= 0:
        wait = _seconds_until_budget(channel.id)
        print(f"stop channel restore deferred ~{int(wait)}s: rename budget for "
              f"'{channel.name}' is used up", flush=True)
        schedule_restore(channel, delay=wait)
        return
    original = stop_channel_original.pop(channel.id, None)
    if original is None:
        return
    try:
        await channel.edit(name=original, reason="Traffic stop ended")
        _record_rename(channel.id)
        print(f"stop channel restored -> '{original}'", flush=True)
    except Exception as exc:
        stop_channel_original[channel.id] = original  # keep for a later retry
        print(f"stop channel restore failed: {exc}", flush=True)


async def maybe_label_stop_for_member(member, postal=""):
    if not TS_CHANNEL_LABELS:
        return
    vs = getattr(member, "voice", None)
    ch = vs.channel if vs else None
    if ch is None or not is_traffic_stop_channel(ch.name):
        return
    if not postal:
        postal = await officer_postal(member)
    if postal:
        await label_stop_channel(ch, postal)


def duty_idents(member):
    # Includes word-token candidates so tagged Discord names still match.
    return set(name_match_keys(member))


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
            cs = str(p.get("Callsign") or "").strip()
            if not cs:
                print(f"nick: matched {member.display_name} in game but no callsign is set on their character", flush=True)
            remember_callsign(cs)
            return cs or None
    ingame = [str(p.get("Player") or "").split(":")[0] for p in players]
    print(f"nick: {member.display_name} not found among in-game players {ingame} "
          f"(tried {sorted(wanted)}); if their Roblox name differs, run /link", flush=True)
    return None


async def set_duty_nick(member, cs):
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


async def apply_duty_nick(member):
    cs = await get_ingame_callsign(member)
    if not cs:
        print(f"nick: {member.display_name} joined voice but no in-game callsign found", flush=True)
        return
    await set_duty_nick(member, cs)


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
        if CALLSIGN_NICK:
            guild = client.get_guild(GUILD_ID)
            voice_members = []
            if guild is not None:
                for vc in guild.voice_channels:
                    for m in vc.members:
                        if not m.bot:
                            voice_members.append(m)
            if voice_members or nick_original:
                data = await erlc_get("/server?Players=true")
                players = data.get("Players") if isinstance(data, dict) else None
                if isinstance(players, list):
                    on_duty = {}
                    for p in players:
                        uname = norm_callsign(str(p.get("Player") or "").split(":")[0])
                        cs = str(p.get("Callsign") or "").strip()
                        if uname and cs:
                            on_duty[uname] = cs
                    duty_keys = set(on_duty)
                    for m in voice_members:
                        if m.id in nick_original:
                            continue
                        match = duty_idents(m) & duty_keys
                        if match:
                            await set_duty_nick(m, on_duty[next(iter(match))])
                    for uid in list(nick_original.keys()):
                        member = guild.get_member(uid) if guild is not None else None
                        if member is None and guild is not None:
                            try:
                                member = await guild.fetch_member(uid)
                            except Exception:
                                member = None
                        if member is None:
                            nick_original.pop(uid, None)
                            continue
                        if not (duty_idents(member) & duty_keys):
                            await revert_duty_nick(member)
        await asyncio.sleep(20)


def _kill_time(entry):
    ts = entry.get("Timestamp")
    try:
        ts = float(ts)
    except (TypeError, ValueError):
        return 0
    return ts / 1000 if ts > 1e12 else ts


async def announce_officers_down(downed):
    groups = {}
    for d in downed:
        groups.setdefault(d.get("postal") or "", []).append(d)
    for postal, group in groups.items():
        if len(group) >= 2:
            callsigns = [g["cs"] for g in group if g.get("cs")]
            units = ", ".join(f"Unit {c}" for c in callsigns) if callsigns else "multiple units"
            where = f" at postal {postal}" if postal else ""
            await announce(
                f"Multiple officers down{where}. {units}. Any available unit, respond Code 3.",
                title="Officers Down", tone=True)
            print(f"officers down (multiple){' @ ' + postal if postal else ''}: {callsigns}", flush=True)
            continue
        d = group[0]
        parts = [f"All units, officer down, Unit {d['cs']}."]
        where_bits = []
        if d.get("postal"):
            where_bits.append(f"nearest postal {d['postal']}")
        if d.get("street"):
            where_bits.append(d["street"])
        if where_bits:
            joined = ", ".join(where_bits)
            parts.append(joined[:1].upper() + joined[1:] + ".")
        if d.get("veh"):
            line = f"Last known at a traffic stop with a {d['veh']}"
            if d.get("plate"):
                line += f", license plate {d['plate']}"
            parts.append(line + ".")
        parts.append("Any available unit, respond Code 3.")
        await announce(" ".join(parts), title="Officer Down", tone=True)
        print(f"officer down: {d['cs']}", flush=True)


async def officer_down_loop():
    global _kill_debugged
    await client.wait_until_ready()
    if OFFICER_DOWN:
        print("officer-down watch active", flush=True)
    while not client.is_closed():
        if OFFICER_DOWN:
            data = await erlc_get("/server?Players=true&KillLogs=true")
            if isinstance(data, dict):
                kills = data.get("KillLogs")
                if isinstance(kills, list):
                    if kills and not _kill_debugged:
                        _kill_debugged = True
                        print(f"killlog sample: {kills[0]}", flush=True)
                    downed = []
                    for k in kills:
                        name = str(k.get("Killed") or "").split(":")[0]
                        keyid = norm_callsign(name)
                        ts = _kill_time(k)
                        seen_key = (keyid, ts)
                        if not keyid or ts < boot_time or seen_key in seen_kills:
                            continue
                        seen_kills.add(seen_key)
                        info = officer_last_seen.get(keyid)
                        if info:
                            cs, street, postal = info
                            veh, plate = "", ""
                            for suid in [u for u, s in active_stops.items() if s.get("key") == keyid]:
                                s = active_stops.pop(suid)
                                if s.get("vehicle"):
                                    veh, plate = s["vehicle"], s.get("plate", "")
                            downed.append({"cs": cs, "street": street, "postal": postal, "veh": veh, "plate": plate})
                    if downed:
                        await announce_officers_down(downed)
                players = data.get("Players")
                if isinstance(players, list):
                    officer_last_seen.clear()
                    for p in players:
                        cs = str(p.get("Callsign") or "").strip()
                        team = str(p.get("Team") or "").lower()
                        if cs and any(t in team for t in CALL_TEAMS):
                            uname = norm_callsign(str(p.get("Player") or "").split(":")[0])
                            if uname:
                                officer_last_seen[uname] = (cs, extract_street(p), extract_postal(p))
        await asyncio.sleep(OFFICER_DOWN_POLL)


async def end_stop_pursuit(uid, stop, street):
    stop["pursuit"] = True
    stop["slow_since"] = None
    stop["last_callout"] = time.time()
    try:
        players, _v = await snapshot_players_vehicles()
        stop["suspect"] = nearest_suspect(players, stop.get("last"))
        stop["track_street"] = ""
        if stop["suspect"]:
            add_wanted(stop["suspect"], "fleeing and eluding", stop.get("callsign"))
    except Exception as exc:
        print(f"could not identify the suspect: {exc}", flush=True)
    await move_member(stop["member"], VOICE_CHANNEL_ID)
    cs = stop["callsign"]
    where = f" near {street}" if street else ""
    await announce(
        f"All units, Unit {cs} is in pursuit, subject fleeing a traffic stop{where}. "
        f"Clear the air.", title="Pursuit", tone=True)
    avail = available_units(exclude=cs)
    if avail:
        names = ", ".join(f"Unit {u}" for u in avail[:4])
        await announce(
            f"{names}, you are 10-8, respond to assist Unit {cs} in the pursuit, Code 3.",
            title="Pursuit Assist")
    else:
        await announce(
            f"All available units, respond to assist Unit {cs} in the pursuit, Code 3.",
            title="Pursuit Assist")
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
                pos, street, pname = entry[0], entry[1], entry[2]
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
                if speed >= 500:
                    active_stops.pop(uid, None)
                    print(f"stop {stop['callsign']}: teleport/respawn, ending (no pursuit)", flush=True)
                    continue
                if stop.get("pursuit"):
                    if speed >= PURSUIT_END_SPEED:
                        stop["slow_since"] = None
                    else:
                        if stop.get("slow_since") is None:
                            stop["slow_since"] = now
                        elif now - stop["slow_since"] >= PURSUIT_END_SECONDS:
                            active_stops.pop(uid, None)
                            await announce(
                                f"All units, the pursuit involving Unit {stop['callsign']} "
                                f"is terminated. Resume normal traffic.", title="Pursuit Over")
                            print(f"pursuit ended for {stop['callsign']}", flush=True)
                    if uid in active_stops and now - stop.get("last_callout", 0) >= PURSUIT_CALLOUT_SECONDS:
                        stop["last_callout"] = now
                        where = f", {street}" if street else ""
                        await announce(
                            f"Unit {stop['callsign']} still in active pursuit{where}. "
                            f"Available units continue to assist, Code 3.", title="Pursuit")
                    continue
                if speed >= 3:
                    print(f"stop {stop['callsign']}: {speed:.0f} units/sec (flee at {FLEE_SPEED})", flush=True)
                if speed >= FLEE_SPEED:
                    await end_stop_pursuit(uid, stop, street)
                    continue
                if not stop.get("veh_done") and (now - stop["since"]) >= 8:
                    stop["veh_done"] = True
                    desc, plate = await suspect_vehicle_near(pos)
                    if desc:
                        stop["vehicle"] = desc
                        stop["plate"] = plate
                        if plate:
                            plate_memory[norm_callsign(plate)] = {"vehicle": desc, "owner": stop.get("suspect") or "",
                                                                  "callsign": stop.get("callsign"), "at": now}
                        print(f"stop {stop['callsign']}: suspect vehicle noted", flush=True)
                if STATUS_CHECKS:
                    await maybe_status_check(uid, stop, pos, street, pname, now)
        await asyncio.sleep(STOP_POLL_SECONDS)


async def maybe_status_check(uid, stop, pos, street, pname, now):
    stop.setdefault("check_at", stop["since"] + STATUS_CHECK_SECONDS)
    if not stop.get("checked"):
        if now < stop["check_at"]:
            return
        if not pname:
            stop["check_at"] = now + 60
            return
        msg = (f"Dispatch to {stop['callsign']}, status check. Drive a short distance "
               f"to advise Code 4, or clear when 10-4.")
        if not await erlc_command(f":pm {pname} {msg}"):
            stop["check_at"] = now + 60
            return
        stop["checked"] = True
        stop["check_pos"] = pos
        stop["check_deadline"] = now + STATUS_CHECK_GRACE
        print(f"status check sent to {stop['callsign']} ({pname})", flush=True)
        return
    cpos = stop.get("check_pos")
    moved = cpos is not None and (((pos[0] - cpos[0]) ** 2 + (pos[1] - cpos[1]) ** 2) ** 0.5) >= STATUS_CHECK_MOVE
    if moved:
        stop["checked"] = False
        stop["check_at"] = now + STATUS_CHECK_SECONDS
        stop.pop("check_pos", None)
        stop.pop("check_deadline", None)
        print(f"status check acknowledged by {stop['callsign']}", flush=True)
    elif now >= stop.get("check_deadline", now):
        active_stops.pop(uid, None)
        where = f", last known location {street}" if street else ""
        await announce(
            f"All units, be advised, Unit {stop['callsign']} is not responding to a "
            f"status check{where}. Any available unit, check their welfare.",
            title="Welfare Check", tone=True)
        print(f"status check FAILED for {stop['callsign']} — welfare broadcast", flush=True)


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


_held = {}            # member id -> {"text", "at", "task"}: a transmission that stopped mid-thought
_pending_lookup = {}  # member id -> {"kind", "callsign", "at"}: waiting for the plate or the name
_lookup_buf = {}      # member id -> letters collected so far while they spell one out
_speaking_now = set()

RESTART_PHRASES = ("correction", "disregard", "scratch that", "strike that", "start over",
                   "let me start over", "let me try that again", "try that again")
STANDBY_PHRASES = ("stand by", "standby", "wait one", "hold on", "one second", "one sec", "give me a second")
TRAIL_FILLERS = {"uh", "um", "uhh", "umm", "er", "ah", "the", "a", "an", "and", "to", "at", "on",
                 "in", "for", "with", "is", "of", "i", "im", "we", "be", "my", "our", "that", "this",
                 # Verbs and prepositions that cannot end a transmission — the unit
                 # was cut off mid-request, so wait instead of answering half of it.
                 # Words that CAN end one (me, you, over, out, up) are deliberately
                 # not here: "can you run a plate for me" is a complete request.
                 "run", "running", "check", "checking", "get", "need", "needs", "want",
                 "give", "gave", "tell", "see", "from", "into", "onto", "near"}


def starts_over(text):
    low = _flat(text).lstrip(" ,.")
    head = low[:60]
    return any(head.startswith(p) or f" {p}" in head for p in RESTART_PHRASES)


def strip_restart_prefix(text):
    low = _flat(text)
    cut = 0
    for p in RESTART_PHRASES:
        i = low.find(p)
        if i != -1 and i <= 40:
            cut = max(cut, i + len(p))
    rest = text[cut:].lstrip(" ,.-") if cut else text
    return rest


def looks_unfinished(text):
    """A transmission that stopped mid-thought: a trailing filler or dangling
    word, a stand-by, or a fragment with nothing in it but a callsign."""
    low = _flat(text).strip()
    if not low:
        return True
    words = re.findall(r"[a-z0-9']+", low)
    if not words:
        return True
    if any(p in low for p in STANDBY_PHRASES):
        return True
    if words[-1] in TRAIL_FILLERS:
        return True
    if text.rstrip().endswith(("-", "—", "…", ",")):
        return True
    if has_intent(text):
        return False
    strict = lambda w: any(ch.isdigit() for ch in w) or w in CALLSIGN_NUMS or w in CALLSIGN_PHON or (len(w) == 1 and w.isalpha())
    body = [w for w in words if w != "dispatch" and not strict(w)]
    return len(body) < 2


def has_intent(text):
    """Whether dispatch would know what to do with this on its own."""
    if detect_status(text) or wants_repeat(text) or wants_roster(text) or wants_status_board(text):
        return True
    if wants_calls_holding(text) or wants_backup(text) or wants_bolo_read(text) or wants_call_cleared(text):
        return True
    if extract_bolo(text) or lookup_request_kind(text) or wants_air_up(text) or wants_air_down(text):
        return True
    key = normalize_intent(text, "")
    if not key:
        return False
    if fallback_reply(key) is not None:
        return True
    # Four real words beyond the callsign: a unit that only keyed up with its
    # number is still waiting to say what it wants.
    words = [w for w in key.split() if len(w) > 1 and w not in CALLSIGN_NUMS and w not in CALLSIGN_PHON]
    return len(words) >= 4


def merge_fragments(first, second):
    """Join a held fragment with what followed it. A restart that repeats the
    beginning of the fragment replaces it; otherwise the two are one message."""
    a = _flat(first).split()
    b = _flat(second).split()
    if not a:
        return second
    head = a[:3]
    if len(b) >= len(head) and b[: len(head)] == head:
        return second
    if len(b) >= 2 and " ".join(b[:2]) in " ".join(a):
        return second
    return first.rstrip(" ,.-") + " " + second


# ============================================================================
# Plate and name checks, the air unit, and live suspect tracking.
# ============================================================================

_PLATE_REQ = re.compile(r"\b(run|running|check|checking|got|have|need|got a|10-28|ten twenty eight)\b.*\bplate\b|\bplate for you\b|\brun a plate\b", re.I)
_NAME_REQ = re.compile(r"\b(run|running|check|checking|got|have|need)\b.*\b(name|username|user name|person|subject|10-29)\b|\bname for you\b|\brun a name\b|\bname check\b", re.I)
_NATO = {"a": "Alpha", "b": "Bravo", "c": "Charlie", "d": "Delta", "e": "Echo", "f": "Foxtrot", "g": "Golf",
         "h": "Hotel", "i": "India", "j": "Juliet", "k": "Kilo", "l": "Lima", "m": "Mike", "n": "November",
         "o": "Oscar", "p": "Papa", "q": "Quebec", "r": "Romeo", "s": "Sierra", "t": "Tango", "u": "Uniform",
         "v": "Victor", "w": "Whiskey", "x": "X-ray", "y": "Yankee", "z": "Zulu"}
_PLATE_SKIP = {"plate", "plates", "the", "is", "as", "in", "its", "it's", "number", "reads", "read", "of", "a",
               "license", "licence", "tag", "dispatch", "for", "you", "go", "ahead", "copy", "ready", "that", "this"}
_NAME_SKIP = {"name", "names", "username", "user", "users", "the", "is", "as", "in", "its", "it's", "of", "a",
              "dispatch", "for", "you", "go", "ahead", "copy", "ready", "that", "this", "subject", "person",
              "roblox", "player", "spelled", "spelt", "spell", "goes", "by", "on", "im", "i'm", "checking",
              "check", "suspect", "individual", "male", "female", "party", "occupant", "guy", "dude", "kid",
              "lady", "gentleman", "driver", "owner", "him", "her", "hers", "them", "they", "their", "his",
              "any", "anything", "anybody", "anyone", "want", "wants", "warrant", "warrants", "wanted",
              "record", "records", "priors", "criminal", "history", "run", "running", "over", "pulled",
              "stopped", "stop", "vehicle", "car", "plate", "plates", "tag", "tags", "and", "or", "with",
              "to", "me", "my", "got", "get", "have", "has", "there", "here", "back", "comes", "come",
              "ticket", "tickets", "citation", "citations", "warning", "warnings", "verbal", "written",
              "cited", "ticketed", "issuing", "issued", "issue", "giving", "gave", "writing", "wrote",
              "cutting", "serving", "served", "speeding"}


_RECORDS_REQ = re.compile(
    r"\b(records? check|record check|wants and warrants|wants or warrants|warrant check|"
    r"criminal history|check .{0,12}?for (?:wants|warrants|priors)|priors|"
    r"10-?29|ten twenty ?nine|10-?27|ten twenty ?seven|"
    r"run (?:him|her|them|this (?:guy|subject|person|driver)|a (?:name|person|subject|record)))\b", re.I)
# The AI used to answer a records check with "stand by" and then nothing ever
# came back. Any reply that promises a lookup is turned into a real one.
_PROMISE = re.compile(
    r"\b(stand ?by|give me a (?:second|sec|moment|minute)|one moment|hold on|"
    r"let me (?:run|check|look|pull)|i'?ll (?:run|check|get back|have)|checking now|"
    r"working on (?:that|it)|pulling (?:that|it) up|looking (?:that|it) up|"
    r"go ahead with (?:that|the|your))\b", re.I)


def lookup_request_kind(text):
    """'run a plate' / 'have a name for you' / 'records check' -> which check."""
    low = _flat(text)
    if _PLATE_REQ.search(low):
        return "plate"
    if _NAME_REQ.search(low):
        return "name"
    if _RECORDS_REQ.search(low):
        return "plate" if "plate" in low else "name"
    return ""


def parse_plate(text):
    """'alpha bravo one two three' / 'A B C 1 2 3' / 'ABC123' -> 'ABC123'."""
    low = _flat(text).replace("x-ray", "xray").replace("x ray", "xray")
    low = re.sub(r"\bas in \w+", " ", low)
    tokens = [t for t in re.split(r"[\s,.\-]+", low) if t]
    out = []
    for t in tokens:
        if len(t) == 1 and t.isalnum():
            out.append(t)  # a spelled letter or digit, even "a" and "i"
            continue
        if t in _PLATE_SKIP or t in REQUEST_WORDS:
            continue
        if t in _PHON:
            out.append(_PHON[t])
        elif t in _NUM_ONES:
            out.append(_NUM_ONES[t])
        elif t in _NUM_TEEN:
            out.append(_NUM_TEEN[t])
        elif t in _NUM_TENS:
            out.append(str(_NUM_TENS[t]))
        elif t.isalnum() and any(ch.isdigit() for ch in t) and len(t) <= 8:
            out.append(t)
        elif t.isalpha() and len(t) <= 3 and t.upper() == t.upper() and len(out) > 0:
            out.append(t)
    plate = "".join(out).upper()
    return plate[:10]


def spell_plate(plate):
    parts = []
    for ch in str(plate or ""):
        if ch.isalpha():
            parts.append(_NATO.get(ch.lower(), ch))
        elif ch.isdigit():
            parts.append(ch)
    return " ".join(parts)


def parse_name(text):
    low = _flat(text)
    m = re.search(r"\b(name is|username is|name of|goes by|it is|its|it's)\b\s+(.+)$", low)
    if m:
        low = m.group(2)
    tokens = [t for t in re.split(r"[\s,.]+", low) if t]
    keep = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in _NAME_SKIP or t in REQUEST_WORDS or t == "dispatch":
            i += 1
            continue
        # Spoken numbers become digits ("twenty two" -> 22) so 22hype22 survives.
        if t in _NUM_TENS:
            val = _NUM_TENS[t]
            if i + 1 < len(tokens) and tokens[i + 1] in _NUM_ONES and tokens[i + 1] not in ("zero", "oh", "o"):
                val += int(_NUM_ONES[tokens[i + 1]])
                i += 1
            keep.append(str(val))
        elif t in _NUM_TEEN:
            keep.append(_NUM_TEEN[t])
        elif t in _NUM_ONES and t != "o":
            keep.append(_NUM_ONES[t])
        elif t.isalnum():
            keep.append(t)
        i += 1
    if not keep:
        return ""
    # Spelled letters, or a word with numbers around it, are one username.
    if all(len(t) == 1 for t in keep) or (len(keep) <= 4 and any(t.isdigit() for t in keep)):
        return "".join(keep)[:24]
    keep.sort(key=len, reverse=True)
    return keep[0][:24]


async def snapshot_players_vehicles():
    """One API call for everyone in the game and every vehicle out."""
    data = await erlc_get("/server?Players=true&Vehicles=true")
    players = data.get("Players") if isinstance(data, dict) else None
    vehicles = data.get("Vehicles") if isinstance(data, dict) else None
    players = players if isinstance(players, list) else []
    vehicles = vehicles if isinstance(vehicles, list) else []
    remember_vehicles(vehicles)
    return players, vehicles


def describe_vehicle(v):
    """'Super Red Redline Fire Engine' the way an MDT return reads: colour,
    livery when there is one, then the model."""
    color = str(v.get("ColorName") or "").strip()
    texture = str(v.get("Texture") or "").strip()
    name = str(v.get("Name") or "").strip()
    if texture and texture.lower() in name.lower():
        texture = ""
    return " ".join(x for x in (color, texture, name) if x)


def vehicle_for(vehicles, owner_name):
    nk = norm_callsign(owner_name)
    for v in vehicles:
        if norm_callsign(str(v.get("Owner") or "")) == nk:
            return describe_vehicle(v), str(v.get("Plate") or "").strip()
    return "", ""


async def roblox_profile(name):
    """Public Roblox profile for a username: display name, id, account age."""
    try:
        async with http.post("https://users.roblox.com/v1/usernames/users",
                             json={"usernames": [name], "excludeBannedUsers": False}) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
        hit = ((data or {}).get("data") or [None])[0]
        if not hit:
            return None
        async with http.get(f"https://users.roblox.com/v1/users/{hit['id']}") as resp:
            if resp.status != 200:
                return {"name": hit.get("name"), "display": hit.get("displayName"), "id": hit.get("id")}
            user = await resp.json()
        created = str(user.get("created") or "")
        age = ""
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            days = (datetime.now(timezone.utc) - dt).days
            if days >= 365:
                age = f"{days // 365} year{'s' if days // 365 != 1 else ''}"
            elif days >= 30:
                age = f"{days // 30} month{'s' if days // 30 != 1 else ''}"
            else:
                age = f"{days} day{'s' if days != 1 else ''}"
        except Exception:
            pass
        return {"name": user.get("name") or hit.get("name"), "display": user.get("displayName") or hit.get("displayName"),
                "id": user.get("id") or hit.get("id"), "age": age, "banned": bool(user.get("isBanned"))}
    except Exception as exc:
        print(f"roblox lookup failed: {exc}", flush=True)
        return None


WANTED_EXPIRE = int(os.environ.get("WANTED_EXPIRE", "21600"))  # 6 hours

_WANTED_ADD = re.compile(
    r"(?:be advised,?\s*)?(?:that\s+)?(?:subject\s+|suspect\s+|player\s+|user\s+|driver\s+)?"
    r"([a-z0-9_]{3,24})\s+(?:is|has|shows|comes back)\s+(?:back\s+)?"
    r"(?:as\s+)?(?:10-?99|ten ninety ?nine|wanted|a wanted|flagged|"
    r"(?:got |with )?an? (?:active )?(?:felony |arrest )?warrant)", re.I)
_WANTED_CLEAR = re.compile(
    r"\b(?:clear|cancel|remove|drop|void)\b.{0,24}?\b(?:wanted|warrant|flag)\b.{0,12}?"
    r"(?:on|for)\s+([a-z0-9_]{3,24})|([a-z0-9_]{3,24})\s+is\s+(?:now\s+)?in custody", re.I)
_WANTED_REASON = re.compile(r"\bwanted\s+(?:for|on)\s+(.+?)(?:\.|$)", re.I)


def wanted_entry(name):
    """The live wanted record for a name, or None. Records age out."""
    rec = wanted_persons.get(norm_callsign(name))
    if not rec:
        return None
    if time.time() - float(rec.get("at") or 0) > WANTED_EXPIRE:
        wanted_persons.pop(norm_callsign(name), None)
        return None
    return rec


def add_wanted(name, reason, callsign=""):
    name = str(name or "").strip()
    if not name:
        return
    wanted_persons[norm_callsign(name)] = {"name": name, "reason": (reason or "").strip(),
                                           "callsign": callsign, "at": time.time()}
    print(f"wanted: {name} for {reason or 'unspecified'} per {callsign or 'unknown'}", flush=True)


def clear_wanted(name):
    return wanted_persons.pop(norm_callsign(name), None) is not None


CITE_EXPIRE = int(os.environ.get("CITE_EXPIRE", "604800"))  # a week

_CITE_ADD = re.compile(
    r"\b(?:issu(?:e|ed|ing)|wrote|writing|write|gave|giving|give|cut|cutting|serv(?:ed|ing))\b"
    r"[^.]{0,30}?\b(citation|ticket|written warning|verbal warning|warning)\b", re.I)
_CITE_QUESTION = re.compile(r"\b(any|was|were|did|does|do|has|have|is|are|got)\b[^.]{0,30}?"
                            r"\b(citation|ticket|warning|cited|ticketed)\b", re.I)
_Q_CITE = re.compile(r"\b(citation|citations|ticket|tickets|warning|warnings|cited|ticketed)\b", re.I)


def human_ago(seconds):
    seconds = max(0, int(seconds))
    if seconds < 90:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"about {minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"about {hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


def add_citation(name, kind, reason, callsign=""):
    name = str(name or "").strip()
    if not name:
        return
    rec = {"kind": kind, "reason": (reason or "").strip(), "callsign": callsign, "at": time.time()}
    citations.setdefault(norm_callsign(name), []).append(rec)
    citations[norm_callsign(name)] = citations[norm_callsign(name)][-5:]
    print(f"citation: {name} {kind} for {reason or 'unspecified'} per {callsign or 'unknown'}", flush=True)


def citation_list(name):
    """Live tickets and warnings on file for a name, newest first."""
    key = norm_callsign(name)
    recs = [r for r in (citations.get(key) or []) if time.time() - float(r.get("at") or 0) <= CITE_EXPIRE]
    if recs:
        citations[key] = recs
    else:
        citations.pop(key, None)
    return sorted(recs, key=lambda r: -float(r.get("at") or 0))


def citation_phrase(name, subject=""):
    """'be advised, X was issued a ticket for speeding by Unit 1S-032 about ten
    minutes ago' — what dispatch adds after a wants and warrants check."""
    recs = citation_list(name)
    if not recs:
        return ""
    who = subject or name
    out = []
    for i, r in enumerate(recs[:2]):
        kind = r.get("kind") or "citation"
        seg = f"{who} was issued a {kind}" if i == 0 else f"and another {kind}"
        if r.get("reason"):
            seg += f" for {r['reason']}"
        if r.get("callsign"):
            seg += f" by Unit {r['callsign']}"
        seg += f" {human_ago(time.time() - float(r.get('at') or 0))}"
        out.append(seg)
    return "be advised, " + ", ".join(out)


def wanted_phrase(name):
    """'wanted for armed robbery, per Unit 1S-032' — the line that leads a return."""
    rec = wanted_entry(name)
    if not rec:
        return ""
    reason = rec.get("reason") or "an outstanding warrant"
    who = f", per Unit {rec['callsign']}" if rec.get("callsign") else ""
    return f"wanted for {reason}{who}"


def remember_vehicles(vehicles):
    """Every plate seen on the map is filed with its owner, so a plate check
    still returns the driver after they log off."""
    now = time.time()
    for v in vehicles or []:
        plate = str(v.get("Plate") or "").strip()
        if not plate:
            continue
        plate_memory[norm_callsign(plate)] = {"plate": plate, "vehicle": describe_vehicle(v),
                                              "owner": str(v.get("Owner") or "").strip(), "at": now}


def plate_for_owner(vehicles, owner_name):
    """The plate on the vehicle this player is driving, live or last known."""
    _desc, plate = vehicle_for(vehicles, owner_name)
    if plate:
        return plate
    nk = norm_callsign(owner_name)
    best, best_at = "", 0.0
    for rec in plate_memory.values():
        if norm_callsign(rec.get("owner") or "") == nk and float(rec.get("at") or 0) > best_at:
            best, best_at = rec.get("plate") or "", float(rec.get("at") or 0)
    return best


def bolo_matches(needle):
    nk = norm_callsign(needle)
    if not nk:
        return []
    out = []
    for b in bolos:
        desc = b.get("desc") if isinstance(b, dict) else str(b)
        if nk in norm_callsign(desc):
            out.append(desc)
    return out


SUBJECT_WINDOW = float(os.environ.get("SUBJECT_WINDOW", "420"))  # 7 minutes

# Words that carry a question rather than name somebody, so what is left over
# tells us whether a unit named a new subject or is still on the last one.
_FOLLOWUP_SKIP = set("""any anymore anything about advise are as ask back be been before but by came come comes
copy could did do does dont driver else for from get got guy had has have he her hers herself him himself his
how i if in is it its just know last like me my no not now of on one or our out over person priors owner
records record run running same say see she show shows so subject that the their them then these they
things this those to too under up us want wanted wants warrant warrants was we were what whats when where
which who whose will with would yes you your 10-27 10-28 10-29 1027 1028 1029 dispatch check checking
criminal history plate plates tag tags vehicle car driving location 20 twenty
user users username name names suspect individual male female party occupant dude kid lady gentleman
anybody anyone pulled stopped stop my mine guy girl
ticket tickets citation citations warning warnings cited ticketed issued issue""".split())
_Q_WANTS = re.compile(r"\b(wants?|warrants?|wanted|10-?29|ten twenty ?nine|priors|criminal history|record)\b", re.I)
_Q_VEHICLE = re.compile(r"\b(driving|drive|drives|vehicle|car|plate|tag|10-?28|ten twenty ?eight)\b", re.I)
_Q_WHERE = re.compile(r"\b(where|location|last seen|what.{0,8}20\b|his 20|her 20|their 20)\b", re.I)
# "I have a plate for you" / "run a name" — a fresh check, not a follow-up.
_OFFER_LOOKUP = re.compile(r"\b(?:i(?:'ve)? (?:have|got)|have a|got a|run a|running a|need a|do a|get a)\b"
                           r"[^.]{0,16}\b(plate|tag|name|username|record)\b", re.I)
_PRONOUN = re.compile(r"\b(he|him|his|she|her|hers|they|them|their|that (?:subject|guy|person|driver|one|name|plate)|"
                      r"this (?:subject|guy|person|driver)|the (?:subject|driver|owner|same)|same (?:subject|guy|person|one))\b", re.I)


def names_someone_new(text):
    """A token left after the question words is a new subject; nothing left
    means the unit is still talking about the one dispatch just ran."""
    for tok in re.split(r"[^A-Za-z0-9_]+", _flat(text)):
        if not tok or tok in _FOLLOWUP_SKIP or tok in REQUEST_WORDS:
            continue
        if is_callsign_token(tok) or len(tok) < 3:
            continue
        return True
    return False


def remember_subject(member, name, plate=""):
    if not name:
        return
    rec = {"name": name, "plate": plate or "", "at": time.time()}
    if member is not None:
        last_subject[member.id] = rec
    _subject_any.clear()
    _subject_any.update(rec)


def recent_subject(member):
    """Who this unit just ran, or failing that whoever was last run on the air."""
    now = time.time()
    rec = last_subject.get(getattr(member, "id", 0))
    if rec and now - float(rec.get("at") or 0) <= SUBJECT_WINDOW:
        return rec
    if _subject_any and now - float(_subject_any.get("at") or 0) <= SUBJECT_WINDOW:
        return dict(_subject_any)
    return None


def find_player_in(players, name):
    best, best_r = None, 0.0
    for p in players:
        pname = str(p.get("Player") or "").split(":")[0]
        r = difflib.SequenceMatcher(None, str(name).lower(), pname.lower()).ratio()
        if r > best_r:
            best_r, best = r, p
    return best if best_r >= 0.72 else None


def person_lines(real, ingame, vehicles, lead="", known_plate=""):
    """What dispatch knows about a person: wanted first, then where they are,
    what they are driving and its plate. A vehicle already named in the return
    (the one the plate was run on) is not described twice."""
    out = []
    subject = lead or real
    want = wanted_phrase(real)
    if want:
        out.append(f"be advised, {subject} is {want}")
    if ingame is not None:
        team = str(ingame.get("Team") or "").strip()
        icall = str(ingame.get("Callsign") or "").strip()
        seg = f"{subject} is in the server" if lead else "shows in the server"
        if team:
            seg += f" on {team}"
        if icall:
            seg += f" as unit {icall}"
        out.append(seg)
        desc, plate = vehicle_for(vehicles, real)
        same = known_plate and plate and norm_callsign(plate) == norm_callsign(known_plate)
        if desc and not same:
            veh = f"driving a {desc}"
            if plate:
                veh += f", plate {spell_plate(plate)}"
            out.append(veh)
        elif desc and same:
            out.append("driving that vehicle now")
        elif not desc:
            known = plate_for_owner(vehicles, real)
            if known and norm_callsign(known) != norm_callsign(known_plate or ""):
                out.append(f"last known plate {spell_plate(known)}")
        street = extract_street(ingame)
        postal = extract_postal(ingame)
        if street:
            out.append(f"last seen on {street}, postal {postal}" if postal else f"last seen on {street}")
    else:
        out.append(f"{subject} is not currently in the server" if lead else "not currently in the server")
        known = plate_for_owner(vehicles, real)
        if known and norm_callsign(known) != norm_callsign(known_plate or ""):
            out.append(f"last known plate {spell_plate(known)}")
    flags = bolo_matches(real)
    if flags:
        out.append(f"matches an active BOLO: {flags[0]}")
    cite = citation_phrase(real, lead or real)
    if cite:
        out.append(cite)
    return out


async def answer_followup(member, text, callsign):
    """'Any wants or warrants?' right after a check means that same subject.
    True when dispatch answered it."""
    subj = recent_subject(member)
    if not subj or names_someone_new(text):
        return False
    # A unit calling out their own status or stop is not asking about the last
    # subject, even when they say a word like "vehicle".
    if detect_status(text) or wants_backup(text) or wants_call_cleared(text) or extract_bolo(text):
        return False
    # "Issuing him a ticket" states something; it is logged, not answered.
    if _CITE_ADD.search(text) and not _CITE_QUESTION.search(text):
        return False
    low = _flat(text)
    # It has to read as a question about somebody.
    if not (_PRONOUN.search(low) or re.search(
            r"\b(any|anything|what|whats|where|is|are|does|do|did|got|has|have|show|10-?29|10-?28)\b", low)):
        return False
    wants = bool(_Q_WANTS.search(low))
    cites = bool(_Q_CITE.search(low))
    vehicle = bool(_Q_VEHICLE.search(low))
    where = bool(_Q_WHERE.search(low))
    if not (wants or cites or vehicle or where):
        return False
    real = subj["name"]
    ack = f"Unit {callsign}, " if callsign else ""
    players, vehicles = await snapshot_players_vehicles()
    ingame = find_player_in(players, real)
    remember_subject(member, real, subj.get("plate"))
    if wants or cites:
        rec = wanted_entry(real)
        if cites and not wants:
            recs = citation_list(real)
            if recs:
                line = f"{ack}{citation_phrase(real, real)}."
            else:
                line = f"{ack}{real} has no citations or warnings on file."
            await announce(line, title="Citations")
            print(f"follow-up by {callsign or getattr(member, 'display_name', '?')} on {real}: citations", flush=True)
            return True
        if rec:
            reason = rec.get("reason") or "an outstanding warrant"
            who = f", per Unit {rec['callsign']}" if rec.get("callsign") else ""
            line = f"{ack}{real} is wanted for {reason}{who}, use caution."
        else:
            line = f"{ack}{real} shows clear, no current wants or warrants."
        flags = bolo_matches(real)
        if flags:
            line += f" Be advised, matches an active BOLO: {flags[0]}."
        cite = citation_phrase(real, real)
        if cite:
            line += f" {cite[0].upper()}{cite[1:]}."
        await announce(line, title="Wants and Warrants", tone=bool(rec))
    elif vehicle:
        desc, plate = vehicle_for(vehicles, real)
        if desc:
            line = f"{ack}{real} is driving a {desc}"
            if plate:
                line += f", plate {spell_plate(plate)}"
            line += "."
        else:
            known = plate_for_owner(vehicles, real)
            line = (f"{ack}no vehicle out for {real} right now, last known plate {spell_plate(known)}."
                    if known else f"{ack}no vehicle on file for {real}.")
        await announce(line, title="Vehicle")
    else:
        if ingame is None:
            line = f"{ack}{real} is not currently in the server."
        else:
            street = extract_street(ingame)
            postal = extract_postal(ingame)
            if street and postal:
                line = f"{ack}{real} is on {street}, postal {postal}."
            elif street:
                line = f"{ack}{real} is on {street}."
            else:
                line = f"{ack}{real} is in the server, no location showing."
        await announce(line, title="Location")
    print(f"follow-up by {callsign or getattr(member, 'display_name', '?')} on {real}: "
          f"{'wants' if wants else 'vehicle' if vehicle else 'location'}", flush=True)
    return True


async def run_lookup(member, pend, text):
    cs = pend.get("callsign") or member_callsign(member)
    ack = f"Unit {cs}, " if cs else ""
    kind = pend.get("kind")
    players, vehicles = await snapshot_players_vehicles()

    def find_player(name):
        return find_player_in(players, name)

    if kind == "plate":
        plate = parse_plate(text)
        if len(plate) < 2:
            _pending_lookup[member.id] = {**pend, "at": time.time()}
            await announce(f"{ack}dispatch did not catch that plate, say again.", title="Plate Check")
            return
        spelled = spell_plate(plate)
        pk = norm_callsign(plate)
        hit = None
        for v in vehicles:
            if norm_callsign(str(v.get("Plate") or "")) == pk:
                hit = {"vehicle": describe_vehicle(v), "owner": str(v.get("Owner") or "").strip(), "live": True}
                break
        if hit is None and pk in plate_memory:
            m = plate_memory[pk]
            hit = {"vehicle": m.get("vehicle") or "", "owner": m.get("owner") or "", "live": False}
        if not hit:
            line = f"{ack}plate {spelled} shows no record on file."
            flags = bolo_matches(plate)
            if flags:
                line += f" Be advised, that plate matches an active BOLO: {flags[0]}."
            await announce(line, title="Plate Check")
            print(f"plate check by {cs or member.display_name}: {plate} -> no record", flush=True)
            return
        owner = hit["owner"]
        parts = [f"{ack}plate {spelled} returns to a {hit['vehicle'] or 'vehicle'}"]
        if owner:
            parts.append(f"registered to {owner}")
            parts.extend(person_lines(owner, find_player(owner), vehicles, lead="the registered owner", known_plate=plate))
            remember_subject(member, owner, plate)
        else:
            parts.append("no registered owner on file")
        flags = bolo_matches(plate)
        if flags:
            parts.append(f"that plate matches an active BOLO: {flags[0]}")
        await announce(", ".join(parts) + ".", title="Plate Check")
        print(f"plate check by {cs or member.display_name}: {plate} -> {owner or 'unknown owner'}"
              f"{' WANTED' if wanted_entry(owner) else ''}", flush=True)
        return

    name = parse_name(text)
    if len(name) < 3:
        _pending_lookup[member.id] = {**pend, "at": time.time()}
        await announce(f"{ack}dispatch did not catch that name, say again.", title="Name Check")
        return
    ingame = find_player(name)
    real = str(ingame.get("Player") or "").split(":")[0] if ingame is not None else name
    parts = [f"{ack}name {real} returns"]
    parts.extend(person_lines(real, ingame, vehicles))
    remember_subject(member, real, plate_for_owner(vehicles, real))
    profile = await roblox_profile(real)
    if profile:
        if profile.get("age"):
            parts.append(f"Roblox account is {profile['age']} old")
        if profile.get("banned"):
            parts.append("the account is banned on Roblox")
    else:
        parts.append("no Roblox account by that exact name")
    await announce(", ".join(parts) + ".", title="Name Check")
    print(f"name check by {cs or member.display_name}: {name} -> {real}"
          f"{' WANTED' if wanted_entry(real) else ''} ({'in game' if ingame is not None else 'not in game'})", flush=True)


def wants_air_up(text):
    low = _flat(text)
    return any(p in low for p in ("air unit up", "air unit is up", "air is up", "air one up", "air one is up",
                                  "helicopter is up", "helicopter up", "airborne", "in the air", "air support up",
                                  "air support is up", "bird is up", "bird up"))


def wants_air_down(text):
    low = _flat(text)
    return any(p in low for p in ("air unit down", "air unit is down", "air is down", "helicopter is down",
                                  "helicopter down", "landing", "air unit landing", "bird is down", "air support down"))


def heli_out(players, vehicles):
    """A police unit is in a helicopter right now."""
    police = {norm_callsign(str(p.get("Player") or "").split(":")[0])
              for p in players if any(t in str(p.get("Team") or "").lower() for t in CALL_TEAMS)}
    for v in vehicles:
        name = str(v.get("Name") or "").lower()
        if ("heli" in name or "chopper" in name or "airbus" in name) and norm_callsign(str(v.get("Owner") or "")) in police:
            return True
    return False


def air_unit_active(players, vehicles):
    return time.time() < air_manual_until or heli_out(players, vehicles)


def nearest_suspect(players, officer_pos):
    """The closest non-police player to the officer: the subject of the stop."""
    if officer_pos is None:
        return ""
    best, best_d = "", None
    for p in players:
        team = str(p.get("Team") or "").lower()
        if any(t in team for t in CALL_TEAMS):
            continue
        pos = extract_player_pos(p)
        if pos is None:
            continue
        d = ((pos[0] - officer_pos[0]) ** 2 + (pos[1] - officer_pos[1]) ** 2) ** 0.5
        if best_d is None or d < best_d:
            best_d, best = d, str(p.get("Player") or "").split(":")[0]
    return best if best and best_d is not None and best_d <= SUSPECT_RADIUS * 2 else ""


_TRACK_REQ = re.compile(r"\b(track|tracking|start tracking|keep eyes on|eyes on|follow)\b\s+(?:the\s+)?(?:suspect\s+|subject\s+|player\s+|user\s+)?([a-z0-9_]{3,24})", re.I)


def wants_track(text):
    m = _TRACK_REQ.search(_flat(text))
    return m.group(2) if m else ""


def wants_track_stop(text):
    low = _flat(text)
    return any(p in low for p in ("stop tracking", "lost the suspect", "lost visual", "terminate tracking", "cancel tracking"))


async def pursuit_track_loop():
    """Turn by turn. While a pursuit is running and the air unit is up, or a
    unit asked dispatch to track someone, the suspect's road is checked every
    couple of seconds and every change of road is put out the moment it happens."""
    await client.wait_until_ready()
    print("live suspect tracking: ready (air unit up, or 'dispatch, track NAME')", flush=True)
    while not client.is_closed():
        pursuits = [(uid, st) for uid, st in active_stops.items() if st.get("pursuit")]
        if not pursuits and not manual_tracks:
            await asyncio.sleep(TRACK_POLL_SECONDS)
            continue
        players, vehicles = await snapshot_players_vehicles()
        now = time.time()
        by_name = {norm_callsign(str(p.get("Player") or "").split(":")[0]): p for p in players}
        air = air_unit_active(players, vehicles)
        targets = []
        for uid, st in pursuits:
            if not st.get("suspect"):
                st["suspect"] = nearest_suspect(players, st.get("last"))
                if st["suspect"]:
                    print(f"pursuit {st.get('callsign')}: suspect identified as {st['suspect']}", flush=True)
            if st.get("suspect") and air:
                targets.append((st, st["suspect"], f" fleeing from Unit {st.get('callsign')}"))
        for key, tr in list(manual_tracks.items()):
            if now - float(tr.get("since") or now) > 1800:
                manual_tracks.pop(key, None)
                continue
            targets.append((tr, tr.get("name") or key, ""))
        for holder, name, who in targets:
            p = by_name.get(norm_callsign(name))
            if p is None:
                continue
            street = extract_street(p)
            postal = extract_postal(p)
            if not street or street == holder.get("track_street"):
                continue
            if now - float(holder.get("track_call") or 0) < 2.0:
                continue
            holder["track_street"] = street
            holder["track_call"] = now
            where = f"{street}, postal {postal}" if postal else street
            await announce(f"Suspect{who} now on {where}.", title="Suspect Location")
        await asyncio.sleep(TRACK_POLL_SECONDS)


async def handle_special(member, text, callsign):
    """Requests that sit outside the normal reply flow. True when handled."""
    global air_manual_until
    now = time.time()
    ack = f"Unit {callsign}, " if callsign else ""
    # "Issuing him a ticket for speeding" — logged against whoever is on the
    # air, so a later wants and warrants check reports it.
    cm = _CITE_ADD.search(text)
    if cm and not _CITE_QUESTION.search(text):
        kind = "warning" if "warning" in cm.group(1).lower() else "citation"
        reason_m = re.search(r"\bfor\s+(.+?)(?:\.|$)", text, re.I)
        reason = reason_m.group(1).strip() if reason_m else ""
        # The reason clause is dropped before looking for who it was issued to,
        # so "for no headlights" cannot be mistaken for a name.
        body = re.sub(r"\bfor\s+.+$", "", text, flags=re.I)
        cands = [t for t in re.split(r"[^A-Za-z0-9_]+", body)
                 if len(t) >= 3 and t.lower() not in _NAME_SKIP and not is_callsign_token(t)
                 and t.lower() not in ("dispatch", "issuing", "issued", "giving", "writing", "cutting", "serving")]
        target, best_r = "", 0.0
        if cands:
            players, _v = await snapshot_players_vehicles()
            for c in cands:
                for pl in players:
                    pname = str(pl.get("Player") or "").split(":")[0]
                    r = difflib.SequenceMatcher(None, c.lower(), pname.lower()).ratio()
                    if r > best_r:
                        best_r, target = r, pname
        if best_r < 0.6:
            subj = recent_subject(member)
            target = subj["name"] if subj else ""
        if target:
            add_citation(target, kind, reason, callsign)
            remember_subject(member, target)
            why = f" for {reason}" if reason else ""
            await announce(f"{ack}copy, showing a {kind} issued to {target}{why}.", title="Citation")
        else:
            await announce(f"{ack}copy, who was that {kind} issued to?", title="Citation")
        return True

    # "Any wants or warrants on that user?" is about the subject just run, so
    # it is answered before anything treats it as a brand new check. A unit
    # plainly offering a fresh plate or name skips straight to the lookup.
    if not _OFFER_LOOKUP.search(_flat(text)):
        if _PRONOUN.search(text) or not names_someone_new(text):
            if await answer_followup(member, text, callsign):
                return True
    kind = lookup_request_kind(text)
    if kind == "plate":
        plate = parse_plate(re.sub(r".*\bplate\b", "", _flat(text)))
        if len(plate) >= 3:
            await run_lookup(member, {"kind": "plate", "callsign": callsign, "at": now}, text)
            return True
        _pending_lookup[member.id] = {"kind": "plate", "callsign": callsign, "at": now}
        await announce(f"{ack}go ahead with that plate.", title="Plate Check")
        return True
    if kind == "name":
        name = parse_name(re.sub(r".*\b(name|username|user name|subject|person)\b", "", _flat(text)))
        if len(name) >= 3 and name not in _NAME_SKIP:
            await run_lookup(member, {"kind": "name", "callsign": callsign, "at": now}, text)
            return True
        _pending_lookup[member.id] = {"kind": "name", "callsign": callsign, "at": now}
        await announce(f"{ack}go ahead with that name.", title="Name Check")
        return True
    # "Run ByteRider99 for warrants" — a records question that names somebody
    # in the same breath, so there is nothing to ask for.
    if _Q_WANTS.search(_flat(text)) and names_someone_new(text) and not _WANTED_ADD.search(text):
        cand = parse_name(text)
        if len(cand) >= 3 and cand not in _NAME_SKIP:
            await run_lookup(member, {"kind": "name", "callsign": callsign, "at": now}, text)
            return True
    m = _WANTED_CLEAR.search(text)
    if m:
        target = (m.group(1) or m.group(2) or "").strip()
        players, _v = await snapshot_players_vehicles()
        best, best_r = target, 0.0
        for p in players:
            pname = str(p.get("Player") or "").split(":")[0]
            r = difflib.SequenceMatcher(None, target.lower(), pname.lower()).ratio()
            if r > best_r:
                best_r, best = r, pname
        real = best if best_r >= 0.6 else target
        if clear_wanted(real):
            await announce(f"{ack}copy, the wanted on {real} is cleared.", title="Wanted Cleared")
            return True
        return False
    m = _WANTED_ADD.search(text)
    if m and not detect_status(text):
        target = m.group(1).strip()
        if target.lower() not in ("dispatch", "unit", "subject", "suspect", "driver") and not is_callsign_token(target):
            reason_m = _WANTED_REASON.search(text)
            reason = reason_m.group(1).strip() if reason_m else ""
            players, _v = await snapshot_players_vehicles()
            best, best_r = target, 0.0
            for p in players:
                pname = str(p.get("Player") or "").split(":")[0]
                r = difflib.SequenceMatcher(None, target.lower(), pname.lower()).ratio()
                if r > best_r:
                    best_r, best = r, pname
            real = best if best_r >= 0.6 else target
            add_wanted(real, reason, callsign)
            why = f" for {reason}" if reason else ""
            await announce(f"{ack}copy, {real} is flagged wanted{why}. All units be advised.",
                           title="Wanted", tone=True)
            return True
    if wants_air_down(text):
        air_manual_until = 0.0
        await announce(f"{ack}copy, air unit is down.", title="Air Unit")
        return True
    if wants_air_up(text):
        air_manual_until = now + 3600
        await announce(f"{ack}copy, air unit is up. Dispatch will put out the suspect's location turn by turn.", title="Air Unit")
        return True
    if wants_track_stop(text):
        if manual_tracks:
            manual_tracks.clear()
            await announce(f"{ack}copy, tracking terminated.", title="Tracking")
            return True
        return False
    target = wants_track(text)
    if target and not detect_status(text):
        players, _v = await snapshot_players_vehicles()
        best, best_r = "", 0.0
        for p in players:
            pname = str(p.get("Player") or "").split(":")[0]
            r = difflib.SequenceMatcher(None, target.lower(), pname.lower()).ratio()
            if r > best_r:
                best_r, best = r, pname
        if best and best_r >= 0.6:
            manual_tracks[norm_callsign(best)] = {"name": best, "callsign": callsign, "since": now, "track_street": "", "track_call": 0}
            await announce(f"{ack}copy, dispatch is tracking {best} and will call every turn.", title="Tracking")
        else:
            await announce(f"{ack}dispatch does not see {target} in the server.", title="Tracking")
        return True
    return False


def spelling_fragment(text):
    """Mostly single letters, phonetic words or digits — the unit is spelling
    something out and has not finished."""
    toks = [t for t in re.split(r"[^a-z0-9]+", _flat(text)) if t]
    if not toks:
        return False
    spelled = sum(1 for t in toks
                  if len(t) == 1 or t in _PHON or t in _NUM_ONES or t in _NUM_TEEN or t in _NUM_TENS)
    return spelled >= max(1, int(len(toks) * 0.6))


async def run_buffered_lookup(member):
    uid = getattr(member, "id", 0)
    buf = _lookup_buf.pop(uid, None)
    if not buf:
        return
    task = buf.get("task")
    if task is not None and task is not asyncio.current_task():
        task.cancel()
    pend = _pending_lookup.pop(uid, None) or {"kind": buf["kind"], "callsign": buf.get("callsign"),
                                              "at": time.time()}
    await run_lookup(member, pend, " ".join(buf["parts"]))


async def collect_lookup(member, pend, text):
    """A plate or a name given a few letters at a time. Each transmission is
    added to what came before, and dispatch only answers once the unit has
    stopped talking — never over the top of them mid-spell."""
    uid = member.id
    if pend.get("kind") == "ask":
        # "A plate for me" / "the name is X" / a plate-shaped string — work out
        # which was meant from what they actually said.
        low = _flat(text)
        if re.search(r"\b(plate|tag|registration)\b", low):
            kind = "plate"
        elif re.search(r"\b(name|username|person|subject|records?)\b", low):
            kind = "name"
        else:
            guess = parse_plate(text)
            kind = "plate" if len(guess) >= 5 and any(c.isdigit() for c in guess) else "name"
        pend = {**pend, "kind": kind, "at": time.time()}
        _pending_lookup[uid] = pend
        bare = re.sub(r"\b(a|the|that|this|my|for|me|you|is|it|please)\b", " ", low)
        bare = re.sub(r"\b(plate|tag|registration|name|username|person|subject|records?)\b", " ", bare).strip()
        if not bare:
            ack = f"Unit {pend.get('callsign')}, " if pend.get("callsign") else ""
            await announce(f"{ack}go ahead with that {kind}.",
                           title="Plate Check" if kind == "plate" else "Name Check")
            return
    buf = _lookup_buf.get(uid)
    if buf is None or buf.get("kind") != pend.get("kind"):
        buf = {"kind": pend.get("kind"), "callsign": pend.get("callsign"), "parts": [], "task": None}
        _lookup_buf[uid] = buf
    if buf.get("task"):
        buf["task"].cancel()
        buf["task"] = None
    buf["parts"].append(text)
    joined = " ".join(buf["parts"])
    _pending_lookup[uid] = {**pend, "at": time.time()}

    if buf["kind"] == "plate":
        got = parse_plate(joined)
        # A full ER:LC plate is six or seven characters. Anything shorter, or a
        # fragment that is still being spelled, waits for the rest.
        done = len(got) >= 7 or (len(got) >= 6 and not spelling_fragment(text))
    else:
        got = parse_name(joined)
        done = len(got) >= 3 and not spelling_fragment(text)
    if done:
        await run_buffered_lookup(member)
        return

    async def _later():
        waited = 0.0
        while True:
            await asyncio.sleep(LOOKUP_HOLD)
            waited += LOOKUP_HOLD
            if uid not in _speaking_now or waited >= 20:
                break
        await run_buffered_lookup(member)

    buf["task"] = asyncio.ensure_future(_later())
    print(f"collecting {buf['kind']} from {getattr(member, 'display_name', uid)}: {joined!r} -> {got!r}", flush=True)


async def handle_utterance(member, pcm):
    uid = getattr(member, "id", 0)
    now = time.time()
    # Dispatch just asked this unit for a plate or a name, so it is listening
    # for a short answer. A plate read straight back — "LEB011" — is well under
    # the normal minimum and used to be thrown away before it was even
    # transcribed, which is why it only worked when the unit said "dispatch"
    # again and spoke for longer.
    awaiting = uid in _pending_lookup or uid in _lookup_buf
    if len(pcm) < (MIN_UTTER_BYTES // 5 if awaiting else MIN_UTTER_BYTES):
        return
    if audioop is not None and not awaiting:
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
    if LOG_HEARD:
        print(f"heard {who}{' (awaiting)' if awaiting else ''}: {text}", flush=True)

    # A lookup in progress: this transmission is the plate or the name.
    pend = _pending_lookup.get(uid)
    if pend and now - pend["at"] <= LOOKUP_WINDOW and not lookup_request_kind(text):
        await collect_lookup(member, pend, text)
        return

    # Something held from a moment ago: a restart replaces it, a continuation joins it.
    held = _held.pop(uid, None)
    if held:
        task = held.get("task")
        if task:
            task.cancel()
        if starts_over(text):
            text = strip_restart_prefix(text)
            if not text.strip():
                return
        elif now - held["at"] <= HOLD_SECONDS + 2.5:
            text = merge_fragments(held["text"], text)
        elif not is_for_dispatch(text):
            text = held["text"] if is_for_dispatch(held["text"]) else text
    if not is_for_dispatch(text):
        return

    if looks_unfinished(text):
        # The unit stopped mid-thought. Say nothing; wait for them to start over
        # or pick up where they were. If they never do, the fragment is used
        # only when dispatch can act on it, otherwise it is dropped quietly.
        async def _later():
            waited = 0.0
            while True:
                await asyncio.sleep(HOLD_SECONDS)
                waited += HOLD_SECONDS
                if uid not in _speaking_now or waited >= 15:
                    break
            h = _held.pop(uid, None)
            if h and has_intent(h["text"]):
                await process_transmission(member, h["text"])
            elif h:
                print(f"dropped an unfinished transmission from {who}: {h['text']!r}", flush=True)
        _held[uid] = {"text": text, "at": now, "task": asyncio.ensure_future(_later())}
        print(f"holding for {who}: {text!r}", flush=True)
        return

    await process_transmission(member, text)


async def process_transmission(member, text):
    spoken = extract_callsign(text)
    callsign = resolve_callsign(spoken, member)
    await learn_voice_callsign(member, spoken, callsign)
    if await handle_special(member, text, callsign):
        return
    if wants_repeat(text):
        if last_call is not None:
            ack = f"Unit {callsign}, copy. " if callsign else "Copy. "
            await announce(ack + build_call_line(last_call), title="Repeat")
        else:
            ack = f"Unit {callsign}, " if callsign else ""
            await announce(f"{ack}dispatch has no active calls to repeat at this time.", title="Repeat")
        return
    if wants_roster(text):
        await announce(await read_roster(callsign), title="Roster")
        return
    if wants_status_board(text):
        await announce(read_status_board(callsign), title="Unit Status")
        return
    if wants_calls_holding(text):
        await announce(read_calls_holding(callsign), title="Calls Holding")
        return
    if wants_backup(text):
        await assign_backup(member, callsign)
        return
    if wants_bolo_read(text):
        await announce(read_bolos(callsign), title="BOLO")
        return
    bolo_desc = extract_bolo(text)
    if bolo_desc:
        add_bolo(bolo_desc, callsign)
        who = f", per Unit {callsign}" if callsign else ""
        await announce(f"All units, be on the lookout for {bolo_desc}{who}.", title="BOLO")
        return
    if wants_call_cleared(text):
        ack = f"Unit {callsign}, " if callsign else ""
        low = _flat(text)
        if "all call" in low or "all calls" in low or "clear all" in low:
            had = list(open_calls.keys())
            for n in had:
                mark_call_cleared(n)
            msg = "10-4, all calls are concluded, all units disregard." if had else "no calls are holding to clear."
            await announce(f"{ack}{msg}", title="Calls Concluded")
            return
        number = extract_call_number(text)
        if number is None and last_call is not None:
            number = last_call.get("CallNumber")
        if number is not None:
            mark_call_cleared(number)
            await announce(f"{ack}10-4, call number {number} is concluded. All units, disregard.", title="Call Concluded")
        else:
            await announce(f"{ack}there are no active calls to clear.", title="Call Concluded")
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
        # Dispatch never promises to look something up and then goes quiet: a
        # reply like "stand by" becomes the real check, asking for the plate
        # or the name and handling whatever comes back next.
        if _PROMISE.search(body):
            low = _flat(text)
            if re.search(r"\b(plate|tag|registration|10-?28)\b", low):
                kind = "plate"
            elif re.search(r"\b(name|username|person|subject|records?|warrants?|wants|10-?29)\b", low):
                kind = "name"
            else:
                kind = "ask"  # they never said which — ask, do not guess
            _pending_lookup[member.id] = {"kind": kind, "callsign": callsign, "at": time.time()}
            ack = f"Unit {callsign}, " if callsign else ""
            if kind == "ask":
                await announce(f"{ack}is that a plate or a name?", title="Check")
            else:
                await announce(f"{ack}go ahead with that {kind}.",
                               title="Plate Check" if kind == "plate" else "Name Check")
            return
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
        def on_voice_member_speaking_start(self, member):
            _speaking_now.add(member.id)

        @voice_recv.AudioSink.listener()
        def on_voice_member_speaking_stop(self, member):
            _speaking_now.discard(member.id)
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
    current_numbers = {c.get("CallNumber") for c in calls if c.get("CallNumber") is not None}
    cleared_calls.intersection_update(current_numbers)
    prev_open = set(open_calls.keys())
    open_calls.clear()
    for call in calls:
        number = call.get("CallNumber")
        if number is not None and number not in cleared_calls:
            open_calls[number] = call
    if CALL_CLEARED:
        for num in prev_open:
            if num not in open_calls and num not in cleared_calls and ("call", num) in seen_keys:
                await announce(f"Be advised, call number {num} has cleared.", title="Call Cleared")
    pending = []
    for call in calls:
        number = call.get("CallNumber")
        started = call.get("StartedAt", 0)
        key = ("call", number)
        if started < boot_time or key in seen_keys or number in cleared_calls:
            continue
        seen_keys.add(key)
        pending.append(call)
    units = await duty_units() if pending else []
    for call in pending:
        last_call = call
        nearest = pick_nearest_units(call, units, 2)
        line = await compose_dispatch(call, nearest)
        if len(open_calls) > 1:
            line = f"{line} Be advised, you now have {len(open_calls)} calls holding."
        await announce(line, tone=is_priority(call))


async def config_refresh_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.sleep(60)
        await refresh_runtime_config()
        await ensure_voice()


async def voice_channel_watch_loop():
    """Near-instant channel switching. Polls only the cheap tokenless voice
    RPC every few seconds and moves the bot the moment the dashboard value
    changes — so picking a channel takes effect in seconds, not up to a
    minute. Acts only on an actual change, so it never causes reconnect churn.
    """
    global VOICE_CHANNEL_ID
    await client.wait_until_ready()
    print("fast voice watcher: ON (checks dashboard every 3s)", flush=True)
    while not client.is_closed():
        await asyncio.sleep(3)
        try:
            vc = await fetch_dispatch_voice_channel()
            if not vc:
                continue
            new_id = int(vc)
            if new_id and new_id != VOICE_CHANNEL_ID:
                print(f"dashboard changed voice channel {VOICE_CHANNEL_ID} -> {new_id}, switching",
                      flush=True)
                VOICE_CHANNEL_ID = new_id
                await ensure_voice()
        except Exception as exc:
            print(f"voice watcher error (continuing): {exc}", flush=True)


async def dispatch_loop():
    await client.wait_until_ready()
    print(f"dispatch loop started, polling emergency calls every {POLL_SECONDS}s", flush=True)
    while not client.is_closed():
        await poll_calls()
        await asyncio.sleep(max(POLL_SECONDS, 15) if active_stops else POLL_SECONDS)


async def ensure_voice():
    global voice_client
    if not client.guilds:
        print("no server yet — add the dispatch bot to your Discord server", flush=True)
        return False
    if not VOICE_CHANNEL_ID:
        print("no voice channel set yet — pick one on the dashboard", flush=True)
        return False
    # Find the channel across every server the bot is in, so the dashboard's
    # channel pick works regardless of which guild it belongs to (and even if
    # a single guild's cache is cold). Fall back to the configured guild.
    channel = client.get_channel(VOICE_CHANNEL_ID)
    if channel is None:
        guild = client.get_guild(GUILD_ID) if GUILD_ID else client.guilds[0]
        channel = guild.get_channel(VOICE_CHANNEL_ID) if guild else None
    if channel is None:
        print(f"voice channel {VOICE_CHANNEL_ID} not found in any server yet", flush=True)
        return False
    guild = channel.guild
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
    if member.bot:
        return
    joined = after.channel is not None and (
        before.channel is None or before.channel.id != after.channel.id)
    left = before.channel is not None and (
        after.channel is None or after.channel.id != before.channel.id)

    if CALLSIGN_NICK and joined and member.id not in nick_original:
        await apply_duty_nick(member)

    if TS_CHANNEL_LABELS:
        # Officer who has an active stop joins a Traffic Stop VC → label it.
        if joined and member.id in active_stops and is_traffic_stop_channel(after.channel.name):
            postal = active_stops[member.id].get("postal") or await officer_postal(member)
            if postal:
                await label_stop_channel(after.channel, postal)
        # Last person leaves a labelled VC → revert its name (after the grace
        # window, so a quick re-stop in the same VC reuses the label).
        if left and before.channel.id in stop_channel_original and not channel_humans(before.channel):
            schedule_restore(before.channel)


@client.event
async def on_ready():
    global http, tone_path, VOICE_CHANNEL_ID
    if http is None:
        http = aiohttp.ClientSession()
    print(f"dispatch online as {client.user}", flush=True)
    print(f"running build: {BUILD}", flush=True)
    try:
        client.loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(_graceful_shutdown()))
    except Exception as exc:
        print(f"could not hook SIGTERM: {exc}", flush=True)

    # Back in the channel FIRST. One quick read for the channel id, then join.
    # Secrets, region, saved memory, command sync and tone generation all
    # happen after — command sync alone has taken over a minute when a guild
    # rejects it, and it used to run ahead of the voice join, which is why a
    # redeploy left the channel silent for so long.
    try:
        vc = await fetch_dispatch_voice_channel()
        if vc:
            VOICE_CHANNEL_ID = int(str(vc).strip())
    except Exception as exc:
        print(f"voice channel read failed: {exc}", flush=True)
    joined = await ensure_voice()
    print(f"voice ready {time.time() - _BOOT_T0:.1f}s after start "
          f"({'in channel' if joined else 'not yet'})", flush=True)

    # The watchers run while the rest of startup finishes.
    for _name, _fn in (("playback_worker", playback_worker), ("dispatch_loop", dispatch_loop),
                       ("voice_guard", voice_guard), ("stop_watch_loop", stop_watch_loop),
                       ("nick_watch_loop", nick_watch_loop), ("officer_down_loop", officer_down_loop),
                       ("config_refresh_loop", config_refresh_loop),
                       ("voice_channel_watch_loop", voice_channel_watch_loop),
                       ("identity_watch_loop", identity_watch_loop),
                       ("state_save_loop", state_save_loop),
                       ("pursuit_track_loop", pursuit_track_loop)):
        client.loop.create_task(_supervise(_name, _fn))

    async def _finish_startup():
        await refresh_runtime_config()
        print(f"region: {DISPATCH_REGION}", flush=True)
        load_links()
        await load_state()
        if not joined:
            await ensure_voice()
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
        if TRAFFIC_STOP_RETURN:
            print(f"traffic-stop auto-return: ON (flee speed {FLEE_SPEED}/sec, needs Move Members perm + /link)", flush=True)
        if STATUS_CHECKS:
            print(f"status checks: ON (after {STATUS_CHECK_SECONDS}s on a stop)", flush=True)
        if OFFICER_DOWN:
            print("officer-down detection: ON", flush=True)
        if CALLSIGN_NICK:
            print("on-duty callsign nicknames: ON (needs Manage Nicknames perm)", flush=True)
        if TS_CHANNEL_LABELS:
            print("traffic-stop VC labels: ON (needs Manage Channels perm)", flush=True)
        if ALERT_TONES and tone_path is None:
            globals()["tone_path"] = await client.loop.run_in_executor(None, make_tone)
            print(f"alert tones: {'ready' if tone_path else 'unavailable'}", flush=True)
        # Slowest and least urgent: a guild that rejects it can block for a minute.
        await sync_commands()
        print(f"startup complete {time.time() - _BOOT_T0:.1f}s after start", flush=True)

    client.loop.create_task(_supervise("startup", _finish_startup))


async def _supervise(name, factory):
    """Run a background loop and start it again if it ever raises. Before
    this, one failed announcement (a TTS or API hiccup) ended the dispatch
    loop for the life of the process while everything else kept logging."""
    while not client.is_closed():
        try:
            await factory()
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"{name} crashed, restarting in 5s: {exc!r}", flush=True)
            traceback.print_exc()
            await asyncio.sleep(5)


client.run(TOKEN)
