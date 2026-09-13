"""What the police in one US state actually say on the radio.

There is no national 10-code and no state statute that sets one. APCO published
a recommended list decades ago, adoption was voluntary, and every agency edited
it, so the same number means different things a state apart. The closest thing
to a statewide standard is whatever the state police or highway patrol use, and
that is what this table records.

It matters because the clashes are not cosmetic:

    10-97  on scene almost everywhere, NO WANTS OR WARRANTS in Alaska
    10-50  traffic accident in Texas, OFFICER DOWN in Louisiana
    10-13  a weather report under APCO, OFFICER NEEDS HELP in New York
    10-4   acknowledgement nearly everywhere, REPEAT MESSAGE in New Hampshire

Several states do not use 10-codes at all. Connecticut, Florida, Rhode Island
and Ohio run on signal numbers, Oregon on 12-codes, Massachusetts on plain
"Code" numbers, and Maryland, Missouri and Virginia have moved their state
agencies to plain language outright.

Each entry holds only what a source actually stated. Where nothing state
specific could be confirmed, `system` is "apco" and the bot falls back to the
common set rather than inventing one. Codes here are the operational handful a
dispatcher says out loud, not a complete sheet.
"""

# system:
#   "ten"    a 10-code set of its own, listed in codes
#   "apco"   the common APCO 10-codes, nothing state specific confirmed
#   "signal" signal or code numbers instead of 10-codes
#   "plain"  the state agency has dropped codes for plain language
STATE_CODES = {
    "Alabama": {
        "agency": "Alabama State Troopers",
        "system": "ten",
        "codes": {
            "00": "officer needs all possible assistance",
            "10-23": "arrived at scene",
            "10-26": "detaining person or vehicle, expedite",
            "10-29": "check if person or vehicle is wanted",
            "10-31": "hit and run",
            "10-32": "person with a gun",
            "10-33": "emergency, maximum priority, maintain radio silence",
            "10-36": "urgent call, use lights and siren",
            "10-37": "urgent, silent run, no lights or siren",
            "10-38": "investigate suspicious vehicle",
            "10-39": "stopping suspicious vehicle",
            "10-40": "stolen vehicle",
            "10-50": "accident",
            "10-55": "intoxicated driver",
            "10-57": "crime in progress",
            "10-72": "meet complainant",
            "10-84": "en route",
            "10-89": "dead person",
            "10-92": "murder",
            "10-95": "reckless driving",
            "10-97": "civil disturbance",
            "10-99": "records indicate wanted or stolen",
            "10-100": "hot pursuit",
        },
        "note": "Alabama 10-97 is a civil disturbance, not an arrival and not a "
                "records result. On scene is 10-23, en route is 10-84 and a "
                "pursuit is 10-100. The double zero call clears the air.",
        "source": "Ala. Admin. Code r. 265-X-3-.01, Alabama Criminal Justice "
                  "Information Center radio communication codes",
        "confidence": "official"
    },
    "Alaska": {
        "agency": "Alaska State Troopers",
        "system": "ten",
        "codes": {
            "10-23": "arrived at scene",
            "10-26": "detaining subject, expedite",
            "10-27": "driver license check",
            "10-28": "vehicle registration",
            "10-29": "check for wants and warrants",
            "10-36": "routine traffic stop",
            "10-39": "urgent, use lights and siren",
            "10-40": "urgent, no lights or siren",
            "10-50": "vehicle accident",
            "10-55": "driving while intoxicated",
            "10-57": "hit and run",
            "10-60": "welfare check",
            "10-68": "request backup",
            "10-69": "emergency backup",
            "10-79": "notify coroner",
            "10-80": "in custody",
            "10-97": "no wants or warrants",
            "10-99": "wanted and dangerous",
        },
        "note": "Alaska 10-97 means the subject is clear, not that a unit is on "
                "scene. On scene is 10-23. Never use 10-97 to mean arrival here.",
        "source": 'police-codes.com Alaska page cross-checked against independent Alaska State Troopers 10-code study sets',
        "confidence": 'corroborated',
    },
    "Arizona": {
        "agency": "Arizona Department of Public Safety",
        "system": "ten",
        "codes": {
            "10-80": "chase in progress",
            "10-82": "no backup available",
            "10-88": "records indicate wanted",
            "10-90": "alarm",
            "10-91": "pick up prisoner",
            "10-95": "prisoner in custody",
            "10-96": "mental subject",
            "10-98": "escape",
            "10-100": "supervisor",
        },
        "note": "Arizona reports a warrant hit as 10-88, not 10-99.",
        "source": 'AZ DPS 10-code study sets and the RadioReference Arizona DPS wiki',
        "confidence": 'single',
    },
    "Arkansas": {
        "agency": "Arkansas State Police",
        "system": "apco",
        "codes": {},
        "note": "Arkansas agencies that use codes generally follow the state "
                "police, who stay close to the common set.",
        "source": 'no state-specific list located; sources say agencies follow the state police, who stay near the common set',
        "confidence": 'default',
    },
    "California": {
        "agency": "California Highway Patrol",
        "system": "ten",
        "codes": {
            "10-14": "provide escort",
            "10-15": "prisoner in custody",
            "10-23": "stand by",
            "10-29": "check for wanted",
            "10-31": "attempted suicide",
            "10-36": "confidential information",
            "11-25": "traffic hazard",
            "11-44": "fatality at the scene",
            "11-80": "collision, major injury",
            "11-81": "collision, minor injury",
            "11-85": "tow truck requested",
            "11-99": "officer needs help",
        },
        "note": "CHP runs 11-codes alongside the 10-codes for anything on the "
                "road, and California 10-23 is stand by, not on scene. Penal "
                "code numbers are said on the air as call types: 187 homicide, "
                "207 kidnapping, 211 robbery, 240 assault, 245 assault with a "
                "deadly weapon, 415 disturbance, 459 burglary, 484 theft, "
                "5150 mental health hold, 23152 DUI.",
        "source": 'CHP radio code references and California police code guides agreeing on the 10- and 11-codes',
        "confidence": 'corroborated',
    },
    "Colorado": {
        "agency": "Colorado State Patrol",
        "system": "apco",
        "codes": {},
        "note": "Colorado State Patrol uses the expanded APCO set. Troopers open "
                "a transmission by naming the dispatch centre, then their call sign.",
        "source": 'RadioReference Colorado State Patrol wiki, which states the patrol uses the expanded APCO set',
        "confidence": 'single',
    },
    "Connecticut": {
        "agency": "Connecticut State Police",
        "system": "signal",
        "codes": {
            "Signal 10": "accident",
            "Signal 11": "fatal accident",
            "Signal 12": "motor vehicle violator",
            "Signal 13": "driving while intoxicated",
            "Signal 14": "disabled motorist",
            "Signal 20": "NCIC check",
            "Signal 23": "alarm",
            "Signal 25": "escape",
            "Signal 31": "out of service, on scene",
            "Signal 32": "in service",
            "Signal 34": "location",
            "Signal 35": "return to troop",
        },
        "note": "Connecticut troopers run signals, not 10-codes. Code A is an "
                "emergency, Code B is sensitive information.",
        "source": 'Connecticut State Police brevity code references and trooper radio code study sets',
        "confidence": 'corroborated',
    },
    "Delaware": {
        "agency": "Delaware State Police",
        "system": "ten",
        "codes": {
            "10-1": "situation under control",
            "10-2": "arriving at scene",
            "10-3": "go ahead with message",
            "10-10": "accident, personal injury, property damage or hit and run",
            "10-15": "prisoner in custody",
            "10-18": "clear the assignment as soon as possible",
            "10-23": "direct traffic",
            "10-24": "send assistance to scene",
            "10-100": "clear the air, emergency message",
        },
        "note": "Delaware is a long way from the common set: arrival is 10-2, an "
                "accident is 10-10, and the 10-80s and 10-90s are medical "
                "conditions rather than police calls.",
        "source": 'Delaware police 10-code study sets and the RadioReference Delaware state agencies wiki',
        "confidence": 'single',
    },
    "Florida": {
        "agency": "Florida Highway Patrol and state law enforcement",
        "system": "signal",
        "codes": {
            "Signal 0": "armed, use caution",
            "Signal 1": "driving under the influence",
            "Signal 3": "hit and run crash",
            "Signal 4": "vehicle crash",
            "Signal 4I": "vehicle crash with injuries",
            "Signal 5": "murder",
            "Signal 6": "escaped prisoner",
            "Signal 7": "fatality",
            "Signal 11": "abandoned vehicle",
            "Signal 12": "reckless vehicle",
            "Signal 13": "suspicious person or vehicle",
            "Signal 18": "felony",
            "Signal 19": "misdemeanor",
            "Signal 30": "shooting",
            "Signal 43": "assist the public",
            "Signal 45": "officer down",
            "Signal 47": "bomb threat",
            "Signal 61": "past criminal history",
            "Signal 76": "disabled vehicle",
            "Signal 99": "possible computer hit, unconfirmed",
            "Signal 99C": "confirmed computer hit",
            "TRF": "traffic stop",
            "HP": "hot pursuit",
            "ATL": "attempt to locate",
            "BOLO": "be on the lookout",
        },
        "note": "Florida runs signals with letter suffixes for the specific "
                "variant, and says some calls as plain words: TRF for a stop, HP "
                "for a pursuit, BOLO and ATL. Officer down is Signal 45, and "
                "Signal 0 means armed and dangerous, not a call for help.",
        "source": "Florida Department of Management Services SOP 14, State Law "
                  "Enforcement Signal Codes (JTF approved)",
        "confidence": "official"
    },
    "Georgia": {
        "agency": "Georgia State Patrol",
        "system": "ten",
        "codes": {
            "10-0": "use caution",
            "10-12": "unwelcome visitor present",
            "10-14": "escort or convoy",
            "10-15": "prisoner in custody",
            "10-17": "warrants",
            "10-18": "high rate of speed",
        },
        "note": "Georgia says 10-17 for warrants, where most states use it to "
                "mean meet the complainant.",
        "source": 'Georgia State Patrol 10-code study sets',
        "confidence": 'single',
    },
    "Hawaii": {
        "agency": "Hawaii county police departments",
        "system": "ten",
        "codes": {"10-19": "traffic accident"},
        "note": "Hawaii has no state police force; the four county departments "
                "each run their own set and the fire service has moved to plain "
                "language. Stay close to the common codes.",
        "source": 'RadioReference Hawaii county police wiki; no state force exists, so the four county departments each differ and only one code was confirmable',
        "confidence": 'single',
    },
    "Idaho": {
        "agency": "Idaho State Police",
        "system": "signal",
        "codes": {
            "Code 1": "normal driving",
            "Code 2": "more urgent",
            "Code 3": "lights and siren, urgent or critical",
            "Code 4": "the trooper is okay",
            "Code 6 Charles": "felony hit from NCIC",
            "Code 6 Mary": "misdemeanor hit",
            "Code 6 Victor": "return from the Threat Screening Center file",
            "Code 7": "trooper is leaving the vehicle for a break",
            "Code 1000": "trooper taken hostage",
        },
        "note": "Idaho troopers do not use 10-codes. Record returns come back as "
                "Code Six Charles or Code Six Mary, and on a Charles the "
                "dispatcher clears the air for emergency traffic.",
        "source": "Idaho State Police Procedure 07.12, Patrol Radio Operations",
        "confidence": "official"
    },
    "Illinois": {
        "agency": "Illinois State Police",
        "system": "ten",
        "codes": {
            "10-0": "use caution",
            "10-1": "unable to copy, change location",
            "10-41": "beginning tour of duty",
            "10-42": "ending tour of duty",
        },
        "note": "Ten-codes were invented here, by the Illinois State Police in "
                "1937. Illinois agencies mix codes, plain language and statute "
                "numbers.",
        "source": 'Illinois police code guides; the origin of ten-codes with the state police in 1937 is well documented',
        "confidence": 'single',
    },
    "Indiana": {
        "agency": "Indiana State Police",
        "system": "ten",
        "codes": {
            "10-0": "deceased person",
            "10-43": "information",
            "10-45": "dead animal in the road",
            "10-46": "assist motorist",
            "10-50": "accident, fatal, personal injury or property damage",
            "Signal 23": "vehicle well over the posted limit",
            "Signal 80": "computer check came back clear",
        },
        "note": "Indiana runs signal numbers beside the 10-codes, and a clear "
                "record check comes back as Signal 80.",
        "source": 'Indiana scanner code references and the RadioReference Indiana State Police wiki',
        "confidence": 'single',
    },
    "Iowa": {
        "agency": "Iowa State Patrol",
        "system": "ten",
        "codes": {
            "10-83": "welfare check",
            "10-95": "subject in custody",
            "10-99": "wanted or stolen",
        },
        "note": "Iowa departments mostly run the common APCO set with these few "
                "of their own.",
        "source": 'Iowa police 10-code references; most departments run the common set',
        "confidence": 'single',
    },
    "Kansas": {
        "agency": "Kansas Highway Patrol",
        "system": "apco",
        "codes": {},
        "note": "The highway patrol uses the standard set; many local agencies "
                "have moved to plain speech.",
        "source": 'Missouri/Kansas scanner wiki, which states the highway patrol uses the standard set',
        "confidence": 'single',
    },
    "Kentucky": {
        "agency": "Kentucky State Police",
        "system": "apco",
        "codes": {},
        "note": "No distinct statewide set confirmed; stay with the common codes.",
        "source": 'no state-specific list located',
        "confidence": 'default',
    },
    "Louisiana": {
        "agency": "Louisiana State Police",
        "system": "ten",
        "codes": {
            "10-10": "out of service on a call",
            "10-12": "visitors present",
            "10-14": "convoy",
            "10-15": "prisoner in custody",
            "10-50": "officer down",
        },
        "note": "Louisiana 10-50 is an officer down, not an accident. This is the "
                "worst code clash in the country and the one to get right. Do not "
                "use 10-50 for a crash in Louisiana.",
        "source": 'RadioReference Louisiana discussion and police1 reporting on the 10-50 clash; sources warn most published Louisiana lists are wrong, so only the corroborated few are kept',
        "confidence": 'single',
    },
    "Maine": {
        "agency": "Maine State Police",
        "system": "ten",
        "codes": {
            "10-23": "stand by",
            "10-24": "records indicate stolen",
            "10-25": "pedestrian check",
            "10-26": "detaining subject",
            "10-29": "stolen or wanted check",
            "10-31": "crime in progress",
            "10-32": "person with a weapon",
            "10-33": "chase in progress",
        },
        "note": "Maine 10-23 is stand by rather than on scene, and a pursuit is "
                "10-33.",
        "source": 'Maine 10-code and signal references',
        "confidence": 'single',
    },
    "Maryland": {
        "agency": "Maryland State Police",
        "system": "plain",
        "codes": {},
        "note": "Maryland State Police dropped 10-codes on 1 February 2012 and "
                "run plain English, so troopers do not say 10-4. Speak in plain "
                "language, though older hands still slip a code in.",
        "source": 'Washington Post and NBC4 Washington reporting on the Maryland State Police dropping ten codes on 1 February 2012',
        "confidence": 'corroborated',
    },
    "Massachusetts": {
        "agency": "Massachusetts State Police",
        "system": "signal",
        "codes": {
            "Code 1": "stand by for emergency, all units off the air",
            "Code 2": "phone your barracks",
            "Code 4": "cruiser out of service",
            "Code 5": "cruiser in service",
            "Code 6": "what is your location",
            "Code 7": "return to your barracks",
            "Code 8": "stopping suspicious car",
            "Code 9": "registration information",
            "Code 10": "stolen check",
            "Code 11": "license data",
            "Code 14": "missing or wanted",
            "Code 15": "officer in trouble",
        },
        "note": "Massachusetts troopers work in plain Code numbers, not "
                "10-codes. Code 15 is the emergency.",
        "source": 'Massachusetts State Police radio code references',
        "confidence": 'single',
    },
    "Michigan": {
        "agency": "Michigan State Police",
        "system": "ten",
        "codes": {
            "10-8": "subject is a registered sex offender",
            "10-9": "subject has a misdemeanor or traffic warrant",
            "10-10": "subject has a felony warrant",
            "10-13": "trooper needs emergency assistance",
            "10-14": "request medical examiner",
            "10-25": "cancel",
            "10-49": "accident with injuries",
            "10-51": "en route",
            "10-59": "meet the complainant",
            "10-60": "check the area",
            "10-99": "shots fired, request backup",
            "Signal 1": "traffic stop",
            "Signal 2": "call the post",
            "Signal 3": "return to the post",
            "Signal 4": "trooper needs emergency assistance",
        },
        "note": "Michigan is one of the furthest from the common set. 10-8 and "
                "10-10 are record results here, not service status, so never use "
                "10-8 to mean in service in Michigan. A stop is Signal 1.",
        "source": 'Michigan State Police radio code study sets and the RadioReference Department of State Police wiki',
        "confidence": 'corroborated',
    },
    "Minnesota": {
        "agency": "Minnesota State Patrol",
        "system": "ten",
        "codes": {
            "10-7": "off duty",
            "10-8": "on duty, clear",
            "10-14": "transport",
            "10-15": "transport to jail",
            "10-22": "cancel, disregard",
            "10-24": "status okay",
            "10-29": "stolen vehicle or party with warrants",
            "10-31": "status check",
            "10-33": "emergency",
            "10-72": "dead person",
            "10-73": "abandoned vehicle",
            "10-74": "theft",
            "10-75": "juvenile trouble",
            "10-76": "see complainant",
            "10-77": "prowler",
        },
        "note": "Minnesota folds warrants and stolen vehicles into one code, "
                "10-29, and uses 10-31 to ask a unit if it is okay.",
        "source": 'RadioReference Minnesota 10-codes wiki and two independent Minnesota scanner code pages',
        "confidence": 'corroborated',
    },
    "Mississippi": {
        "agency": "Mississippi Highway Patrol",
        "system": "ten",
        "codes": {
            "10-17": "urgent, rush",
            "10-23": "arrived at scene",
            "10-26": "detaining subject or vehicle",
            "10-27": "driver license check",
            "10-29": "stolen",
            "10-91": "civil disturbance",
            "10-92": "mental case",
            "10-94": "pursuit in progress",
        },
        "note": "Mississippi puts a pursuit at 10-94, where most states use that "
                "number for drag racing.",
        "source": 'Mississippi Highway Patrol radio code references',
        "confidence": 'single',
    },
    "Missouri": {
        "agency": "Missouri State Highway Patrol",
        "system": "plain",
        "codes": {
            "10-1": "unable to copy",
            "10-2": "signal good",
            "10-3": "affirmative, granted",
            "10-4": "message received",
            "10-5": "relay",
        },
        "note": "Missouri has no endorsed 10-codes on its statewide radio system "
                "and the Department of Public Safety discourages them, so prefer "
                "plain language with only the handful above.",
        "source": 'RadioReference Missouri Department of Public Safety wiki, which records that the department discourages ten codes on the statewide system',
        "confidence": 'single',
    },
    "Montana": {
        "agency": "Montana Highway Patrol",
        "system": "ten",
        "codes": {
            "10-25": "reckless driver",
            "10-28": "vehicle registration",
            "10-29": "warrant check",
            "10-31": "driver license check",
            "10-61": "driving under the influence",
            "10-85": "en route",
            "901": "traffic stop",
            "902": "officer needs help",
            "903": "in pursuit",
            "904": "everything okay",
            "905": "vehicle accident",
        },
        "note": "Montana runs a 900 series beside the 10-codes: a stop is a 901, "
                "a pursuit a 903 and a crash a 905.",
        "source": 'Montana police code references; the 900 series may be county practice rather than Highway Patrol, so treat it as indicative',
        "confidence": 'single',
    },
    "Nebraska": {
        "agency": "Nebraska State Patrol",
        "system": "ten",
        "codes": {
            "10-15": "prisoner in custody",
            "10-18": "urgent, rush this detail",
            "10-38": "potentially dangerous offender",
            "10-39": "registration information with VIN",
            "10-40": "drug violation",
            "10-44": "accident, property damage",
            "10-45": "accident, personal injury",
            "10-46": "dispatch wrecker",
            "10-47": "driving while intoxicated",
            "10-48": "speeder",
            "10-50": "use caution",
            "10-55": "dispatch ambulance",
        },
        "note": "Nebraska 10-50 means use caution, not an accident. Crashes split "
                "into 10-44 for damage and 10-45 for injuries.",
        "source": 'Nebraska statewide 10-code list published by a Nebraska fire department and the RadioReference Nebraska State Patrol wiki',
        "confidence": 'corroborated',
    },
    "Nevada": {
        "agency": "Nevada Highway Patrol",
        "system": "ten",
        "codes": {
            "10-15": "have in possession",
            "10-17": "urgent, rush",
            "10-34": "trouble at station",
            "10-35": "major crime alert",
            "10-36": "confidential information",
            "10-51": "wrecker needed",
            "10-52": "ambulance needed",
            "10-53": "coroner needed",
            "10-54": "district attorney needed",
        },
        "note": "Nevada uses 10-53 for the coroner, where most states use it for "
                "a blocked road.",
        "source": 'Nevada radio code references; parts of the published list look dated, so treat it as indicative',
        "confidence": 'single',
    },
    "New Hampshire": {
        "agency": "New Hampshire State Police",
        "system": "ten",
        "codes": {
            "10-1": "in service",
            "10-2": "out of service, off the air",
            "10-3": "go ahead",
            "10-4": "repeat message",
            "Code 1": "with traffic, when convenient",
            "Code 2": "urgent response",
            "Code 3": "emergency response",
            "Code 4": "emergency, no lights or siren",
            "Signal 1000": "emergency, hold all non-emergency traffic",
        },
        "note": "New Hampshire is the sharpest trap in the country: 10-4 means "
                "say again here, not acknowledged, and 10-1 and 10-2 are service "
                "status. Nearly every agency in the state runs this set.",
        "source": 'New Hampshire police radio 10-code reference and the RadioReference New Hampshire police codes wiki',
        "confidence": 'corroborated',
    },
    "New Jersey": {
        "agency": "New Jersey State Police",
        "system": "ten",
        "codes": {
            "10-23": "arrived at scene",
            "10-29": "check for wanted",
            "10-31": "crime in progress",
            "10-32": "man with a gun",
            "10-50": "accident, fatal, personal injury or property damage",
        },
        "note": "New Jersey stays close to the common set.",
        "source": 'New Jersey State official ten-code list published by a state police association, plus a New Jersey police code guide',
        "confidence": 'corroborated',
    },
    "New Mexico": {
        "agency": "New Mexico State Police",
        "system": "ten",
        "codes": {
            "10-97": "arrived on scene",
            "10-98": "last assignment completed",
            "10-99": "officer needs assistance",
            "10-100": "riot conditions",
        },
        "note": "No single statewide list; state, county, city and tribal "
                "agencies each differ. New Mexico 10-99 is an officer calling "
                "for help, not a wanted return.",
        "source": 'New Mexico police 10-code references; the state has no single mandated list',
        "confidence": 'single',
    },
    "New York": {
        "agency": "New York State Police, and NYPD downstate",
        "system": "ten",
        "codes": {
            "10-1": "call your command",
            "10-2": "return to your command",
            "10-3": "call the dispatcher by telephone",
            "10-13": "officer needs assistance",
            "10-30": "robbery in progress",
            "10-31": "burglary in progress",
            "10-34": "assault",
            "10-52": "dispute",
            "10-53": "vehicle accident",
            "10-85": "need backup at scene",
        },
        "note": "New York 10-13 is an officer calling for urgent help and drops "
                "everything. Under the common set that same number is a weather "
                "report, so never use 10-13 for conditions in New York.",
        "source": 'NYPD signal code references; the New York State Police set is not separately published',
        "confidence": 'corroborated',
    },
    "North Carolina": {
        "agency": "North Carolina State Highway Patrol",
        "system": "ten",
        "codes": {
            "10-17": "en route",
            "10-23": "arrived at scene",
            "10-29": "records check",
            "10-30": "danger, caution",
            "10-33": "help me quick",
            "10-43": "chase",
            "10-48": "detaining subject, expedite",
            "10-50": "collision, property damage, injury or fatal",
            "10-54": "hit and run",
            "10-55": "intoxicated driver",
            "10-61": "stopping suspicious vehicle",
            "10-64": "crime in progress",
            "10-72": "have prisoner in custody",
            "10-73": "mental subject",
            "10-75": "records indicate wanted or stolen",
            "Signal 1": "suspect armed and dangerous",
            "Signal 5": "situation under control, no further assistance needed",
            "Signal 16": "registered sex offender",
            "Signal 31": "respond to active shooter situation",
        },
        "note": "The patrol calls these ten signals and runs lettered Signals "
                "beside them for record returns. 10-33 is the emergency call and "
                "10-43 is a pursuit.",
        "source": "NC State Highway Patrol form HP-979 Rev.02/2013, Official Ten "
                  "Signals",
        "confidence": "official"
    },
    "North Dakota": {
        "agency": "North Dakota Highway Patrol",
        "system": "apco",
        "codes": {},
        "note": "No distinct statewide set confirmed; the patrol works through "
                "State Radio on the common codes.",
        "source": 'no statewide patrol list located; the patrol works through State Radio',
        "confidence": 'default',
    },
    "Ohio": {
        "agency": "Ohio State Highway Patrol",
        "system": "signal",
        "codes": {
            "Signal 1": "out of service",
            "Signal 2": "in service",
            "Signal 3": "out of service, on a call",
            "Signal 5": "rush",
            "Signal 13": "phone the post",
            "Signal 23": "go to the post",
            "Signal 30": "fatal accident",
            "Signal 31": "property damage accident",
            "Signal 31A": "injury accident",
            "Signal 32": "road blocked",
            "Signal 33": "drowning",
        },
        "note": "The Ohio patrol does not use 10-codes at all. Its numbers stand "
                "alone, so a unit goes Signal 2 for in service, never 10-8.",
        "source": 'Ohio State Highway Patrol signal listings from two independent scanner archives and OSP study sets',
        "confidence": 'corroborated',
    },
    "Oklahoma": {
        "agency": "Oklahoma Highway Patrol",
        "system": "ten",
        "codes": {
            "10-15": "subject in custody",
            "10-70": "stopping a vehicle, may be dangerous",
            "10-71": "officer is clear from the 10-70",
            "10-85": "keep the vehicle under surveillance, do not stop",
            "10-97": "arrived at scene",
            "10-98": "last assignment completed",
            "Signal 9": "bomb threat",
            "Signal 30": "fatal accident",
            "Signal 76": "accident, seriousness unknown",
            "Signal 81": "minor accident",
            "Signal 82": "major accident",
        },
        "note": "Oklahoma pairs a risky stop, 10-70, with 10-71 when the trooper "
                "is clear of it, and grades crashes by signal number.",
        "source": 'Oklahoma Highway Patrol ten-code archive and the RadioReference Oklahoma Highway Patrol entry',
        "confidence": 'corroborated',
    },
    "Oregon": {
        "agency": "Oregon State Police",
        "system": "signal",
        "codes": {
            "12-1": "in service",
            "12-2": "out of service",
            "12-3": "return to office",
            "12-4": "call the office by phone",
            "12-7": "vehicle registration check",
            "12-10": "driver license and driving status check",
            "12-16": "motor vehicle accident",
            "12-16A": "motor vehicle accident, fatal",
            "12-18": "dispatch ambulance",
            "12-19": "dispatch tow vehicle",
            "12-20": "check wanted or stolen status",
        },
        "note": "Oregon State Police run 12-codes, not 10-codes. Never say a "
                "10-code to an Oregon trooper.",
        "source": 'Oregon State Police radio code reference and the RadioReference Oregon State Police wiki, both recording 12-codes',
        "confidence": 'corroborated',
    },
    "Pennsylvania": {
        "agency": "Pennsylvania State Police",
        "system": "ten",
        "codes": {
            "10-17": "en route",
            "10-23": "arrived on scene",
            "10-27": "driver license information",
            "10-28": "vehicle registration",
            "10-29": "wants and warrants check",
            "10-30": "danger, caution",
            "10-45": "accident",
            "10-46": "holding a suspect, rush the reply",
            "10-47": "send an ambulance",
            "10-97": "radio check",
            "10-99": "emergency",
            "Signal 33": "help me quickly",
        },
        "note": "Pennsylvania puts an accident at 10-45, not 10-50, and 10-97 is "
                "only a radio check here, never an arrival.",
        "source": 'RadioReference Pennsylvania State Police 10-codes wiki and PSP study sets',
        "confidence": 'corroborated',
    },
    "Rhode Island": {
        "agency": "Rhode Island State Police",
        "system": "signal",
        "codes": {
            "Signal 1": "call the barracks",
            "Signal 2": "return to the barracks",
            "Signal 5": "accident",
            "Signal 6": "do not transmit",
            "Signal 10": "hit and run",
            "Signal 15": "hold up",
            "Signal 20": "stolen vehicle",
            "Signal 30": "missing or lost person",
            "Signal 50": "driving while intoxicated",
        },
        "note": "Rhode Island troopers run signals rather than 10-codes.",
        "source": 'Rhode Island signal code references',
        "confidence": 'single',
    },
    "South Carolina": {
        "agency": "South Carolina Highway Patrol",
        "system": "apco",
        "codes": {},
        "note": "No distinct statewide patrol set confirmed; county systems vary "
                "widely, so stay with the common codes.",
        "source": 'no statewide patrol list located; the results found were county systems, so they were not used',
        "confidence": 'default',
    },
    "South Dakota": {
        "agency": "South Dakota Highway Patrol",
        "system": "ten",
        "codes": {
            "10-16": "NCIC check",
            "10-16H": "hit on NCIC",
            "10-23": "status check",
            "10-28": "check full registration",
            "10-29": "check for record or wanted",
            "10-29H": "local wants or warrant hit",
            "10-29W": "wanted check only",
            "10-31": "send wrecker",
            "10-32": "send ambulance",
            "10-33": "emergency traffic, all stand by",
            "10-44": "stopping a vehicle, description and plate",
            "10-50": "use caution",
            "10-53": "request backup, non-emergency",
            "10-54": "requesting backup, emergency",
            "10-59": "driver license status",
            "10-71": "send coroner",
            "10-78S": "sex offender",
            "10-97": "arrived at the scene",
            "10-98": "assignment complete",
            "10-99": "emergency, all units and stations copy",
        },
        "note": "South Dakota 10-23 is a status check, not an arrival. On scene "
                "is 10-97 and a traffic stop is 10-44. Backup splits into 10-53 "
                "routine and 10-54 emergency.",
        "source": "South Dakota Communications Field Operations Guide (SD-CFOG), "
                  "State Radio",
        "confidence": "official"
    },
    "Tennessee": {
        "agency": "Tennessee Highway Patrol",
        "system": "ten",
        "codes": {
            "10-10": "out of service, subject to call",
            "10-12": "officials or visitors present",
            "10-14": "convoy or escort",
            "10-15": "prisoner in custody",
            "10-52A": "armed robbery",
            "10-56": "prowler",
            "10-57": "overweight truck",
            "10-58": "public drunk",
            "10-59": "fight",
            "10-61": "child abuse or neglect",
            "10-62": "corpse",
        },
        "note": "Tennessee runs an extended set with letter suffixes on some "
                "codes for the specific offence.",
        "source": 'Tennessee Highway Patrol 10-code reference and the RadioReference Tennessee Highway Patrol wiki',
        "confidence": 'corroborated',
    },
    "Texas": {
        "agency": "Texas Department of Public Safety",
        "system": "ten",
        "codes": {
            "10-9": "say again",
            "10-10": "negative",
            "10-17": "en route",
            "10-22": "disregard",
            "10-24": "assignment complete",
            "10-30": "danger, caution",
            "10-38": "traffic stop",
            "10-50": "traffic accident",
            "10-71": "officer needs assistance",
            "10-80": "in pursuit",
        },
        "note": "Texas 10-50 is a crash. Be aware that in Louisiana the same "
                "number means an officer down.",
        "source": 'Texas DPS 10-code study sets and Texas police code guides',
        "confidence": 'corroborated',
    },
    "Utah": {
        "agency": "Utah Highway Patrol",
        "system": "signal",
        "codes": {
            "Code 1": "expedite, no lights or siren",
            "Code 3": "lights and siren",
            "Code 4": "situation is under control",
            "Code 5": "surveillance",
        },
        "note": "No statewide 10-code list in Utah. The response Code numbers are "
                "the part everyone shares; much traffic is plain language.",
        "source": 'RadioReference Utah state public service 10-codes; Utah has no mandated statewide list and the published visor card is dated',
        "confidence": 'single',
    },
    "Vermont": {
        "agency": "Vermont State Police",
        "system": "apco",
        "codes": {},
        "note": "Vermont runs the APCO set.",
        "source": 'Vermont police code guide, which records the APCO set',
        "confidence": 'single',
    },
    "Virginia": {
        "agency": "Virginia State Police",
        "system": "plain",
        "codes": {"10-4": "acknowledged"},
        "note": "Virginia State Police converted to plain English on 1 November "
                "2006 for interoperability and kept only 10-4. Speak plainly.",
        "source": 'NPR and Fox News reporting on Virginia State Police converting to plain language on 1 November 2006',
        "confidence": 'corroborated',
    },
    "Washington": {
        "agency": "Washington State Patrol",
        "system": "apco",
        "codes": {},
        "note": "No distinct statewide set confirmed; stay with the common codes.",
        "source": 'no statewide patrol list located',
        "confidence": 'default',
    },
    "West Virginia": {
        "agency": "West Virginia State Police",
        "system": "ten",
        "codes": {
            "10-11": "on duty",
            "10-17": "en route",
            "10-18": "urgent, be quick",
            "10-19": "in contact",
        },
        "note": "West Virginia uses 10-17 for en route rather than meet the "
                "complainant.",
        "source": 'West Virginia radio code references',
        "confidence": 'single',
    },
    "Wisconsin": {
        "agency": "Wisconsin State Patrol",
        "system": "ten",
        "codes": {
            "10-23": "arrived, on scene",
            "10-26": "subject detained",
            "10-29": "warrant check only",
            "10-32": "person with a gun",
            "10-33": "emergency",
            "10-50": "crash, property damage, injury or fatal",
            "10-55": "impaired driver, OWI",
            "10-57": "hit and run crash",
            "10-75": "status check",
            "10-76": "en route",
            "10-78": "officer needs assistance",
            "10-80": "pursuit or chase in progress",
            "10-87": "traffic stop",
            "10-95": "subject in custody, under arrest",
            "10-96": "mentally disturbed person",
            "10-97": "radio or signal test",
            "10-99": "warrant",
        },
        "note": "Wisconsin says OWI, not DWI. A stop is 10-87, a pursuit 10-80, "
                "and 10-97 is only a radio test, never an arrival.",
        "source": "Wisconsin State Patrol WSP 10 Code List (obtained by FOIA, "
                  "published by the ACLU)",
        "confidence": "official"
    },
    "Wyoming": {
        "agency": "Wyoming Highway Patrol",
        "system": "apco",
        "codes": {},
        "note": "Wyoming has largely moved off 10-codes; what remains follows the "
                "common set. Prefer plain language.",
        "source": 'RadioReference discussion indicating the patrol has largely moved off ten codes',
        "confidence": 'default',
    },
}

