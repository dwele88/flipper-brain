"""Persistent sensory memory: visual scenes and noise patterns.

Two JSON stores (default ~/.flipper-brain/):

- vision_memory.json — scene signatures the brain has seen, with visit
  counts, per-hour patterns, which mood each scene tended to trigger, and
  when the brain last "noticed" (remarked on) each scene.
- hearing_memory.json — the loudest moments on record, an hourly noise
  profile (average level per hour of day), and engagement tags: moments
  that were followed by the user talking to or commanding the brain.

Both use atomic writes (tmp + rename) like playground/memory.py.
"""
from __future__ import annotations

import json
import os
import threading
import time

DEFAULT_VISION_PATH = os.path.expanduser("~/.flipper-brain/vision_memory.json")
DEFAULT_HEARING_PATH = os.path.expanduser("~/.flipper-brain/hearing_memory.json")


def _load(path: str, template: dict) -> dict:
    try:
        with open(path) as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            merged = dict(template)
            merged.update(data)
            return merged
    except (OSError, json.JSONDecodeError):
        pass
    return dict(template)


def _save(path: str, data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


class VisionMemory:
    """Accumulates knowledge of places the eyes have seen."""

    def __init__(self, path: str = DEFAULT_VISION_PATH):
        self.path = path
        self._lock = threading.Lock()
        self.data = _load(path, {"scenes": {}, "total_frames": 0})

    def record(self, signature: str, mood: str | None) -> dict:
        """Log one sighting. Returns {is_new, visits, recognized}."""
        now = time.time()
        hour = str(time.localtime(now).tm_hour)
        with self._lock:
            self.data["total_frames"] += 1
            sc = self.data["scenes"].get(signature)
            is_new = sc is None
            if is_new:
                sc = {"visits": 0, "first_seen": now, "last_seen": now,
                      "hours": {}, "moods": {}, "last_noticed": 0.0}
                self.data["scenes"][signature] = sc
            sc["visits"] += 1
            sc["last_seen"] = now
            sc["hours"][hour] = sc["hours"].get(hour, 0) + 1
            if mood:
                sc["moods"][mood] = sc["moods"].get(mood, 0) + 1
            # Cap stored scenes so the file can't grow forever.
            if len(self.data["scenes"]) > 500:
                oldest = min(self.data["scenes"],
                             key=lambda k: self.data["scenes"][k]["last_seen"])
                del self.data["scenes"][oldest]
            _save(self.path, self.data)
            return {"is_new": is_new, "visits": sc["visits"],
                    "recognized": sc["visits"] >= 3}

    def should_notice(self, signature: str, cooldown_s: float = 600.0) -> bool:
        """True if the brain may remark on recognizing this scene now."""
        with self._lock:
            sc = self.data["scenes"].get(signature)
            if not sc or sc["visits"] < 3:
                return False
            if time.time() - sc.get("last_noticed", 0.0) < cooldown_s:
                return False
            sc["last_noticed"] = time.time()
            _save(self.path, self.data)
            return True

    def scene_count(self) -> int:
        with self._lock:
            return len(self.data["scenes"])

    def top_scenes(self, n: int = 5) -> list[dict]:
        with self._lock:
            scenes = sorted(self.data["scenes"].items(),
                            key=lambda kv: kv[1]["visits"], reverse=True)
            return [{"signature": k, "visits": v["visits"],
                     "moods": v["moods"]} for k, v in scenes[:n]]


class HearingMemory:
    """Accumulates knowledge of the soundscape around the user."""

    def __init__(self, path: str = DEFAULT_HEARING_PATH):
        self.path = path
        self._lock = threading.Lock()
        self.data = _load(path, {"loudest": [], "hourly": {}, "total_samples": 0})

    def record(self, level: float, bass: float, mid: float, treble: float) -> dict:
        """Log one second of audio. Returns {is_record_loud, quiet_streak_info}."""
        now = time.time()
        hour = str(time.localtime(now).tm_hour)
        with self._lock:
            self.data["total_samples"] += 1
            hh = self.data["hourly"].setdefault(
                hour, {"samples": 0, "level_sum": 0.0})
            hh["samples"] += 1
            hh["level_sum"] = round(hh["level_sum"] + level, 3)

            is_record = False
            if level >= 0.5:  # only genuinely loud moments make the board
                entry = {"ts": now, "level": round(level, 3),
                         "engaged_after": False}
                self.data["loudest"].append(entry)
                self.data["loudest"].sort(key=lambda e: e["level"], reverse=True)
                self.data["loudest"] = self.data["loudest"][:20]
                is_record = self.data["loudest"][0] is entry
            _save(self.path, self.data)
            return {"is_record_loud": is_record}

    def note_engagement(self) -> None:
        """The user just talked to / commanded the brain — tag recent loud
        moments so the brain learns which sounds precede engagement."""
        with self._lock:
            now = time.time()
            changed = False
            for entry in self.data["loudest"]:
                if now - entry["ts"] <= 120 and not entry["engaged_after"]:
                    entry["engaged_after"] = True
                    changed = True
            if changed:
                _save(self.path, self.data)

    def hourly_profile(self) -> dict:
        """Average noise level per hour of day (0-23) seen so far."""
        with self._lock:
            return {h: round(v["level_sum"] / v["samples"], 3)
                    for h, v in self.data["hourly"].items() if v["samples"]}

    def quietest_hours(self, n: int = 3) -> list[str]:
        prof = self.hourly_profile()
        ranked = sorted(prof.items(), key=lambda kv: kv[1])
        return [h for h, _ in ranked[:n] if prof[h] < 0.25]

    def loudest_moments(self, n: int = 5) -> list[dict]:
        with self._lock:
            return [dict(e) for e in self.data["loudest"][:n]]
