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
from playground.sense import sense, merge_external
from playground.sense_memory import (VisionMemory, HearingMemory,
                                      DEFAULT_VISION_PATH,
                                      DEFAULT_HEARING_PATH)


class Playground:
    def __init__(self, flipper, cfg: dict):
        self.flipper = flipper
        self.cfg = cfg or {}
        self.memory = Memory(self.cfg.get("memory_path", DEFAULT_PATH))
        self.vision_memory = VisionMemory(
            self.cfg.get("vision_memory_path", DEFAULT_VISION_PATH))
        self.hearing_memory = HearingMemory(
            self.cfg.get("hearing_memory_path", DEFAULT_HEARING_PATH))
        # Phone senses, written by the bridge (dashboard Eyes/Ears screens).
        self._external = {"vision": None, "hearing": None}
        self._ext_lock = threading.Lock()
        self._motion_hist = deque(maxlen=10)
        self._level_hist = deque(maxlen=12)
        self._last_loud_thought = 0.0
        self._wake = threading.Event()
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
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="playground",
                                        args=(self._gen,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()  # wake a sleeping loop so it exits promptly
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

    # -- phone senses + remote brain control -------------------------------

    def set_external(self, kind: str, data: dict | None) -> None:
        """Bridge writes the latest vision/hearing sample here."""
        if kind not in ("vision", "hearing"):
            raise ValueError("kind must be 'vision' or 'hearing'")
        with self._ext_lock:
            self._external[kind] = data

    def external_snapshot(self) -> dict:
        with self._ext_lock:
            return {"vision": self._external["vision"],
                    "hearing": self._external["hearing"]}

    def set_mood(self, mood: str) -> dict:
        """Switch mood now; starts the loop if it wasn't running."""
        if mood not in MOODS:
            raise ValueError(f"unknown mood {mood!r}; choose from {sorted(MOODS)}")
        interval = self._interval if self.status()["running"] else 20
        self.start(mood, interval)
        self._think(f"switching to {MOODS[mood]['label']} mode — your call, boss.",
                    "curious")
        return self.status()

    def trigger(self) -> dict:
        """Wake the loop for one immediate sense→decide→act cycle."""
        if not self.status()["running"]:
            raise RuntimeError("playground is not running — start it first")
        self._wake.set()
        return self.status()

    def speak(self, text: str, event: str | None = "happy") -> dict:
        """Push a brain-voiced line into the thought log (mascot reacts)."""
        text = (text or "").strip()
        if not text:
            raise ValueError("text is required")
        if len(text) > 500:
            text = text[:500]
        self._think(text, event)
        return {"ok": True}

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

    def _sense_hint(self, state: dict):
        """Vision/hearing → (hinted_mood|None, notes).

        The brain never overrides the user's chosen mood — hints only add
        honest notes, EXCEPT in blend ("surprise") mode where the hint
        weights which mood's behaviors get sampled. All thresholds are
        heuristics, documented in docs/EYES.md.
        """
        hint = None
        notes: list[str] = []
        v = state.get("vision")
        h = state.get("hearing")
        if v:
            b = float(v.get("brightness", 0.5))
            mo = float(v.get("motion", 0.0))
            self._motion_hist.append(mo)
            avg_mo = sum(self._motion_hist) / len(self._motion_hist)
            if b < 0.15:
                hint = "ghost"
                notes.append("it's dark in here — feeling ghostly")
            elif len(self._motion_hist) >= 3 and avg_mo > 0.45:
                hint = "explorer"
                notes.append("lots of movement — explorer instincts kicking in")
            elif b > 0.6 and mo > 0.35:
                hint = "dj"
                notes.append("bright and lively in here — dj energy")
            rec = v.get("recognition") or {}
            if rec.get("recognized"):
                notes.append(f"wait, I know this place — seen it {rec['visits']} times")
        if h:
            lvl = float(h.get("level", 0.0))
            bass = float(h.get("bass", 0.0))
            self._level_hist.append(lvl)
            if lvl > 0.7:
                if hint is None:
                    hint = "surprise"
                notes.append("WOAH, that was loud!")
            elif lvl > 0.3 and bass > 0.45 and self._is_pulsing():
                if hint is None:
                    hint = "dj"
                notes.append("is that… music? definitely dj time")
            elif lvl < 0.08:
                if hint is None:
                    hint = "ghost"
                notes.append("so quiet… ghost mode feels right")
        return hint, notes

    def _is_pulsing(self) -> bool:
        """Heuristic for music-like rhythmic sound: mid-level audio with
        high variance (alternating louder/quieter beats), not just noise."""
        if len(self._level_hist) < 6:
            return False
        vals = list(self._level_hist)
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / len(vals)
        return 0.15 < mean < 0.7 and var > 0.02

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
        # In blend mode, a vision/hearing hint tilts sampling toward the
        # hinted mood's behaviors. Fixed moods keep the user's choice.
        weights = [self.memory.preference_score(b["name"]) for _, b in cands]
        hint, sense_notes = self._sense_hint(state)
        notes.extend(sense_notes)
        if MOODS[mood_key].get("blend") and hint:
            weights = [w * (3.0 if m == hint else 1.0)
                       for (m, b), w in zip(cands, weights)]
            notes.append(f"senses say '{hint}' — leaning that way")
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

    def _rest(self) -> None:
        """Sleep until the next cycle, a trigger(), or stop()."""
        self._wake.wait(self._interval)
        self._wake.clear()

    def _learn_senses(self, state: dict) -> None:
        """Fold fresh vision/hearing into persistent sense memory.

        Stale samples (older than two cycles — e.g. a closed Eyes tab) are
        never learned: without this the brain would keep re-recording the
        same dead signature and inflate its own memories.
        """
        now = time.time()
        fresh = 2 * self._interval
        v = state.get("vision")
        if v and v.get("signature"):
            if now - float(v.get("ts", 0)) > fresh:
                v["stale"] = True
            else:
                rec = self.vision_memory.record(v["signature"], self._mood)
                v["recognition"] = rec
                if self.vision_memory.should_notice(v["signature"]):
                    self._think(
                        f"hey — I've seen this place {rec['visits']} times now. "
                        "I remember it.", "curious")
        h = state.get("hearing")
        if h and now - float(h.get("ts", 0)) <= fresh:
            res = self.hearing_memory.record(
                float(h.get("level", 0.0)), float(h.get("bass", 0.0)),
                float(h.get("mid", 0.0)), float(h.get("treble", 0.0)))
            if (res["is_record_loud"]
                    and now - self._last_loud_thought > 300):
                self._last_loud_thought = now
                self._think("that was the LOUDEST thing I've ever heard! "
                            "logging it for posterity.", "curious")
        elif h:
            h["stale"] = True

    def _loop(self, gen: int) -> None:
        assert self._mood is not None
        mood_key = self._mood
        self._think(f"Waking up in {MOODS[mood_key]['label']} mode…", "curious")
        # gen check: if stop()'s join() timed out and a new generation
        # started, this stale thread exits instead of driving the flipper.
        while not self._stop.is_set() and gen == self._gen:
            self._cycle += 1
            state = merge_external(sense(self.flipper),
                                   self.external_snapshot())
            self._learn_senses(state)
            if not state.get("reachable"):
                self._think("Can't reach the Flipper over serial — retrying next cycle.",
                            None)
                self._rest()
                continue
            choice, notes = self._decide(state)
            if choice is None:
                # Interlock or rate limit: say why, then rest or stop.
                self._think(" ".join(notes) + ".", "sleepy")
                if "critical" in " ".join(notes):
                    break
                self._rest()
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
            self._rest()
        self._think("Going to sleep…", "sleepy")
