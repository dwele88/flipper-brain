"""EXPLORER mood: passive sensing only. Listens on SubGHz / IR / RFID,
scans 1-Wire and I2C. RX ONLY — never transmits, never replays, never
touches rolling codes. If a scan hears something, the next decision
investigates it (longer listen, protocol identification from RX output)."""
from __future__ import annotations

from playground.sense import extract_protocols

LABEL = "Explorer"
EMOJI = "🔭"
DESCRIPTION = ("Curious explorer. Passively listens on radio bands and scans "
               "wired buses. RX only — it never transmits anything.")


def _scan(flipper, cmd, seconds, freq_hz=None):
    out = flipper.send(cmd, timeout=seconds + 15, stop_after=seconds)
    protos = extract_protocols(out)
    return out, protos


def b_scan_433(flipper, ctx):
    out, protos = _scan(flipper, "subghz rx 433920000 0", 8, 433920000)
    heard = f"heard {', '.join(protos)}" if protos else "band was quiet"
    return {"ok": True, "detail": f"listened on 433.92 MHz for 8s — {heard}",
            "event": "curious", "dwell_s": 8,
            "extra": {"freq_hz": 433920000, "protocols": protos}}


def b_scan_868(flipper, ctx):
    out, protos = _scan(flipper, "subghz rx 868350000 0", 8, 868350000)
    heard = f"heard {', '.join(protos)}" if protos else "band was quiet"
    return {"ok": True, "detail": f"listened on 868.35 MHz for 8s — {heard}",
            "event": "curious", "dwell_s": 8,
            "extra": {"freq_hz": 868350000, "protocols": protos}}


def b_ir_listen(flipper, ctx):
    out = flipper.send("ir rx", timeout=23, stop_after=8)
    saw = "caught IR activity" if out.strip() else "no IR seen"
    return {"ok": True, "detail": f"listened for infrared 8s — {saw}",
            "event": "curious", "dwell_s": 8}


def b_rfid_listen(flipper, ctx):
    out = flipper.send("rfid read", timeout=25, stop_after=10)
    saw = "card detected" if out.strip() else "no card presented"
    detail = f"waited for an RFID card 10s — {saw}"
    if out.strip():
        detail += f" ({out.strip().splitlines()[0][:60]})"
    return {"ok": True, "detail": detail, "event": "curious", "dwell_s": 10}


def b_onewire_scan(flipper, ctx):
    out = flipper.send("onewire search", timeout=20)
    found = "devices found" if out.strip() and "not" not in out.lower()[:80] else "nothing found"
    return {"ok": True, "detail": f"scanned the 1-Wire bus — {found}",
            "event": "curious", "dwell_s": 2}


def b_i2c_scan(flipper, ctx):
    out = flipper.send("i2c", timeout=30, stop_after=12)
    return {"ok": True, "detail": "scanned the I2C bus for attached devices",
            "event": "curious", "dwell_s": 12}


def b_investigate_signal(flipper, ctx):
    """Follow-up: a previous scan heard something — listen longer on the
    same frequency and pull protocol details from the RX output."""
    mem = ctx["memory"]
    last = mem.last_scan()
    if not last or not last.get("protocols"):
        return {"ok": False, "detail": "nothing to investigate (no prior signal)",
                "event": None, "dwell_s": 0}
    freq = last["freq_hz"]
    out, protos = _scan(flipper, f"subghz rx {freq} 0", 20, freq)
    protos = protos or last["protocols"]
    return {"ok": True,
            "detail": (f"investigated {freq/1e6:.2f} MHz for 20s — "
                       f"protocols seen: {', '.join(protos)}"),
            "event": "curious", "dwell_s": 20,
            "extra": {"freq_hz": freq, "protocols": protos, "investigated": True}}


def b_library_spotlight(flipper, ctx):
    """Spotlight a random SubGHz capture from the library as inspiration —
    passive reference only, never transmitted.

    The library tree fetch can hit the network (up to 60s timeout), which
    must never stall the sense-decide-act loop: run it in a worker thread
    and give up gracefully after 10s."""
    import concurrent.futures
    from bridge import library as lib
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        try:
            hits = ex.submit(lib.search, ".sub", 200).result(timeout=10)
        except concurrent.futures.TimeoutError:
            return {"ok": False, "detail": "library fetch timed out — skipping",
                    "event": None, "dwell_s": 0}
        except lib.LibraryError as exc:
            return {"ok": False, "detail": f"library unreachable ({exc})",
                    "event": None, "dwell_s": 0}
    finally:
        # Don't wait for a hung network fetch; the worker dies on its own.
        ex.shutdown(wait=False, cancel_futures=True)
    if not hits:
        return {"ok": False, "detail": "no captures found in library",
                "event": None, "dwell_s": 0}
    import random as _r
    pick = _r.choice(hits)
    name = pick["path"].split("/")[-1]
    return {"ok": True,
            "detail": (f"library has a capture called '{name}' — wave your own "
                       "remote nearby and compare what you hear"),
            "event": "curious", "dwell_s": 1}


BEHAVIORS = [
    {"name": "scan_433", "tags": {"radio"}, "cooldown": 300, "run": b_scan_433},
    {"name": "scan_868", "tags": {"radio"}, "cooldown": 300, "run": b_scan_868},
    {"name": "ir_listen", "tags": {"quiet", "low_power"}, "cooldown": 300,
     "run": b_ir_listen},
    {"name": "rfid_listen", "tags": {"quiet", "low_power"}, "cooldown": 300,
     "run": b_rfid_listen},
    {"name": "onewire_scan", "tags": {"quiet", "low_power"}, "cooldown": 600,
     "run": b_onewire_scan},
    {"name": "i2c_scan", "tags": {"quiet", "low_power"}, "cooldown": 600,
     "run": b_i2c_scan},
    # investigate has no cooldown: it fires once per uninvestigated finding,
    # gated by the engine on memory.last_scan.
    {"name": "investigate_signal", "tags": {"radio"}, "cooldown": 60,
     "run": b_investigate_signal},
    {"name": "library_spotlight", "tags": {"quiet", "low_power"}, "cooldown": 600,
     "run": b_library_spotlight},
]