# How firmly the bot may assert a state's codes. A thinly sourced entry is
# still useful, but the AI is told to follow the unit rather than correct them.
_CONFIDENCE_TAIL = {
    "official": "",
    "corroborated": "",
    "single": " This set is from a single reference, so if a unit uses a "
              "different code, follow their lead rather than correcting them.",
    "default": " Nothing state specific is on record here, so mirror whatever "
               "codes the units use and stay consistent.",
}

_SYSTEM_LEAD = {
    "ten": "{agency} uses its own 10-codes. The ones that matter on the air:",
    "apco": "{agency} uses the common 10-codes, with nothing state specific "
            "on record.",
    "signal": "{agency} does not run standard 10-codes. What they say instead:",
    "plain": "{agency} has moved to plain language.",
}


def state_entry(state):
    return STATE_CODES.get(state)


def state_code_block(state):
    """The radio-code paragraph handed to the AI for one state, or "" when the
    state is not in the table."""
    entry = STATE_CODES.get(state)
    if not entry:
        return ""
    lead = _SYSTEM_LEAD[entry["system"]].format(agency=entry["agency"])
    parts = [lead]
    codes = entry.get("codes") or {}
    if codes:
        parts.append("; ".join(f"{k} {v}" for k, v in codes.items()) + ".")
    note = entry.get("note")
    if note:
        parts.append(note)
    tail = _CONFIDENCE_TAIL.get(entry.get("confidence", "default"), "")
    if tail:
        parts.append(tail.strip())
    return " ".join(parts)


def audit():
    """Every state, how firmly it is sourced and where from. Run this before
    trusting any single entry."""
    rows = []
    for state, e in sorted(STATE_CODES.items()):
        rows.append((e["confidence"], state, e["system"], len(e["codes"]), e["source"]))
    order = {"official": 0, "corroborated": 1, "single": 2, "default": 3}
    rows.sort(key=lambda r: (order[r[0]], r[1]))
    return rows


def states_using_codes():
    """Handy for a quick audit of the table."""
    return {s: e["system"] for s, e in STATE_CODES.items()}
