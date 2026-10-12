"""DJ mood: the little brain becomes a DJ. Plays melodies on the piezo
buzzer, syncs LED color shows, drops vibration beats."""
from __future__ import annotations

import random
import time

LABEL = "DJ"
EMOJI = "🎧"
DESCRIPTION = ("Resident DJ. Plays chiptunes on the buzzer, runs LED light "
               "shows, and drops the occasional vibration beat.")


def _note(flipper, note, dur="220ms"):
    flipper.send(f"buzzer note {note} {dur}", timeout=5)


def _led(flipper, r, g, b):
    flipper.send(f"led r {r}", timeout=5)
    flipper.send(f"led g {g}", timeout=5)
    flipper.send(f"led b {b}", timeout=5)


TWINKLE = ["c4", "c4", "g4", "g4", "a4", "a4", "g4",
           "f4", "f4", "e4", "e4", "d4", "d4", "c4"]
MARY = ["e4", "d4", "c4", "d4", "e4", "e4", "e4",
        "d4", "d4", "d4", "e4", "g4", "g4"]
ODE = ["e4", "e4", "f4", "g4", "g4", "f4", "e4", "d4",
       "c4", "c4", "d4", "e4", "e4", "d4", "d4"]


def _play(flipper, notes, dur="240ms"):
    for n in notes:
        _note(flipper, n, dur)
        time.sleep(0.03)


def b_twinkle(flipper, ctx):
    _play(flipper, TWINKLE)
    return {"ok": True, "detail": f"played Twinkle Twinkle ({len(TWINKLE)} notes)",
            "event": "happy", "dwell_s": 4}


def b_mary(flipper, ctx):
    _play(flipper, MARY)
    return {"ok": True, "detail": f"played Mary Had a Little Lamb ({len(MARY)} notes)",
            "event": "happy", "dwell_s": 4}


def b_ode(flipper, ctx):
    _play(flipper, ODE, "200ms")
    return {"ok": True, "detail": f"played Ode to Joy ({len(ODE)} notes)",
            "event": "happy", "dwell_s": 4}


def b_arpeggio(flipper, ctx):
    base = random.choice([["c4", "e4", "g4", "c5"], ["a3", "c4", "e4", "a4"],
                          ["f3", "a3", "c4", "f4"]])
    for _ in range(3):
        for n in base + base[-2::-1]:
            flipper.send(f"buzzer freq {440} 90ms", timeout=5)
            _note(flipper, n, "120ms")
    return {"ok": True, "detail": f"ran an arpeggio climb ({' '.join(base)})",
            "event": "happy", "dwell_s": 3}


def b_led_sync(flipper, ctx):
    palette = [(255, 0, 128), (0, 200, 255), (128, 0, 255), (0, 255, 128)]
    for _ in range(2):
        for r, g, b in palette:
            _led(flipper, r, g, b)
            time.sleep(0.3)
    _led(flipper, 0, 0, 0)
    return {"ok": True, "detail": "ran a 4-color LED light show (2 rounds)",
            "event": "happy", "dwell_s": 2.5}


def b_beat_drop(flipper, ctx):
    for _ in range(4):
        flipper.send("vibro 1", timeout=5)
        flipper.send("buzzer freq 90 180ms", timeout=5)
        time.sleep(0.35)
        flipper.send("vibro 0", timeout=5)
        time.sleep(0.15)
    return {"ok": True, "detail": "dropped 4 vibration bass hits",
            "event": "happy", "dwell_s": 2.5}


def b_crate_dig(flipper, ctx):
    """Dig a random track out of the library and install it to /ext/music.
    Install-on-demand: the install is reported in the thought log."""
    from bridge import library as lib
    try:
        files = lib.list_category("Music_Player")
    except lib.LibraryError as exc:
        return {"ok": False, "detail": f"library unreachable ({exc})",
                "event": None, "dwell_s": 0}
    tracks = [f for f in files if "/" not in f["path"][len("Music_Player/"):]]
    if not tracks:
        return {"ok": False, "detail": "no tracks in library Music_Player",
                "event": None, "dwell_s": 0}
    pick = random.choice(tracks)
    try:
        res = lib.install(flipper, pick["path"])
    except (lib.LibraryError, Exception) as exc:
        return {"ok": False, "detail": f"couldn't install {pick['name']} ({exc})",
                "event": None, "dwell_s": 0}
    return {"ok": True,
            "detail": (f"dug '{pick['name']}' out of the library and installed it "
                       f"to {res['sd_path']} ({res['bytes']} bytes) — find it in Music"),
            "event": "happy", "dwell_s": 3,
            "extra": {"installed": pick["path"]}}


BEHAVIORS = [
    {"name": "twinkle", "tags": {"noisy"}, "cooldown": 600, "run": b_twinkle},
    {"name": "mary", "tags": {"noisy"}, "cooldown": 600, "run": b_mary},
    {"name": "ode", "tags": {"noisy"}, "cooldown": 600, "run": b_ode},
    {"name": "arpeggio", "tags": {"noisy"}, "cooldown": 300, "run": b_arpeggio},
    {"name": "led_sync", "tags": {"low_power"}, "cooldown": 180, "run": b_led_sync},
    {"name": "beat_drop", "tags": {"noisy"}, "cooldown": 300, "run": b_beat_drop},
    {"name": "crate_dig", "tags": {"quiet", "low_power"}, "cooldown": 900,
     "run": b_crate_dig},
]
