# Ears — the brain hears back

The Ears screen turns your phone's mic into the Flipper's hearing. Beyond the
per-second level feed (`/api/ears`), the dashboard now **detects** what it
hears, **tells the brain**, and the brain **talks back out loud**.

## How it works

1. **Listen.** Enable ears on the Eyes & Ears screen. The mic samples volume
   and pitch bands 10x per second into a rolling history (in memory only).
2. **Detect.** Two events, with a cooldown of max 1 event per 15 seconds:
   - 😲 **startle** — level jumps more than 0.5 within 300ms *and* peaks
     above 0.7 (a crash, a thud, a gasp).
   - 😂 **laughter** — 3+ mid-band peaks above threshold inside a 2s window
     (the ha-ha-ha pattern).
3. **Clip.** On every event the last ~4 seconds of audio are frozen into a
   replayable clip (kept: max 10, newest first, in-memory object URLs).
   Tap play on any clip to hear what the brain heard.
4. **React.** The event is POSTed to `/api/ears/event`. The playground
   consumes it on the next cycle and answers with a mood-voiced line that
   the dashboard speaks via speechSynthesis — in character, one sentence.

| Mood | Startle | Laughter |
|---|---|---|
| 😈 Gremlin | "Whoa! What broke? Tell me it wasn't me." | "Ha! Do that again, I need it for my collection." |
| 🔭 Explorer | "Something just happened over there — investigating." | "Fascinating. Humans make that noise when happy. Noted." |
| 🎧 DJ | "That drop hit different. What WAS that?" | "Okay, that's a whole vibe. Run it back!" |
| 👻 Ghost | "...did you hear that too? I'm hiding." | "Even I almost smiled. Almost." |
| 🎲 Surprise Me | "Whoa! Okay. That was new. I liked it." | "Joy detected! Logging this as a core memory." |

## The honest part

Detection is heuristic, not a classifier — a dropped pan and a thunderclap
both look like startles, and the brain will happily react to both. Events
older than 30s are dropped so a stale scare never gets relived. The 🔇 voice
toggle mutes reactions too.

## Privacy

The mic records **only while the Ears screen is enabled** — never in the
background. Clips live in the page's memory as object URLs; nothing is
uploaded anywhere, and stopping ears stops the recorder immediately.
