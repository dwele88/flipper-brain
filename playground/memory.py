"""Persistent memory: what the brain did, when, and what it learned.

Stored as JSON (default ~/.flipper-brain/memory.json). The decision policy
consults this every cycle: cooldowns, no-immediate-repeat, scan findings,
and preference scores (which behaviors get the most successful runtime).
"""
from __future__ import annotations

import json
import os
import threading
import time

DEFAULT_PATH = os.path.expanduser("~/.flipper-brain/memory.json")


class Memory:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        self._lock = threading.Lock()
        self.data: dict = {"history": [], "prefs": {}, "last_scan": None}
        self.load()

    # -- persistence ------------------------------------------------------

    def load(self) -> None:
        try:
            with open(self.path) as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass

    def save(self) -> None:
        tmp = self.path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(tmp, "w") as fh:
                json.dump(self.data, fh, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            pass

    # -- recording --------------------------------------------------------

    def record(self, mood: str, behavior: str, ok: bool,
               dwell_s: float = 0.0, extra: dict | None = None) -> None:
        with self._lock:
            entry = {"ts": time.time(), "mood": mood, "behavior": behavior,
                     "ok": ok, "dwell_s": round(dwell_s, 1)}
            if extra:
                entry.update(extra)
            self.data["history"].append(entry)
            self.data["history"] = self.data["history"][-500:]
            pref = self.data["prefs"].setdefault(
                behavior, {"runs": 0, "ok": 0, "dwell_s": 0.0})
            pref["runs"] += 1
            pref["dwell_s"] = round(pref["dwell_s"] + dwell_s, 1)
            if ok:
                pref["ok"] += 1
            self.save()

    def record_scan(self, freq_hz: int, protocols: list[str],
                    investigated: bool = False) -> None:
        with self._lock:
            self.data["last_scan"] = {
                "ts": time.time(), "freq_hz": freq_hz,
                "protocols": protocols, "investigated": investigated,
            }
            self.save()

    # -- queries used by the decision policy -------------------------------

    def last_run(self, behavior: str) -> float | None:
        """Timestamp of the most recent run of a behavior (any mood)."""
        with self._lock:
            for entry in reversed(self.data["history"]):
                if entry["behavior"] == behavior:
                    return entry["ts"]
        return None

    def last_behavior(self) -> str | None:
        with self._lock:
            return self.data["history"][-1]["behavior"] if self.data["history"] else None

    def preference_score(self, behavior: str) -> float:
        """Learned preference: successful runs + time spent. Starts at 1.0."""
        pref = self.data["prefs"].get(behavior)
        if not pref:
            return 1.0
        return 1.0 + pref["ok"] + pref["dwell_s"] / 60.0

    def actions_in_last_hour(self) -> int:
        cutoff = time.time() - 3600
        with self._lock:
            return sum(1 for e in self.data["history"] if e["ts"] >= cutoff)

    def last_scan(self) -> dict | None:
        with self._lock:
            return dict(self.data["last_scan"]) if self.data["last_scan"] else None

    @staticmethod
    def ago(ts: float | None) -> str:
        if ts is None:
            return "never"
        s = int(time.time() - ts)
        if s < 60:
            return f"{s}s ago"
        if s < 3600:
            return f"{s // 60}m ago"
        return f"{s // 3600}h ago"
