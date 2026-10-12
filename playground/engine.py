"""Playground engine: a genuine sense-decide-act loop.

Every cycle:
  SENSE   — query real Flipper state (battery, storage, running app, uptime).
  DECIDE  — mood policy consumes state + memory: battery interlocks, quiet
            hours, cooldowns, no-immediate-repeat, explorer follow-ups on
            real scan findings, preference-weighted choice.
  ACT     — run the behavior, measure what happened, persist to memory.

Thought lines are composed from the actual inputs to each decision
(state + memory + behavior detail). Nothing is canned.
"""
from __future__ import annotations

import datetime
import random
import threading
import time
from collections import deque

from playground.memory import Memory, DEFAULT_PATH
from playground.moods import MOODS
from playground.sense import sense


class Playground:
    def __init__(self, flipper, cfg: dict):
        self.flipper = flipper
        self.cfg = cfg or {}
        self.memory = Memory(self.cfg.get("memory_path", DEFAULT_PATH))
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thoughts: deque[dict] = deque(maxlen=100)
        self._cursor = 0
        self._mood: str | None = None
        self._interval = 20
        self._last_event: str | None = None
        self._cycle = 0
        self._gen = 0  # incremented on every start(); stale threads exit

    # -- control ----------------------------------------------------------

    def start(self, mood: str, interval: int = 20) -> None:
        if mood not in MOODS:
            raise ValueError(f"unknown mood {mood!r}; choose from {sorted(MOODS)}")
        self.stop()
        self._gen += 1
        self._mood = mood
        # Clamp: at least 5s, at most a day (huge values overflow Event.wait).
        self._interval = min(86400, max(5, int(interval)))
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="playground",
                                        args=(self._gen,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        t, self._thread = self._thread, None
        if t and t.is_alive():
            t.join(timeout=8)
        with self._lock:
            if self._mood:
                self._mood = None

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self._thread is not None and self._thread.is_alive(),
                "mood": self._mood,
                "interval": self._interval,
                "cycle": self._cycle,
                "last_event": self._last_event,
            }

    def describe_moods(self) -> dict:
        return {k: {"label": v["label"], "emoji": v["emoji"],
                    "description": v["description"]}
                for k, v in MOODS.items()}

    # -- thoughts ----------------------------------------------------------

    def _think(self, text: str, event: str | None = None) -> None:
        with self._lock:
            self._cursor += 1
            self._thoughts.append({
                "id": self._cursor,
                "ts": time.time(),
                "mood": self._mood,
                "text": text,
                "event": event,
            })
            if event:
                self._last_event = event

    def thoughts_since(self, since: int):
        with self._lock:
            items = [t for t in self._thoughts if t["id"] > since]
            return items, self._cursor

    # -- sense-decide-act ----------------------------------------------------

    def _all_behaviors(self):
        pool = []
        for key, mood in MOODS.items():
            for b in mood["behaviors"]:
                pool.append((key, b))
        return pool

    def _quiet_now(self) -> bool:
        qh = self.cfg.get("quiet_hours") or {}
        if not qh.get("enabled"):
            return False
        hour = datetime.datetime.now().hour
        start, end = int(qh.get("start", 23)), int(qh.get("end", 7))
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end

    def _decide(self, state: dict):
        """Returns (behavior_dict, decision_notes). Notes feed the thought."""
        mood_key = self._mood
        # stop() may clear _mood while a slow sense()/behavior is still
        # finishing after join() timed out — stand down gracefully, never crash.
        if mood_key is None:
            return None, ["brain was stopped mid-cycle — standing down"]
        if MOODS[mood_key].get("blend"):
            pool = self._all_behaviors()
        else:
            pool = [(mood_key, b) for b in MOODS[mood_key]["behaviors"]]

        notes: list[str] = []
        battery = state.get("battery_pct")
        low_at = int(self.cfg.get("battery_low_pct", 25))
        crit_at = int(self.cfg.get("battery_critical_pct", 12))

        # Hard interlock: critical battery stops the brain entirely.
        if battery is not None and battery <= crit_at:
            return None, [f"battery at {battery}% (critical ≤{crit_at}%) — "
                          "shutting down to protect the cell"]

        cands = pool
        if battery is not None and battery <= low_at:
            cands = [(m, b) for m, b in cands if "low_power" in b["tags"]]
            notes.append(f"battery at {battery}% — low-power only")
        if self._quiet_now():
            cands = [(m, b) for m, b in cands if "quiet" in b["tags"]]
            notes.append("quiet hours — silent behaviors only")
        if not cands:  # filters were too strict; fall back to quietest options
            cands = [(m, b) for m, b in pool if "quiet" in b["tags"]] or pool
            notes.append("filters too strict — fell back to gentlest options")

        # Rate limit: max actions per hour.
        max_hr = int(self.cfg.get("max_actions_per_hour", 30))
        if self.memory.actions_in_last_hour() >= max_hr:
            return None, [f"rate limit reached ({max_hr}/hour) — resting this cycle"]

        # Explorer: an uninvestigated real finding takes priority.
        if mood_key in ("explorer", "surprise"):
            last = self.memory.last_scan()
            if last and last.get("protocols") and not last.get("investigated"):
                inv = next((x for x in cands if x[1]["name"] == "investigate_signal"), None)
                if inv:
                    notes.append(f"following up on {', '.join(last['protocols'])} "
                                 f"heard at {last['freq_hz']/1e6:.2f} MHz")
                    return inv, notes

        # Cooldowns + no immediate repeat, from real memory.
        now = time.time()
        fresh = []
        for item in cands:
            last_run = self.memory.last_run(item[1]["name"])
            cd = item[1].get("cooldown", 300)
            if last_run and now - last_run < cd:
                continue
            fresh.append(item)
        if fresh:
            cands = fresh
            notes.append("skipped behaviors still cooling down")
        last_b = self.memory.last_behavior()
        if last_b and len(cands) > 1:
            non_repeat = [x for x in cands if x[1]["name"] != last_b]
            if non_repeat:
                cands = non_repeat

        # Preference-weighted choice (learned from real run history).
        weights = [self.memory.preference_score(b["name"]) for _, b in cands]
        choice = random.choices(cands, weights=weights, k=1)[0]
        top = max(weights)
        if weights[cands.index(choice)] >= top and len(cands) > 1:
            notes.append(f"leaning on '{choice[1]['name']}' — it scores well")
        return choice, notes

    def _compose_thought(self, mood_key, behavior, result, state, notes) -> str:
        """Every thought is built from actual decision inputs. No canned text."""
        parts: list[str] = []
        b = state.get("battery_pct")
        batt = f"{b}%" if b is not None else "unknown"
        parts.append(f"[batt {batt}]")
        if state.get("running_app"):
            parts.append(f"(app open: {state['running_app']})")
        if notes:
            parts.append(" ".join(notes) + ".")
        parts.append(result["detail"] + ".")
        last = self.memory.last_behavior()
        if last and last != behavior["name"]:
            parts.append(f"Last did '{last}' "
                         f"{Memory.ago(self.memory.last_run(last))}.")
        return " ".join(parts)

    def _loop(self, gen: int) -> None:
        assert self._mood is not None
        mood_key = self._mood
        self._think(f"Waking up in {MOODS[mood_key]['label']} mode…", "curious")
        # gen check: if stop()'s join() timed out and a new generation
        # started, this stale thread exits instead of driving the flipper.
        while not self._stop.is_set() and gen == self._gen:
            self._cycle += 1
            state = sense(self.flipper)
            if not state.get("reachable"):
                self._think("Can't reach the Flipper over serial — retrying next cycle.",
                            None)
                self._stop.wait(self._interval)
                continue
            choice, notes = self._decide(state)
            if choice is None:
                # Interlock or rate limit: say why, then rest or stop.
                self._think(" ".join(notes) + ".", "sleepy")
                if "critical" in " ".join(notes):
                    break
                self._stop.wait(self._interval)
                continue
            src_mood, behavior = choice
            ctx = {"state": state, "memory": self.memory, "config": self.cfg}
            t0 = time.time()
            try:
                result = behavior["run"](self.flipper, ctx)
            except Exception as exc:
                result = {"ok": False, "detail": f"behavior failed ({exc})",
                          "event": None, "dwell_s": 0.0}
            dwell = result.get("dwell_s") or (time.time() - t0)
            extra = result.get("extra") or {}
            self.memory.record(mood_key, behavior["name"], bool(result["ok"]),
                               dwell_s=dwell,
                               extra={"src_mood": src_mood, **extra})
            if extra.get("protocols") is not None and extra.get("freq_hz"):
                self.memory.record_scan(extra["freq_hz"], extra["protocols"],
                                        investigated=bool(extra.get("investigated")))
            thought = self._compose_thought(mood_key, behavior, result, state, notes)
            self._think(thought, result.get("event"))
            self._stop.wait(self._interval)
        self._think("Going to sleep…", "sleepy")
