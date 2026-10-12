"""Perception: best-effort parsers for Flipper CLI state output.

Firmware output formats vary (stock vs Momentum vs Unleashed). Every parser
returns None when it cannot confidently parse — the engine treats unknown
state as unknown, never as zero. Marked best-effort in docs/PLAYGROUND.md.
"""
from __future__ import annotations

import re


def parse_battery(info_power_output: str) -> int | None:
    """Extract battery charge percent from `info power` output."""
    for line in info_power_output.splitlines():
        low = line.lower()
        if "charge" in low or "batt" in low:
            m = re.search(r"(\d{1,3})\s*%", line)
            if m:
                val = int(m.group(1))
                if 0 <= val <= 100:
                    return val
            m = re.search(r"charge\s*[:=]\s*(\d{1,3})", low)
            if m:
                val = int(m.group(1))
                if 0 <= val <= 100:
                    return val
    return None


def parse_storage_free(storage_info_output: str) -> str | None:
    """Extract a human free-space snippet from `storage info /ext` output."""
    for line in storage_info_output.splitlines():
        low = line.lower()
        if "free" in low:
            m = re.search(r"free\D*([\d.]+\s*[kmg]?i?b)", low)
            if m:
                return m.group(1).strip()
            return line.strip()[:80]
    return None


def parse_running_app(loader_info_output: str) -> str | None:
    """Extract the currently running app name from `loader info` output."""
    for line in loader_info_output.splitlines():
        low = line.lower()
        if "app" in low and ("run" in low or "open" in low or "active" in low):
            m = re.search(r'["\']([^"\']+)["\']', line)
            if m:
                return m.group(1)
            m = re.search(r"(?:running|open|active)\s*[:=]?\s*([A-Za-z0-9_.\- ]+)", low)
            if m:
                return m.group(1).strip()
    return None


def parse_uptime(uptime_output: str) -> str | None:
    """Return the raw uptime line (format varies too much to normalize)."""
    line = uptime_output.strip().splitlines()
    return line[0][:80] if line and line[0].strip() else None


def extract_protocols(scan_output: str) -> list[str]:
    """Best-effort: pull protocol names from `subghz rx` decoded output lines.

    RX output prints a block per decoded signal, usually containing the
    protocol name (e.g. Princeton, Nice, CAME). We collect distinct
    capitalized tokens from lines that look like decodes. Passive only —
    this never transmits anything.
    """
    found: list[str] = []
    for line in scan_output.splitlines():
        s = line.strip()
        if not s or len(s) > 60:
            continue
        # Decode lines tend to mention a protocol; grab CamelCase tokens.
        for tok in re.findall(r"\b[A-Z][A-Za-z0-9_]{2,}\b", s):
            if tok not in ("Press", "Serial", "Flipper") and tok not in found:
                found.append(tok)
        if len(found) >= 8:
            break
    return found


def sense(flipper) -> dict:
    """Query real device state. Never raises — unknown fields stay None."""
    state: dict = {"battery_pct": None, "storage_free": None,
                   "running_app": None, "uptime": None, "reachable": False}
    try:
        out = flipper.send("info power", timeout=8)
        state["battery_pct"] = parse_battery(out)
        state["reachable"] = True
    except Exception:
        return state
    try:
        state["storage_free"] = parse_storage_free(
            flipper.send("storage info /ext", timeout=8))
    except Exception:
        pass
    try:
        state["running_app"] = parse_running_app(
            flipper.send("loader info", timeout=8))
    except Exception:
        pass
    try:
        state["uptime"] = parse_uptime(flipper.send("uptime", timeout=8))
    except Exception:
        pass
    return state
