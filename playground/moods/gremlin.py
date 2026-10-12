"""GREMLIN mood: mischievous and playful. LED chaos, silly sounds, button
wiggles, and games from the user's allowlist. Nothing transmitted, nothing
destructive."""
from __future__ import annotations

import random
import time

LABEL = "Gremlin"
EMOJI = "😈"
DESCRIPTION = ("Mischievous little gremlin. Flashes the LEDs, plays silly "
               "tunes, wiggles the buttons, and fires up games from your "
               "allowlist.")


def _led(flipper, r, g, b):
    flipper.send(f"led r {r}", timeout=5)
    flipper.send(f"led g {g}", timeout=5)
    flipper.send(f"led b {b}", timeout=5)


def b_led_chaos(flipper, ctx):
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
              (255, 0, 255), (0, 255, 255)]
    seq = random.sample(colors, 4)
    for r, g, b in seq:
        _led(flipper, r, g, b)
        time.sleep(0.25)
    _led(flipper, 0, 0, 0)
    names = { (255,0,0): "red", (0,255,0): "green", (0,0,255): "blue",
              (255,255,0): "yellow", (255,0,255): "purple", (0,255,255): "cyan" }
    shown = ", ".join(names[c] for c in seq)
    return {"ok": True, "detail": f"flashed the LED {shown}",
            "event": "happy", "dwell_s": 1.5}


def b_silly_tune(flipper, ctx):
    notes = ["g4", "e4", "c4", "e4", "g4", "c5", "g4", "e4"]
    random.shuffle(notes)
    for n in notes[:6]:
        flipper.send(f"buzzer note {n} 180ms", timeout=5)
        time.sleep(0.05)
    return {"ok": True, "detail": f"played a silly 6-note tune ({' '.join(notes[:6])})",
            "event": "happy", "dwell_s": 1.5}


def b_vibro_burst(flipper, ctx):
    for _ in range(3):
        flipper.send("vibro 1", timeout=5)
        time.sleep(0.3)
        flipper.send("vibro 0", timeout=5)
        time.sleep(0.2)
    return {"ok": True, "detail": "did 3 vibration bursts",
            "event": "happy", "dwell_s": 1.5}


def b_desktop_wiggle(flipper, ctx):
    moves = random.sample(["up", "down", "left", "right"], 3)
    for key in moves:
        flipper.send(f"input send {key} press", timeout=5)
        flipper.send(f"input send {key} short", timeout=5)
        flipper.send(f"input send {key} release", timeout=5)
        time.sleep(0.2)
    return {"ok": True, "detail": f"wiggled the buttons ({', '.join(moves)})",
            "event": "happy", "dwell_s": 1.5}


def b_neofetch(flipper, ctx):
    out = flipper.send("neofetch", timeout=10)
    first = out.strip().splitlines()[0][:60] if out.strip() else "no output"
    return {"ok": True, "detail": f"ran neofetch ({first})",
            "event": "curious", "dwell_s": 1.0}


def b_play_game(flipper, ctx):
    allow = ctx["config"].get("game_allowlist") or []
    if not allow:
        return {"ok": False,
                "detail": "no games in game_allowlist (see config.yaml) — skipping",
                "event": None, "dwell_s": 0}
    mem = ctx["memory"]
    # Don't repeat the game it just played: pick least-recently-played.
    scored = sorted(allow, key=lambda g: mem.last_run(f"game:{g}") or 0)
    game = scored[0]
    flipper.send(f"loader open {game}", timeout=10)
    dwell = random.uniform(30, 75)
    time.sleep(dwell)
    flipper.send("loader close", timeout=10)
    return {"ok": True, "detail": f"played {game} for {int(dwell)}s",
            "event": "happy", "dwell_s": dwell,
            "extra": {"game": game}}


BEHAVIORS = [
    {"name": "led_chaos", "tags": {"low_power"}, "cooldown": 120, "run": b_led_chaos},
    {"name": "silly_tune", "tags": {"noisy"}, "cooldown": 300, "run": b_silly_tune},
    {"name": "vibro_burst", "tags": {"noisy"}, "cooldown": 300, "run": b_vibro_burst},
    {"name": "desktop_wiggle", "tags": {"low_power", "quiet"}, "cooldown": 180,
     "run": b_desktop_wiggle},
    {"name": "neofetch", "tags": {"low_power", "quiet"}, "cooldown": 600,
     "run": b_neofetch},
    {"name": "play_game", "tags": set(), "cooldown": 900, "run": b_play_game},
]
