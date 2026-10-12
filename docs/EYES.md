# Eyes & Ears — phone senses for the lil brain

The Flipper Zero has no camera and no microphone. The phone does. Eyes & Ears
lend the phone's sensors to the brain: the phone sees and hears, the bridge
reduces the raw feed to honest signals, and the Playground reacts and learns.

## How it works

```
phone camera → dashboard canvas (48×36 grayscale)
    → POST /api/eyes/frame {t, w, h, px(base64)}  (~1/sec)
    → bridge/vision.py: brightness, motion, 3×3 zone map
    → Playground external senses → decide loop + vision_memory.json

phone mic → Web Audio AnalyserNode
    → POST /api/ears {t, level, bass, mid, treble}  (~1/sec)
    → Playground external senses → decide loop + hearing_memory.json
```

- **No ML, no models, no new dependencies.** Vision is mean-pixel arithmetic
  on 1,728 bytes; hearing is RMS level + three frequency bands from the
  browser's AnalyserNode. Deliberately dumb, deliberately honest.
- **Senses go stale.** A vision/hearing sample older than 10 seconds is
  treated as unknown (never as zero) — the engine says "eyes closed" rather
  than inventing darkness.
- **Bridge-only.** Like Playground and Library, this needs the Python bridge;
  Web Bluetooth / Web Serial transports can't reach it.

## How the brain reacts

Heuristics (tuned guesses, not science — thresholds in `playground/engine.py`):

| Sense | Reading | Reaction |
|---|---|---|
| Vision | brightness < 0.15 | Ghost mood favored; "it's dark in here" |
| Vision | sustained motion (avg > 0.45 over 3+ frames) | Explorer favored; "explorer instincts" |
| Vision | bright (> 0.6) + active (motion > 0.35) | DJ favored; "dj energy" |
| Hearing | level > 0.7 | Surprise/Gremlin; "WOAH, that was loud!" |
| Hearing | mid level + strong bass + pulsing variance | DJ; "is that… music?" |
| Hearing | level < 0.08 | Ghost; "so quiet…" |

The brain **never overrides your chosen mood** — hints only add honest notes
to its thoughts, except in Surprise (blend) mode where the hint weights which
mood's behaviors get sampled. All sense influence respects the existing
cooldowns, quiet hours, battery interlocks, and rate limits.

## Learning — it genuinely accumulates

`playground/vision_memory.json` (default `~/.flipper-brain/vision_memory.json`):

- Every frame is reduced to a **scene signature**: brightness bucket (5),
  motion bucket (4), 3×3 zone map (3 levels each), hour of day.
- Repeat visits to the same signature increment a counter with per-hour
  patterns and which mood each scene tended to trigger.
- At 3+ visits the scene counts as **recognized**; the brain remarks on it
  ("I've seen this place 4 times now") at most once per 10 minutes per scene.

`playground/hearing_memory.json`:

- **Loudest moments** leaderboard (top 20, level ≥ 0.5), with timestamps.
- **Hourly noise profile**: average level per hour of day — the brain learns
  your quiet nights vs loud days.
- **Engagement tags**: when you talk to or command the brain, recent loud
  moments get flagged, so it learns which sounds preceded your attention.

Both stores cap their size and use atomic writes. Delete the files to make
the brain forget.

## UNVERIFIED / known limits

- **No real-phone testing yet.** Frame cadence, battery drain of 1/sec
  capture, and AnalyserNode behavior are untested on actual Android hardware.
- The pulsing/music heuristic is a guess — bass + variance, not beat
  detection. It will misfire on traffic, vacuums, and arguments.
- Scene signatures are coarse by design; two similar rooms at the same hour
  can collide. That's a feature for "vibes", a bug for security — don't use
  it for anything that matters.
