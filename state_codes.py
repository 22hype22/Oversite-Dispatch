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
            "10-31": "hit and run",
            "10-33": "emergency, maximum priority, all other units keep radio silence",
            "10-38": "investigate suspicious vehicle",
            "10-39": "stopping suspicious vehicle",
        },
        "note": "Set by the Alabama Criminal Justice Information Center in state "
                "regulation. The double zero call is the one that clears the air.",
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
    },
    "Arkansas": {
        "agency": "Arkansas State Police",
        "system": "apco",
        "codes": {},
        "note": "Arkansas agencies that use codes generally follow the state "
                "police, who stay close to the common set.",
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
    },
    "Colorado": {
        "agency": "Colorado State Patrol",
        "system": "apco",
        "codes": {},
        "note": "Colorado State Patrol uses the expanded APCO set. Troopers open "
                "a transmission by naming the dispatch centre, then their call sign.",
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
    },
    "Florida": {
        "agency": "Florida Highway Patrol",
        "system": "signal",
        "codes": {
            "Signal 0": "officer needs help, emergency",
            "Signal 4": "accident",
            "Signal 7": "dead person",
            "Signal 9": "stolen vehicle",
            "Signal 20": "situation under control",
            "10-15": "prisoner in custody",
            "10-18": "complete assignment quickly",
            "10-20": "location",
        },
        "note": "The highway patrol and most sheriffs run signals; many city "
                "departments use 10-codes instead. Florida has no single "
                "statewide set, so follow whichever the unit uses.",
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
    },
    "Hawaii": {
        "agency": "Hawaii county police departments",
        "system": "ten",
        "codes": {"10-19": "traffic accident"},
        "note": "Hawaii has no state police force; the four county departments "
                "each run their own set and the fire service has moved to plain "
                "language. Stay close to the common codes.",
    },
    "Idaho": {
        "agency": "Idaho State Police",
        "system": "signal",
        "codes": {
            "Code 4": "the trooper is okay",
            "Code 6 Mary": "misdemeanor hit",
            "Code 6 Charles": "criminal history hit",
        },
        "note": "Idaho leans on Code numbers and letter suffixes for record hits "
                "rather than a distinct 10-code set.",
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
    },
    "Kansas": {
        "agency": "Kansas Highway Patrol",
        "system": "apco",
        "codes": {},
        "note": "The highway patrol uses the standard set; many local agencies "
                "have moved to plain speech.",
    },
    "Kentucky": {
        "agency": "Kentucky State Police",
        "system": "apco",
        "codes": {},
        "note": "No distinct statewide set confirmed; stay with the common codes.",
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
    },
    "Maryland": {
        "agency": "Maryland State Police",
        "system": "plain",
        "codes": {},
        "note": "Maryland State Police dropped 10-codes on 1 February 2012 and "
                "run plain English, so troopers do not say 10-4. Speak in plain "
                "language, though older hands still slip a code in.",
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
    },
    "North Carolina": {
        "agency": "North Carolina State Highway Patrol",
        "system": "ten",
        "codes": {
            "10-20": "location",
            "10-33": "help me quick",
            "10-71": "improper use of radio",
            "10-72": "prisoner in custody",
            "10-73": "mental subject",
            "10-74": "prison or jail break",
            "10-75": "wanted or stolen",
        },
        "note": "The patrol calls them ten signals and publishes them as HP-979. "
                "10-33 is the emergency call here.",
    },
    "North Dakota": {
        "agency": "North Dakota Highway Patrol",
        "system": "apco",
        "codes": {},
        "note": "No distinct statewide set confirmed; the patrol works through "
                "State Radio on the common codes.",
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
    },
    "South Carolina": {
        "agency": "South Carolina Highway Patrol",
        "system": "apco",
        "codes": {},
        "note": "No distinct statewide patrol set confirmed; county systems vary "
                "widely, so stay with the common codes.",
    },
    "South Dakota": {
        "agency": "South Dakota Highway Patrol",
        "system": "ten",
        "codes": {
            "10-3": "stand by",
            "10-10": "out of service, subject to call",
            "10-23": "arrived on the scene",
            "10-24": "assignment completed",
            "10-82": "stopping suspicious vehicle",
        },
        "note": "South Dakota 10-3 is stand by, not stop transmitting.",
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
    },
    "Vermont": {
        "agency": "Vermont State Police",
        "system": "apco",
        "codes": {},
        "note": "Vermont runs the APCO set.",
    },
    "Virginia": {
        "agency": "Virginia State Police",
        "system": "plain",
        "codes": {"10-4": "acknowledged"},
        "note": "Virginia State Police converted to plain English on 1 November "
                "2006 for interoperability and kept only 10-4. Speak plainly.",
    },
    "Washington": {
        "agency": "Washington State Patrol",
        "system": "apco",
        "codes": {},
        "note": "No distinct statewide set confirmed; stay with the common codes.",
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
    },
    "Wisconsin": {
        "agency": "Wisconsin State Patrol",
        "system": "ten",
        "codes": {
            "10-23": "arrived on scene",
            "10-46": "motorist assist or disabled vehicle",
            "10-49": "traffic signal out",
            "10-68": "permission to leave the patrol area",
            "10-94": "drag racing",
            "10-95": "subject in custody, under arrest",
            "10-96": "mentally disturbed person",
            "10-97": "radio or signal test",
            "10-98": "prison or jail break",
            "10-99": "warrant",
        },
        "note": "Wisconsin 10-97 is only a radio test, and a warrant comes back "
                "as 10-99.",
    },
    "Wyoming": {
        "agency": "Wyoming Highway Patrol",
        "system": "apco",
        "codes": {},
        "note": "Wyoming has largely moved off 10-codes; what remains follows the "
                "common set. Prefer plain language.",
    },
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
    return " ".join(parts)


def states_using_codes():
    """Handy for a quick audit of the table."""
    return {s: e["system"] for s, e in STATE_CODES.items()}
