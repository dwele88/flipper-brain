"""Voice command matching for NeuroFlipper — no LLM, no new installs.

Matches a transcript against command patterns and returns
{"reply": str, "action": {...}}. The reply is written in the brain's
personality voice, flavored by the current mood. This is command +
personality-response voice, NOT open conversation — freeform chat needs
an LLM key and is documented as future work in docs/VOICE.md.
"""
from __future__ import annotations

import re

MOOD_WORDS = {
    "gremlin": ["gremlin", "mischief", "chaos", "naughty"],
    "explorer": ["explorer", "curious", "investigate", "scout"],
    "dj": ["dj", "music", "party", "dance", "tunes"],
    "ghost": ["ghost", "spooky", "quiet", "haunt", "stealth"],
    "surprise": ["surprise", "random", "whatever", "anything"],
}

MOOD_FLAVOR = {
    "gremlin": "with a mischievous grin",
    "explorer": "peering through its tiny spyglass",
    "dj": "bobbing to a beat only it can hear",
    "ghost": "in a barely-there whisper",
    "surprise": "vibrating with unpredictable energy",
}


def _flavor(mood: str) -> str:
    return MOOD_FLAVOR.get(mood, "happily")


def interpret(text: str, ctx: dict) -> dict:
    """ctx: {mood, vision, hearing, battery (int|None), reachable (bool),
             library_search (callable|None)}."""
    t = (text or "").strip().lower()
    mood = ctx.get("mood") or "gremlin"
    if not t:
        return {"reply": f"hmm? {_flavor(mood)} — I didn't catch that.",
                "action": None}

    # -- mood switching ---------------------------------------------------
    m = re.search(r"\b(become|go|be|switch to|act like|turn into)\b.*?\b"
                  r"(gremlin|explorer|dj|ghost|surprise)\b", t)
    if not m:
        for mk, words in MOOD_WORDS.items():
            if any(w in t for w in words) and re.search(
                    r"\b(be|go|become|switch|mode|mood)\b", t):
                m = True
                t_mood = mk
                break
        else:
            t_mood = None
    else:
        t_mood = m.group(2)
    if t_mood:
        label = {"gremlin": "Gremlin", "explorer": "Explorer", "dj": "DJ",
                 "ghost": "Ghost", "surprise": "Surprise Me"}[t_mood]
        return {
            "reply": f"ooh, {label} mode — I like it {_flavor(t_mood)}.",
            "action": {"type": "mood", "mood": t_mood},
        }

    # -- playground triggers ----------------------------------------------
    if re.search(r"\b(do something|wake up|surprise me|go play|explore now)\b", t):
        return {
            "reply": f"on it {_flavor(mood)} — one fresh brain cycle, coming up.",
            "action": {"type": "trigger"},
        }
    if re.search(r"\b(go to sleep|stop|shut up|quiet)\b", t):
        return {
            "reply": "fine, fine… powering down the playground. poke me when you miss me.",
            "action": {"type": "stop"},
        }

    # -- device queries ----------------------------------------------------
    if "battery" in t or "charge" in t or "power" in t:
        batt = ctx.get("battery")
        if batt is None:
            detail = ("can't reach the Flipper right now, so I can't check — "
                      "is it plugged in?")
        else:
            detail = f"sitting at {batt}%"
            if batt <= 25:
                detail += " — getting snacky, keep me fed"
        return {"reply": f"battery check {_flavor(mood)}: {detail}.",
                "action": None}

    if re.search(r"what (do you|can you) see|how.*look|describe.*(room|around)", t):
        v = ctx.get("vision")
        if not v:
            return {"reply": f"my eyes are closed right now {_flavor(mood)} — "
                             "open the Eyes tab and I'll take a look.",
                    "action": None}
        b, mo = v.get("brightness", 0), v.get("motion", 0)
        if b < 0.15:
            desc = "it's really dark in here — very ghost-friendly"
        elif b > 0.75:
            desc = "bright! I can practically feel the photons"
        else:
            desc = "decent light, I can make out shapes"
        if mo > 0.5:
            desc += ", and something's moving"
        elif mo > 0.2:
            desc += ", slight movement around"
        else:
            desc += ", all still"
        rec = v.get("recognition")
        if rec and rec.get("recognized"):
            desc += f" — and I've seen this place {rec['visits']} times, I know it"
        return {"reply": f"{desc} {_flavor(mood)}.", "action": None}

    if re.search(r"what.*hear|how.*sound|nois|quiet|loud", t):
        h = ctx.get("hearing")
        if not h:
            return {"reply": f"my ears are off {_flavor(mood)} — open the Eyes tab "
                             "and enable Ears so I can listen.",
                    "action": None}
        lvl = h.get("level", 0)
        if lvl < 0.1:
            desc = "quiet… suspiciously quiet. I like it"
        elif lvl < 0.4:
            desc = "a gentle hum of background noise"
        else:
            desc = "it's pretty loud in here!"
        return {"reply": f"{desc} {_flavor(mood)}.", "action": None}

    if re.search(r"who are you|your name|what are you", t):
        return {"reply": f"I'm the lil brain living in your Flipper {_flavor(mood)} — "
                         "part gremlin, part genius, all dolphin.",
                "action": None}

    # -- library ------------------------------------------------------------
    m = re.search(r"(?:find|search|get|look for)\s+(.+?)\s+(?:app|apps)\b", t)
    if m:
        query = m.group(1).strip()
        search = ctx.get("library_search")
        if not search:
            return {"reply": "the library isn't reachable from here right now.",
                    "action": None}
        try:
            results = search(query)[:5]
        except Exception:
            results = []
        if not results:
            return {"reply": f"dug through the collection {_flavor(mood)} — "
                             f"nothing matching '{query}'.",
                    "action": None}
        names = ", ".join(r.get("path", "?").split("/")[-1] for r in results)
        return {"reply": f"found these in the collection {_flavor(mood)}: {names}. "
                         "say the word and tell me which to install from the Library tab.",
                "action": {"type": "library_results", "query": query,
                           "results": results}}

    # -- fallthrough: playful, honest about limits ---------------------------
    return {
        "reply": f"heard you {_flavor(mood)} — I only understand commands for now "
                 "(moods, actions, battery, what I see/hear, library search). "
                 "real conversation needs a bigger brain — that's on the roadmap.",
        "action": None,
    }
