# 🧠 Flipper Brain

Your Flipper Zero, with a mind of its own. A Python bridge lets an AI (or you)
operate the Flipper over USB serial, a web dashboard gives you manual control,
and **Playground mode** runs an autonomous little brain with moods — it senses
real device state, remembers what it did, and tells you what it's thinking.

- **Bridge** — USB serial → HTTP API (device info, CLI terminal, files, apps)
- **Dashboard** — dark hacker UI + an animated **lil brain mascot** that reacts
  to what the brain is doing
- **Playground** — autonomous sense → decide → act loop with 5 moods:
  😈 Gremlin · 🔭 Explorer · 🎧 DJ · 👻 Ghost · 🎲 Surprise Me
- **Library** — browse/install the UberGuidoZ/Flipper file collection
  (apps, IR, SubGHz, NFC…) straight to your Flipper from the dashboard
- **Safety-first** — RX-only radio, battery interlocks, quiet hours, rate limits

## Quickstart

```bash
git clone <this-repo> && cd flipper-brain
pip install -r requirements.txt
cp config.yaml.example config.yaml   # set your serial port
python -m bridge.server              # open http://127.0.0.1:8787
```

Pick a mood in the Playground panel, hit Start, and watch the thought log.
The mascot in the corner reacts — happy on success, curious while scanning,
sleepy when idle.

## Docs

- [Setup](docs/SETUP.md) — prereqs, install, first run
- [Architecture](docs/ARCHITECTURE.md) — how the pieces fit
- [API](docs/API.md) — every bridge endpoint with examples
- [Playground](docs/PLAYGROUND.md) — moods, autonomy design, writing behaviors
- [Library](docs/LIBRARY.md) — UberGuidoZ collection integration
- [Safety](docs/SAFETY.md) — the hard rules (RX-only, etc.)

## The autonomy deal

The brain is not theater. Before every decision it reads real Flipper state
(battery, storage, running app). It keeps persistent memory
(`~/.flipper-brain/memory.json`): what it did, when, what it learned to like.
Battery under 25% → low-power behaviors only, and it tells you why. Under
12% → it puts itself to sleep. Every thought line is composed from the actual
decision inputs — state, memory, mood — never a canned phrase.

## Requirements

- Python 3.10+
- Flipper Zero on any firmware, USB cable (quit qFlipper first — it holds the port)
- `pip install -r requirements.txt` (flask, pyserial, pyyaml)

## License

MIT — your hardware, your toy. See [SAFETY](docs/SAFETY.md) before exploring.

## Support

Free and open source. If Flipper Brain made your Flipper a little more alive,
tips are welcome — [SUPPORT.md](SUPPORT.md). BiMPay (Barbados) preferred 🇧🇧,
BTC / ETH / SOL also accepted.
