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

VOICE_CMD_ENABLED = VOICE_COMMANDS and VOICE_RECV_AVAILABLE and OPUS_OK

ERLC_V2_BASE = "https://api.erlc.gg/v2"
XI_BASE = "https://api.elevenlabs.io/v1"
ANTHROPIC_BASE = "https://api.anthropic.com/v1"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

play_queue = asyncio.Queue()
seen_keys = set()
boot_time = time.time()
voice_client = None
http = None
last_call = None
response_cache = {}


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


DISPATCH_SYSTEM = (
    "You are Oversite Dispatch, a professional emergency dispatcher for an "
    "Emergency Response: Liberty County (ER:LC) roleplay server. Police officers "
    "and sheriff deputies talk to you over the radio. Answer with exactly one "
    "short radio transmission, the way a real dispatcher would respond.\n"
    "Rules:\n"
    "- One or two sentences at most. Radio brevity. No preamble and no sign-off.\n"
    "- Do not include the unit's callsign in your reply; it is added automatically. "
    "Give only the dispatch response itself.\n"
    "- Use standard ten-codes and plain dispatch language: 10-4 to acknowledge, "
    "10-8 in service, 10-7 out of service, 10-76 en route, 10-97 on scene, "
    "10-20 for location, 10-23 standing by, Code 3 for lights and sirens, Code 4 "
    "scene secure. Echo status changes back to the unit, for example 'show you 10-8'.\n"
    "- When a unit attaches to a call, marks en route, or updates their status, "
    "just confirm the action in a few words. Do not read back or restate the "
    "call's details unless the unit explicitly asks you to repeat the call.\n"
    "- You cannot look up plates, warrants, names, or run records. If asked to run "
    "one, advise the unit the return is negative or to stand by, staying in character.\n"
    "- Never break character, never say you are an AI, never use markdown or emojis.\n"
    "- Output only the words dispatch would speak over the radio."
)


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
    triggers = ("repeat", "say again", "come again", "one more time",
                "last call", "that call", "read it back", "read back",
                "what was the last", "what was that")
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
    callsign = " ".join(parts).strip(" ,.-")
    if not callsign or len(callsign) > 24:
        return ""
    return callsign


async def handle_utterance(member, pcm):
    if len(pcm) < 96000:
        return
    print(f"utterance: {len(pcm)} bytes of pcm (~{len(pcm)/192000:.1f}s)", flush=True)
    text = await transcribe(pcm_to_wav(pcm))
    if not text:
        return
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
    body = await dispatch_reply_body(text, callsign)
    ack = f"Unit {callsign}, " if callsign else ""
    if body:
        await announce(ack + body, title="Dispatch")
    else:
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
        reason = "disabled by config" if not VOICE_COMMANDS else (
            "voice-recv extension missing" if not VOICE_RECV_AVAILABLE else "libopus not loaded")
        print(f"voice commands: OFF ({reason}) — 911 dispatch still runs normally", flush=True)
    if AI_ENABLED:
        print(f"ai responses: ENABLED (model {AI_MODEL})", flush=True)
    else:
        print("ai responses: OFF (set ANTHROPIC_API_KEY to let dispatch answer radio traffic)", flush=True)
    await ensure_voice()
    client.loop.create_task(playback_worker())
    client.loop.create_task(dispatch_loop())
    client.loop.create_task(voice_guard())


client.run(TOKEN)
