"""GHOST mood: drifts through the device like a curious ghost. Tours the
installed apps, peeks inside allowlisted ones, wanders the filesystem,
and narrates what it finds. Read-only except opening/closing apps."""
from __future__ import annotations

import random
import time

LABEL = "Ghost"
EMOJI = "👻"
DESCRIPTION = ("Friendly ghost. Tours your installed apps, peeks inside the "
               "ones you allowlisted, and wanders the filesystem telling you "
               "what's there.")


def _app_names(flipper) -> list[str]:
    out = flipper.send("loader list", timeout=15)
    names = []
    for line in out.splitlines():
        s = line.strip()
        if s and not s.startswith((">", ":")) and len(s) < 48:
            # loader list prints one app per line; skip headers
            if " " not in s or "_" in s:
                names.append(s.split()[0])
    return names


def b_tour_apps(flipper, ctx):
    names = _app_names(flipper)
    if not names:
        return {"ok": False, "detail": "couldn't enumerate apps",
                "event": None, "dwell_s": 0}
    pick = random.choice(names)
    return {"ok": True,
            "detail": f"drifted past {len(names)} installed apps — paused at '{pick}'",
            "event": "curious", "dwell_s": 2, "extra": {"app": pick}}


def b_peek_app(flipper, ctx):
    allow = ctx["config"].get("app_tour_allowlist") or []
    if not allow:
        return {"ok": False,
                "detail": "no apps in app_tour_allowlist (see config.yaml) — skipping peek",
                "event": None, "dwell_s": 0}
    mem = ctx["memory"]
    scored = sorted(allow, key=lambda a: mem.last_run(f"peek:{a}") or 0)
    app = scored[0]
    flipper.send(f"loader open {app}", timeout=10)
    time.sleep(8)
    flipper.send("loader close", timeout=10)
    return {"ok": True, "detail": f"peeked inside '{app}' for 8s, then drifted away",
            "event": "happy", "dwell_s": 8, "extra": {"app": app}}


def b_loader_report(flipper, ctx):
    out = flipper.send("loader info", timeout=10)
    first = out.strip().splitlines()[0][:70] if out.strip() else "no output"
    return {"ok": True, "detail": f"checked what's running ({first})",
            "event": "curious", "dwell_s": 1}


def b_storage_wander(flipper, ctx):
    dirs = ["/ext", "/ext/apps", "/ext/subghz", "/ext/nfc", "/ext/infrared",
            "/ext/badusb", "/ext/music"]
    d = random.choice(dirs)
    out = flipper.send(f"storage list {d}", timeout=12)
    n = len([l for l in out.splitlines() if l.strip()])
    return {"ok": True, "detail": f"wandered through {d} — {n} entries",
            "event": "curious", "dwell_s": 1.5}


def b_uptime_tale(flipper, ctx):
    up = flipper.send("uptime", timeout=8).strip().splitlines()
    up = up[0][:60] if up and up[0].strip() else "unknown"
    free = flipper.send("free", timeout=8).strip().splitlines()
    free = free[0][:60] if free and free[0].strip() else "unknown"
    return {"ok": True,
            "detail": f"this device has been awake {up}; heap says {free}",
            "event": "happy", "dwell_s": 1.5}


def b_library_tour(flipper, ctx):
    """Browse the UberGuidoZ library's app collection and spotlight one."""
    from bridge import library as lib
    try:
        files = lib.list_category("Applications")
    except lib.LibraryError as exc:
        return {"ok": False, "detail": f"library unreachable ({exc})",
                "event": None, "dwell_s": 0}
    faps = [f for f in files if f["name"].lower().endswith(".fap")]
    if not faps:
        return {"ok": False, "detail": "no apps found in library cache",
                "event": None, "dwell_s": 0}
    pick = random.choice(faps)
    name = pick["name"]
    try:
        on_device = name.replace(".fap", "").lower() in flipper.send(
            "loader list", timeout=15).lower()
    except Exception:
        on_device = False
    where = "already on your Flipper" if on_device else \
        "not installed — grab it from the Library tab"
    return {"ok": True,
            "detail": f"library spotlight: '{name}' ({where})",
            "event": "curious", "dwell_s": 2,
            "extra": {"library_app": name}}


BEHAVIORS = [
    {"name": "tour_apps", "tags": {"quiet", "low_power"}, "cooldown": 300,
     "run": b_tour_apps},
    {"name": "peek_app", "tags": {"quiet"}, "cooldown": 900, "run": b_peek_app},
    {"name": "loader_report", "tags": {"quiet", "low_power"}, "cooldown": 600,
     "run": b_loader_report},
    {"name": "storage_wander", "tags": {"quiet", "low_power"}, "cooldown": 300,
     "run": b_storage_wander},
    {"name": "uptime_tale", "tags": {"quiet", "low_power"}, "cooldown": 900,
     "run": b_uptime_tale},
    {"name": "library_tour", "tags": {"quiet", "low_power"}, "cooldown": 600,
     "run": b_library_tour},
]
