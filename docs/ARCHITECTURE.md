# Architecture

```
┌─────────────┐   USB serial 230400   ┌──────────────────┐
│ Flipper Zero│ ◄──────────────────► │ bridge/flipper.py│  FlipperConnection
│  (CLI)      │   real CLI commands   │  (pyserial, lock)│
└─────────────┘                       └────────┬─────────┘
                                              │ Python calls
                                     ┌────────▼─────────┐
                                     │ bridge/server.py │  Flask REST API
                                     │  + static files  │  + SSE thought stream
                                     └────────┬─────────┘
                          ┌──────────────────┼──────────────────┐
                          │ HTTP             │                  │ in-process
                 ┌────────▼────────┐ ┌───────▼────────┐ ┌───────▼──────────┐
                 │ dashboard/      │ │ any AI client  │ │ playground/    │
                 │ index.html      │ │ (Claude, your  │ │ engine.py      │
                 │ style.css app.js│ │  own scripts)  │ │ sense/decide/  │
                 │ + lil brain     │ │                │ │ act + memory   │
                 │   mascot (SVG)  │ │                │ │ moods/*.py     │
                 └─────────────────┘ └────────────────┘ └────────────────┘
```

## bridge/

- `flipper.py` — `FlipperConnection`: opens the serial port, syncs to the
  `>:` prompt, sends one command at a time (thread lock), reads until the
  prompt returns. Interactive commands (`subghz rx`, `ir rx`, …) take
  `stop_after=N`: capture output for N seconds, send Ctrl+C (0x03), return.
  `storage_write` chunks through the non-interactive `storage write_chunk`.
  Only documented CLI commands are used (see docs.flipper.net/development/cli).
- `server.py` — Flask app: REST endpoints (see docs/API.md), serves
  `dashboard/` as static files, hosts the Playground engine in a thread,
  exposes the thought log via polling + SSE. Also hosts Eyes/Ears/Voice
  endpoints (`bridge/vision.py`, `bridge/voice.py`) and feeds phone senses
  into the engine's external-sense channel.

## playground/

- `sense.py` — perception. Best-effort parsers for `info power`,
  `storage info /ext`, `loader info`, `uptime`. Unknown formats → `None`,
  never fabricated.
- `memory.py` — persistent JSON memory: full action history (cap 500),
  per-behavior preference scores (runs + dwell time + successes),
  last RX scan findings. Atomic writes (tmp + rename).
- `engine.py` — the sense → decide → act loop in a daemon thread.
  - **Sense**: `sense()` every cycle, merged with phone senses
    (`merge_external` — vision/hearing from the dashboard, stale after 10s).
  - **Decide**: battery interlocks (≤12% stop, ≤25% low-power only), quiet
    hours (quiet-tagged behaviors only), per-behavior cooldowns from memory,
    no-immediate-repeat, explorer follow-up priority on real uninvestigated
    scan findings, max-actions-per-hour rate limit, preference-weighted
    random choice. Vision/hearing hints add honest notes; in blend
    ("surprise") mode they tilt sampling toward the hinted mood. The engine
    never overrides the user's chosen mood.
  - **Act**: run behavior, measure dwell, record to memory, compose an
    honest thought from state + memory + behavior detail.
  - **Learn**: every cycle folds fresh vision into `vision_memory.json`
    (scene signatures, recognition, per-hour patterns) and hearing into
    `hearing_memory.json` (loudest moments, hourly noise profile,
    engagement tags).
  - **Remote**: `set_mood` / `trigger` / `speak` let the dashboard (or voice)
    drive the brain without touching the Flipper.
- `moods/` — five moods, each a module with `BEHAVIORS`: a list of
  `{name, tags, cooldown, run}`. Tags: `low_power`, `quiet`, `radio`,
  `noisy`. `surprise` is a blend mood — the engine samples across all moods
  weighted by learned preference scores.

## dashboard/

Single page, no build step, no libraries. `app.js` polls `/api/status`
(5s) and `/api/playground/thoughts` (2s). The lil brain mascot is inline
SVG + CSS: intro performance on load (wake → stretch → look → wave →
dock), then reactive states (`is-happy`, `is-curious`, `is-sleepy`) and
mood costumes (`mood-gremlin` bounce+smirk, `mood-explorer` spyglass,
`mood-dj` headphones+bob, `mood-ghost` float). Events arrive via the
thought log's `event` field.

New screens (all bridge-only):

- **Eyes** — `getUserMedia` camera → 48×36 grayscale canvas → base64 POST
  to `/api/eyes/frame` at ~1/sec; live brightness/motion meters + 3×3 zone
  preview. The **Ears** subsection uses `getUserMedia` audio +
  `AnalyserNode` → per-second level/bass/mid/treble → `/api/ears`.
- **Remote** — D-pad (honest 501 until button injection is verified on real
  firmware), brain controls (mood switch, trigger cycle, speak-to-thought-log),
  and push-to-talk voice: Web Speech API transcription → `/api/voice` →
  pattern-matched reply spoken back via `speechSynthesis` (mutable).

## Data flow for one autonomous cycle

1. Engine: `state = sense(flipper)` → 4 CLI round-trips.
2. Engine: `choice, notes = _decide(state)` (memory consulted).
3. Engine: `result = behavior["run"](flipper, ctx)`.
4. Engine: `memory.record(...)` (+ `record_scan` for RX findings).
5. Engine: `_think(compose(state, memory, notes, result))` → dashboard log
   + mascot event.
6. Sleep `interval`, repeat until stopped.
