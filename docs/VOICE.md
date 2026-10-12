# Voice — talk to the lil brain

Hold the mic button on the Remote screen, speak, release. The dashboard
transcribes with the Web Speech API (Chrome/Android), the bridge matches
your words against command patterns, and the brain answers out loud via
speech synthesis in its own personality voice.

## What it understands

| You say | Brain does |
|---|---|
| "become a gremlin" / "go ghost" / "dj mode" | Switches playground mood |
| "do something" / "surprise me" / "wake up" | Forces one playground cycle now |
| "go to sleep" / "stop" | Stops the playground |
| "battery?" / "what's your charge?" | Reads real Flipper battery over serial |
| "what do you see?" | Describes the latest Eyes frame (or says eyes are closed) |
| "what do you hear?" | Describes the latest Ears sample (or says ears are off) |
| "find NFC apps" | Searches the UberGuidoZ library collection |
| "who are you?" | Introduces itself, mood-flavored |

Replies are written in the brain's voice — playful, a little gremlin —
flavored by the current mood (whispery in Ghost, bouncy in DJ).

## The honest part

This is **command + personality-response voice, not open conversation**.
There is no language model involved: no new installs, no API keys, no
freeform chat. If you say something outside the patterns, the brain tells
you what it *does* understand instead of hallucinating an answer.

**Future work:** true freeform conversation is planned as an in-browser
~2GB LLM (3B params via WebLLM/WebGPU, fully offline on the phone) — chosen
over bigger models (too heavy for phone browser tabs) and bridge-side
inference (needs the computer on). Until then, commands it is.

## Controls

- **🎙 Hold to talk** — press-and-hold; release to send.
- **🔊/🔇 voice toggle** — mutes the talk-back speech synthesis.
- Talking to the brain counts as **engagement**: recent loud moments in
  hearing memory get tagged, so it learns which sounds precede your attention.

## UNVERIFIED / known limits

- Web Speech API transcription quality is untested on Dwele's actual
  device/browser; noisy rooms will degrade it.
- speechSynthesis voices vary wildly by Android version — the "mascot voice"
  (rate 1.15, pitch 1.3) is a best-effort setting, not a real voice model.
- Requires the Bridge transport (server-side matching).
