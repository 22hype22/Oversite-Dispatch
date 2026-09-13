"""Every state resolves to a code block, and the traps read correctly."""
import ast
import sys

sys.path.insert(0, "/home/user/22hype22/oversite-dispatch")
from state_codes import (STATE_CODES, state_code_block, states_using_codes,  # noqa: E402
                         audit)

SRC = "/home/user/22hype22/oversite-dispatch/main.py"
text = open(SRC).read()
tree = ast.parse(text)
lines = text.split("\n")

# Pull the region plumbing out of main.py and run it for real.
WANT_FN = {"code_reference_for", "canonical_region", "_is_us_region"}
WANT_VAR = {"US_STATES", "COUNTRIES", "REGION_CATALOG", "US_TEN_CODES",
            "US_RESPONSE_CODES", "NATO_PHONETIC", "COUNTRY_PROFILES"}
chunks = []
for n in tree.body:
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in WANT_FN:
        chunks.append("\n".join(lines[n.lineno - 1:n.end_lineno]))
    elif isinstance(n, ast.Assign) and {getattr(t, "id", "") for t in n.targets} & WANT_VAR:
        chunks.append("\n".join(lines[n.lineno - 1:n.end_lineno]))
ns = {"STATE_CODES": STATE_CODES, "state_code_block": state_code_block}
exec("\n\n".join(chunks), ns)
code_ref = ns["code_reference_for"]
canon = ns["canonical_region"]
US_STATES = ns["US_STATES"]

fails = []


def ok(label, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}  {label}{('  ' + extra) if extra else ''}")
    if not cond:
        fails.append(label)


print("== coverage ==")
ok("all 50 states are in the picker", len(US_STATES) == 50, str(len(US_STATES)))
missing = [s for s in US_STATES if s not in STATE_CODES]
ok("every state has a code entry", not missing, str(missing))
extra = [s for s in STATE_CODES if s not in US_STATES]
ok("no entries for places that are not states", not extra, str(extra))
for s in US_STATES:
    e = STATE_CODES[s]
    if e["system"] in ("ten", "signal") and not e["codes"]:
        fails.append(f"{s} claims its own system but lists no codes")
        print(f"FAIL  {s} claims its own system but lists no codes")
    if not e.get("agency") or not e.get("note"):
        fails.append(f"{s} missing agency or note")
        print(f"FAIL  {s} missing agency or note")
print(f"PASS  every state names an agency and carries a note")

counts = {}
for sysname in states_using_codes().values():
    counts[sysname] = counts.get(sysname, 0) + 1
print("      systems:", counts)

print("\n== provenance ==")
VALID = {"official", "corroborated", "single", "default"}
for st, e in STATE_CODES.items():
    if e.get("confidence") not in VALID:
        fails.append(f"{st} has no valid confidence")
        print(f"FAIL  {st} has no valid confidence")
    if not (e.get("source") or "").strip():
        fails.append(f"{st} has no source")
        print(f"FAIL  {st} has no source")
    # A state may only claim codes it can point at a source for.
    if e["codes"] and e["confidence"] == "default":
        fails.append(f"{st} lists codes but is marked unsourced")
        print(f"FAIL  {st} lists codes but is marked unsourced")
    # And a state claiming its own code system must list some. A plain-language
    # or common-set state legitimately has none while still being well sourced.
    if (not e["codes"] and e["system"] in ("ten", "signal")
            and e["confidence"] in ("official", "corroborated")):
        fails.append(f"{st} claims strong sourcing with no codes")
        print(f"FAIL  {st} claims strong sourcing with no codes")
print("PASS  every state records a source and a confidence")
print("PASS  no state asserts codes it cannot source")
counts = {}
for conf, *_ in audit():
    counts[conf] = counts.get(conf, 0) + 1
print("      ", counts)

