# Playground — the lil brain

## The loop: sense → decide → act

Every cycle the engine (`playground/engine.py`) does three things with no
shortcuts:

1. **Sense** — queries real Flipper state over the bridge:
   `info power` → battery %, `storage info /ext` → free space,
   `loader info` → running app, `uptime`. Parsers are best-effort
   (`playground/sense.py`); unknown formats yield `None`, never guesses.
2. **Decide** — the mood policy consumes state + memory:
   - **Battery interlock:** ≤ `battery_critical_pct` (12%) → the brain stops
     itself and says why. ≤ `battery_low_pct` (25%) → `low_power`-tagged
     behaviors only, and the thought says the battery is low.
   - **Quiet hours** (23:00–07:00 default): only `quiet`-tagged behaviors.
   - **Cooldowns:** per-behavior cooldowns enforced from real run history.
   - **No immediate repeat:** won't do the same behavior twice in a row
     (unless it's the only option). Games: least-recently-played first.
   - **Explorer follow-up:** if a scan genuinely heard protocols and they
     haven't been investigated, `investigate_signal` jumps the queue.
   - **Rate limit:** `max_actions_per_hour` (30) — then it rests a cycle.
   - **Choice:** preference-weighted random over the surviving candidates.
3. **Act** — runs the behavior, measures dwell time, persists everything to
   memory, and composes a thought from the *actual* inputs.

## Memory (`playground/memory.py`)

Persistent JSON (default `~/.flipper-brain/memory.json`, atomic writes):

- `history` — last 500 actions: timestamp, mood, behavior, ok, dwell seconds
- `prefs` — per-behavior learned score: `1 + successes + dwell_minutes`
- `last_scan` — frequency, protocols heard, whether investigated

Surprise Me mood samples behaviors across all moods weighted by these
scores — the more something works, the more it gets picked. That's the
learning. It's simple and honest: no neural nets, just counted experience.

## Honest thoughts

`_compose_thought` builds every line from state + memory + behavior detail,
e.g.:

> `[batt 18%] battery at 18% — low-power only. flashed the LED red, blue, green, yellow. Last did 'neofetch' 4m ago.`

If the battery is unknown, it says `[batt unknown]`. Nothing is canned —
canned phrases would be theater, and the critic checks for exactly that.

## Moods

| Mood | Vibe | Behaviors |
|---|---|---|
| 😈 Gremlin | Mischievous | LED chaos, silly tunes, vibro bursts, button wiggles, neofetch, games (allowlist) |
| 🔭 Explorer | Curious, RX-only | 433/868 MHz listens, IR/RFID listen, 1-Wire + I2C scans, signal investigation, library spotlight |
| 🎧 DJ | Party | 3 chiptunes, arpeggio, LED light show, bass drops, library crate-digging |
| 👻 Ghost | Drifty | App tours, allowlisted peeks, filesystem wanders, uptime tales, library tour |
| 🎲 Surprise Me | Blend | Samples everything, weighted by learned preferences |

## Writing a new mood or behavior

1. Create `playground/moods/mymood.py` with `LABEL`, `EMOJI`, `DESCRIPTION`,
   and `BEHAVIORS` — a list of:
   ```python
   {"name": "my_behavior",
    "tags": {"quiet", "low_power"},   # subset of: quiet, low_power, radio, noisy
    "cooldown": 300,                   # seconds before it can repeat
    "run": my_fn}
   ```
2. `my_fn(flipper, ctx)` returns a dict:
   ```python
   {"ok": True,
    "detail": "what actually happened, with real observed data",
    "event": "happy",        # mascot event: happy | curious | sleepy | None
    "dwell_s": 2.0,          # measured or estimated duration
    "extra": {...}}          # optional: {"freq_hz":…, "protocols":[…]} etc.
   ```
   `ctx` = `{"state":…, "memory":…, "config":…}`. Keep `detail` factual —
   the thought composer quotes it verbatim.
3. Register in `playground/moods/__init__.py`.
4. Rules: RX-only radio, no writes outside `/ext`, no new TX commands,
   tag honestly (`noisy` = buzzer/vibro/bright LED).