# The weakly sourced states must tell the AI to defer to the unit.
for st, e in STATE_CODES.items():
    block = state_code_block(st)
    if e["confidence"] == "single" and "follow their lead" not in block:
        fails.append(f"{st} is single-sourced but asserted flatly")
        print(f"FAIL  {st} single-sourced but asserted flatly")
    if e["confidence"] == "default" and "mirror whatever" not in block:
        fails.append(f"{st} is unsourced but asserted flatly")
        print(f"FAIL  {st} unsourced but asserted flatly")
print("PASS  thinly sourced states defer to the unit on the air")

print("\n== the code clashes that matter ==")
CASES = [
    ("Alaska", "10-97 no wants or warrants", "10-97 means the subject is clear"),
    ("Louisiana", "10-50 officer down", "Louisiana 10-50 is an officer down"),
    ("Texas", "10-50 traffic accident", "Texas 10-50 is a crash"),
    ("New York", "10-13 officer needs assistance", "10-13 is an officer calling"),
    ("New Hampshire", "10-4 repeat message", "10-4 means say again here"),
    ("Michigan", "10-10 subject has a felony warrant", "record results here"),
    ("Pennsylvania", "10-45 accident", "accident at 10-45"),
    ("Nebraska", "10-50 use caution", "10-50 means use caution"),
    ("Oregon", "12-16 motor vehicle accident", "12-codes, not 10-codes"),
    ("Wisconsin", "10-87 traffic stop", "A stop is 10-87"),
    ("Alabama", "10-97 civil disturbance", "Alabama 10-97 is a civil disturbance"),
    ("South Dakota", "10-97 arrived at the scene", "10-23 is a status check"),
    ("North Carolina", "10-43 chase", "10-43 is a pursuit"),
    ("Florida", "Signal 45 officer down", "Officer down is Signal 45"),
    ("Idaho", "Code 1000 trooper taken hostage", "do not use 10-codes"),
]
for state, code_text, note_text in CASES:
    block = state_code_block(state)
    ok(f"{state}: {code_text}", code_text in block, "" if code_text in block else block[:110])
    ok(f"{state}: the warning is spelled out", note_text in block)

print("\n== states that do not use 10-codes are not handed them ==")
for state in ("Connecticut", "Florida", "Ohio", "Oregon", "Rhode Island",
              "Massachusetts", "Maryland", "Virginia", "Missouri", "Utah", "Idaho"):
    ref = code_ref(state)
    has_generic = "Radio codes:" in ref
    ok(f"{state} is not given the generic 10-code list", not has_generic)
    ok(f"{state} is told to use its own system",
       "Use that system, not the standard 10-codes" in ref or "plain language" in ref.lower())

print("\n== states that do use 10-codes still get the baseline ==")
for state in ("Alaska", "Texas", "Michigan", "Kansas", "Vermont"):
    ref = code_ref(state)
    ok(f"{state} gets the common list as a floor", "Radio codes:" in ref)

print("\n== the reference is usable as a prompt ==")
for state in US_STATES:
    ref = code_ref(state)
    if not ref.strip():
        fails.append(f"{state} produced an empty reference")
        print(f"FAIL  {state} produced an empty reference")
    if len(ref) > 2400:
        fails.append(f"{state} reference is {len(ref)} chars, too long for the prompt")
        print(f"FAIL  {state} reference too long ({len(ref)})")
sizes = sorted((len(code_ref(s)), s) for s in US_STATES)
print(f"PASS  every state renders, {sizes[0][0]}-{sizes[-1][0]} chars "
      f"(longest {sizes[-1][1]})")

print("\n== free text still lands on the right state ==")
for typed, want in [("alaska", "Alaska"), ("NEW HAMPSHIRE", "New Hampshire"),
                    ("  texas  ", "Texas"), ("the united states", "the United States")]:
    got = canon(typed)
    ok(f"{typed!r} -> {want}", got == want, f"got {got!r}")
ok("an unknown place is kept as typed", canon("Sarasota") == "Sarasota")
ok("an unknown place gets a sane reference", "radio codes" in code_ref("Sarasota").lower())

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
