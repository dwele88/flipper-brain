# 100 AI-Powered Flipper Zero App Ideas
*For Dwele's Flipper Zero Neuro Cortex Brain project — generated 2026-10-12. 70 by Sascha, 18 with Venom (OpenClaw), 12 wildcards. Every idea respects real Flipper Zero hardware (STM32WB55, 128x64 screen, ~256KB RAM). AI runs on-device (tinyML), phone-assisted (phone does the heavy compute over Bluetooth), or cloud-assisted (phone relays). Radio ideas are RX-only: no jamming, no replay, no rolling-code cracking. ★ = top 10.*

## Sub-GHz Signal Intelligence (13)

**1. ★ Signal Sleuth** — Captures an unknown Sub-GHz signal and names its protocol family on the spot. *AI: on-device tinyML pulse-timing classifier.* New: identifies what it heard instead of just recording raw noise.

**2. Weather Whisperer** — Decodes 433MHz weather-station packets and tracks sensor drift over weeks. *AI: phone-assisted model predicts sensor failure before it dies.* New: predictive maintenance for $10 sensors.

**3. Counter Watch** — Logs rolling-code counter progression metadata (never replays) on your own devices to spot desync. *AI: on-device anomaly detection.* New: device health monitoring, not attack.

**4. ★ Spectrum Painter** — Builds a long-term occupancy heatmap of Sub-GHz bands across days. *AI: on-device k-means clustering busy vs quiet times.* New: turns the Flipper into a pocket spectrum survey tool.

**5. Remote Librarian** — Fingerprints your own remotes by timing signature and IDs which one you pressed without decoding the protocol. *AI: on-device k-NN.* New: device identification without protocol decode.

**6. Signal Deduplicator** — Clusters near-identical captures so your SD card stops filling with 40 copies of the same doorbell. *AI: on-device embedding + clustering.* New: solves a real collector annoyance.

**7. Protocol Tutor** — Explains a captured signal in plain language on screen ("OOK, 433.92MHz, 24-bit fixed code, likely a doorbell"). *AI: phone LLM.* New: makes RF legible to beginners.

**8. Anomaly Barker** — Learns the normal RF background of your home and vibrates when something unusual appears. *AI: on-device anomaly detection.* New: passive RF awareness for your space.

**9. TPMS Tracker** — Decodes tire-pressure sensor bursts and learns each tire's pressure curve, warning on slow leaks. *AI: on-device trend analysis.* New: car health from ambient RF you already receive.

**10. Pager Poet** — Decodes POCSAG pager traffic and summarizes interesting broadcasts. *AI: phone-assisted LLM summarizer.* New: turns pager noise into a readable feed.

**11. Channel Optimizer** — Suggests the quietest frequency within a band based on observed background noise. *AI: on-device noise profiling.* New: data-driven frequency picking.

**12. Duration Predictor** — Learns typical lengths of known signals to separate valid transmissions from noise. *AI: on-device sequence learning.* New: smarter capture filtering.

**13. Doorbell DJ** — Recognizes different doorbells by RF signature and plays a custom chime per visitor. *AI: on-device classifier.* New: smart doorbell ID from passive listening.

## NFC / RFID Smarts (12)

**14. Card Curator** — Auto-organizes your NFC dumps: labels card types, flags duplicates, suggests renames. *AI: on-device classifier.* New: file hygiene for NFC collectors.

**15. MIFARE Mentor** — Walks you through reading your own MIFARE cards step by step, explaining each sector as it's read. *AI: phone LLM tutor.* New: teaches while you work.

**16. Key Counter** — Tracks scan counts per RFID tag and predicts tag wear. *AI: on-device trend analysis.* New: usage analytics for physical tokens.

**17. Tag Twin Finder** — Fuzzy-hashes dumps to detect the same physical card saved twice. *AI: on-device fuzzy hashing.* New: dedup for NFC collections.

**18. NFC Ghostwriter** — Composes legitimate NDEF payloads (your own URLs, vCards, guest WiFi) with writing help. *AI: phone-assisted LLM.* New: NDEF authoring assistant.

**19. Reader Radar** — Samples NFC field strength over time to map reader hotspots in a room. *AI: on-device field sampling.* New: NFC field mapping.

**20. Dump Doctor** — Analyzes corrupted or partial dumps and diagnoses which read failed. *AI: phone-assisted heuristics.* New: debugging for bad reads.

**21. Access Logbook** — Turns scans of your own door tag into a personal entry/exit diary with timestamps. *AI: on-device.* New: personal access journal.

**22. Tag Content Summarizer** — Reads a tag and produces a human-readable summary of what's stored. *AI: phone-assisted.* New: instant tag legibility.

**23. Privacy-Tag Scrubber** — Scans tag records and recommends removing personal data before sharing a dump. *AI: phone-assisted PII detection.* New: share safely.

**24. Security Posture Reporter** — Evaluates a tag's encryption and warns about outdated standards. *AI: phone-assisted analysis.* New: know how weak your cards are.

**25. Protocol Emulator** — Simulates dynamic NFC reader-interaction behaviors for protocol research on your own test cards. *AI: phone-assisted behavior modeling.* New: interactive NFC protocol lab.

## Infrared (7)

**26. Remote Remixer** — Learns your remote's codes from observation, then builds one-click macros ("movie night" = TV on + HDMI2 + soundbar on). *AI: on-device macro learner.* New: macros learned by watching you.

**27. IR Archaeologist** — Identifies unknown IR protocols from raw timing and names the likely brand family. *AI: on-device decision tree.* New: protocol ID with no database needed.

**28. Button Mapper** — Reorders your saved remotes by how often you actually press each button. *AI: on-device usage stats.* New: remote layout that adapts to you.

**29. AC Whisperer** — Infers your air conditioner's IR state codes and builds a virtual thermostat UI. *AI: on-device state-machine inference.* New: dumb IR AC becomes smart control.

**30. Couch Referee** — Passively logs IR "channel wars" when two remotes fight and keeps a scoreboard. *AI: on-device RX monitoring.* New: playful passive game for households.

**31. IR Health Check** — Tests every button of a saved remote against the original to find dead buttons. *AI: on-device comparison.* New: remote diagnostics.

**32. IR Signal Synthesizer** — Maps unrecognized IR patterns to standard protocol schemas to generate codes for legacy devices you own. *AI: cloud-assisted pattern mapping.* New: resurrect remotes for old gear.

## BadUSB Productivity — benign automation only (7)

**33. ★ Morning Me** — Describe your morning routine in plain words; it writes the DuckyScript; one plug runs it on your own PC. *AI: phone-assisted LLM script authoring.* New: natural-language BadUSB for your own machine.

**34. Password Butler** — Encrypted vault on the Flipper types your own passwords after an on-device PIN. *AI: on-device auth logic.* New: Flipper as a hardware password keeper.

**35. Meeting Muter** — One button mutes your mic and kills your camera in any meeting app. *AI: on-device macro.* New: panic button for calls.

**36. Snippet Slinger** — Types your code boilerplate from shortcodes; library syncs via phone. *AI: phone-assisted.* New: text-expander dongle.

**37. WiFi Welcomer** — Types your own home WiFi credentials into new devices. *AI: on-device.* New: painless device onboarding.

**38. Presenter Pal** — Advances slides with a timer and haptic countdown warnings. *AI: on-device.* New: presentation remote with a sense of time.

**39. Script Optimizer** — Analyzes your DuckyScript for efficiency and validates it against known-good patterns. *AI: phone/cloud-assisted.* New: linter for BadUSB.

## GPIO / Hardware Helpers (13)

**40. ★ Sensor Sage** — Reads GPIO sensors and explains the data in plain words ("soil's dry — water the plants"). *AI: phone LLM interpreter.* New: natural-language sensor readout.

**41. Logic Detective** — Uses GPIO as a crude logic analyzer and auto-identifies UART/I2C/SPI plus baud rate. *AI: on-device pattern matching.* New: auto-baud detection on a Flipper.

**42. Volt Watcher** — Monitors a voltage rail over time, learns normal ripple, alerts on anomalies. *AI: on-device anomaly detection.* New: PSU health monitoring.

**43. Servo Choreographer** — Describe a movement ("wave hello"); it generates the servo PWM sequence. *AI: phone-assisted LLM.* New: natural-language servo control.

**44. Plant Parent** — Soil + light sensing with learned happy-ranges; nags you only when it matters. *AI: on-device learned thresholds.* New: adaptive plant care.

**45. Air Acolyte** — Logs CO2/VOC and gives weekly air-quality summaries. *AI: phone-assisted.* New: quantified air for your room.

**46. Button Box Builder** — Turns GPIO buttons into a macro pad; suggests layouts from your app usage. *AI: phone-assisted.* New: DIY stream deck.

**47. Continuity Companion** — Cable continuity with tone pitch mapped to resistance; learns good vs flaky connections. *AI: on-device.* New: a multimeter you can hear.

**48. Sensor Calibrator** — Auto-calibrates attached sensors from their observed signal range. *AI: on-device heuristic.* New: no-manual calibration.

**49. Logic-Gate Learner** — Teaches digital logic by suggesting truth-table experiments from live GPIO signals. *AI: on-device.* New: hands-on electronics tutor.

**50. Pin-Map Visualizer** — Identifies attached peripherals from their signaling and suggests the pinout diagram. *AI: on-device.* New: plug in mystery hardware, get answers.

**51. Weather Station Pro** — BME280 sensor learns your microclimate; daily hyperlocal forecast. *AI: phone-assisted.* New: forecast for your backyard, not the city.

**52. Noise Detective** — Classifies noise sources (traffic, snoring, dog) from a mic module. *AI: on-device tinyML audio.* New: knows what it hears.

## Games with AI (13)

**53. ★ Snake Savant** — A ghost snake learns your play style and hunts you. *AI: on-device heuristic opponent.* New: an opponent that adapts to you.

**54. Pong Prophet** — Pong AI that predicts your paddle movement from your history. *AI: on-device linear predictor.* New: it reads you.

**55. ★ Dungeon Delver** — Procedurally generated dungeon crawler where every room gets a real story. *AI: phone LLM writes the narrative.* New: infinite RPG with actual writing.

**56. ★ Chesslet** — Real chess against a reduced-depth engine on the Flipper. *AI: on-device minimax.* New: genuine chess AI in 256KB RAM.

**57. Tamagotchi 2.0** — Virtual pet with a mood model that learns which interactions you enjoy. *AI: on-device learning.* New: a pet that adapts to its owner.

**58. Flappy Foe** — Pipe gaps adapt to your skill to keep you in flow state. *AI: on-device dynamic difficulty.* New: a game that tunes itself to you.

**59. Minesweeper Mentor** — Shows the safest next click with the probability reasoning displayed. *AI: on-device solver.* New: teaches minesweeper logic as you play.

**60. Blackjack Brain** — Card-counting trainer (practice only, not casino play). *AI: on-device coach.* New: learn to count cards legitimately.

**61. RPS Oracle** — Rock-paper-scissors that exploits your patterns via Markov chains. *AI: on-device.* New: humbling in the best way.

**62. Maze Mind** — A new seeded maze daily; race against your own best path. *AI: on-device.* New: daily challenge with history.

**63. Sprite Generator** — Generates monochrome pixel-art sprites for your own Flipper games. *AI: cloud-assisted generation.* New: custom art without drawing skills.

**64. Procgen Engine** — Deterministic seeded generator for endless maze/platformer levels any game can use. *AI: on-device.* New: infinite levels as a library.

**65. Simon Savant** — Simon where the sequences are AI-composed little melodies, not random beeps. *AI: on-device generative.* New: musical memory game.

## Utilities (9)

**66. File Feng Shui** — Auto-organizes your SD card: sorts by type and date, archives the old. *AI: on-device learned preferences.* New: SD hygiene bot.

**67. Signal Diary** — Every capture auto-tagged with time and notes; a daily "what your Flipper heard" journal. *AI: phone-assisted LLM journaling.* New: quantified RF self.

**68. Battery Bard** — Learns your usage patterns and predicts remaining hours better than the stock gauge. *AI: on-device regression.* New: a battery meter that knows you.

**69. Dolphin Trainer** — Recommends the highest-XP-per-minute activities for your dolphin pet. *AI: on-device optimizer.* New: min-max your dolphin.

**70. Backup Brain** — Incremental SD backup: only new/changed files, integrity-verified. *AI: on-device.* New: smart backup without a PC.

**71. UI Fuzzer** — Systematically crawls menu trees and logs dead ends and crashes for firmware developers. *AI: on-device crawler.* New: automated firmware QA.

**72. Update Oracle** — Compares your firmware and apps against latest releases and flags what's stale. *AI: phone-assisted.* New: never run old firmware unknowingly.

**73. Shortcut Sage** — Learns your most-used menu paths and surfaces them one click away. *AI: on-device frequency learning.* New: launcher that adapts to you.

**74. Cable Tester Pro** — Maps continuity across multi-conductor cables and learns their pinouts. *AI: on-device.* New: cable diagnostics.

## Accessibility (6)

**75. ★ Voice Flipper** — Speak commands on your phone; it translates them into Flipper actions over Bluetooth. *AI: phone-assisted LLM.* New: full voice control of the device.

**76. Vibe Coder** — Every UI event gets a distinct vibration pattern; it learns which patterns you recognize fastest. *AI: on-device.* New: a haptic language for the UI.

**77. Big Button Mode** — Simplifies everything to your 6 most-used actions in large text. *AI: on-device usage learning.* New: accessible launcher.

**78. Ambient Display** — Auto-adjusts contrast and backlight from ambient light sampling. *AI: on-device.* New: readable anywhere.

**79. Voice-Memo Transcriber** — Records short voice notes and offloads transcription to the phone. *AI: phone-assisted.* New: audio notes become text.

**80. Room Tone Mapper** — Profiles ambient noise to find the best spot and settings for voice recording. *AI: on-device.* New: acoustic scouting.

## Learning / Study Tools (6)

**81. RF Flashcards** — Quizzes you on protocols with spaced repetition based on your captures. *AI: on-device.* New: RF study deck that uses your own signals.

**82. Morse Mentor** — Teaches morse code with pacing that adapts as you improve. *AI: on-device.* New: a tutor that speeds up with you.

**83. Binary Buddy** — Binary/hex conversion drills with streaks. *AI: on-device.* New: number-base gym.

**84. Protocol Playground** — Interactive timing diagrams: tweak parameters and watch the effects live. *AI: on-device visualizer.* New: learn RF by touching it.

**85. Reaction Racer** — Measures reaction time and coaches improvement drills. *AI: on-device.* New: reflex trainer.

**86. Hangman Helper** — Word game with difficulty adapted to your vocabulary. *AI: on-device.* New: hangman that knows your level.

## Harmless Pranks (4)

**87. Rickroller** — Motion-triggered: plays Never Gonna Give You Up on your own Flipper when a friend picks it up. *AI: on-device trigger.* New: self-pranking Flipper.

**88. Fortune Flipper** — Shake for a fortune; fresh ones written daily. *AI: phone-assisted.* New: magic 8-ball deluxe.

**89. Dolphin Drama** — Your dolphin pet acts out soap-opera episodes with real dialogue. *AI: phone-assisted writing.* New: pet sitcom.

**90. RF Ghost HUD** — Animates fake high-tech frequency visualizations for show. *AI: on-device.* New: look like a movie hacker (harmless).

## Music / Audio (5)

**91. ★ Beat Boxer** — Buzzer step sequencer; hum a melody into your phone and it transcribes it to RTTTL. *AI: phone-assisted transcription.* New: hum-to-ringtone.

**92. RTTTL Remixer** — Takes a ringtone and generates variations in tempo and key. *AI: on-device transformations.* New: generative ringtones.

**93. Vibe Composer** — Type a mood word ("epic", "chill") and get a buzzer melody back. *AI: phone-assisted composition.* New: mood music generator.

**94. Rhythm Tracker** — Syncs screen visuals to rhythmic patterns in ambient light and sound. *AI: on-device.* New: the Flipper feels the beat.

**95. Radio-Music Visualizer** — Maps live radio activity into monochrome screen art. *AI: on-device.* New: see the airwaves.

## Wildcards (5)

**96. ★ Dream Dolphin** — Overnight, the Flipper "dreams": replays the day's captures as abstract light and sound patterns, then writes a dream journal. *AI: phone-assisted.* New: poetic quantified self — nobody's made a device that dreams.

**97. Gesture Wand** — With a GPIO motion module, learns your gesture commands (flick = next track on your own setup). *AI: on-device k-NN.* New: gesture remote from a Flipper.

**98. QR Oracle** — Generates QR codes on the tiny screen: your guest WiFi, your contact card, a link. *AI: on-device.* New: QR business cards from your pocket.

**99. Lost Key Finder** — Put a SubGHz beacon on your keys; the Flipper plays hot/cold with signal strength. *AI: on-device RSSI game, RX-only.* New: find-my-keys as a game.

**100. Lie Detector Lite** — A skin-conductance sensor on GPIO for your own biofeedback practice sessions. *AI: on-device baseline + anomaly flags.* New: self-experiment gadget.

## Sascha's Picks — Round 2
*Dwele loved Dream Dolphin, Voice Flipper, and Chesslet — so here's 20 more at that level: ambitious, delightful, technically spicy. "Wait, a Flipper can do THAT?" energy. Same hardware honesty: STM32WB55, 256KB RAM, 128x64 screen. ★ = the 5 strongest.*

**101. ★ Echo of You** — A chatbot on your Flipper that talks like you do, trained on your own messages. *AI: phone distills your chat history into a tiny n-gram/Markov model; runs fully on-device.* New: nobody carries a pocket clone of their own texting voice.

**102. ★ Dolphin Vault** — Real TOTP/HOTP two-factor codes on the Flipper, secrets synced once from your phone. *AI: on-device RFC 6238 crypto, no AI needed — just correct engineering.* New: turns the Flipper into a hardware authenticator that never touches the internet.

**103. ★ Guitar Tuner** — Plug in a mic module and tune any instrument: pitch detected on-device, cents-off shown on screen. *AI: on-device autocorrelation pitch detection (tinyML-adjacent DSP).* New: a genuinely useful instrument tuner living on a hacking tool.

**104. ★ Flipper Telegraph** — Two of your own Flippers hold a morse-code chat over Sub-GHz at legal low power. *AI: on-device morse decode with error-tolerant timing.* New: a private pocket telegraph network — delightfully anachronistic.

**105. ★ The Airwaves Oracle** — Ask a yes/no question; it consults the day's actual RF statistics and delivers a poetic verdict. *AI: on-device signal stats + phone LLM as the oracle's voice, RX-only.* New: divination powered by real spectrum data instead of random numbers.

**106. Tabletop DM** — Your phone's LLM runs a full tabletop RPG campaign; the Flipper is the dice, initiative tracker, and sound-effects board. *AI: phone LLM narrative + on-device dice physics.* New: the Flipper becomes the sacred artifact at the D&D table.

**107. Pocket Synthesizer** — Your phone streams MIDI over Bluetooth; the Flipper plays it on the buzzer and scrolls the notes on screen. *AI: phone does synthesis; Flipper is the speaker + display.* New: a 128x64-keyboard instrument you can actually jam on.

**108. Distraction Draft** — Phone acts as a Bluetooth keyboard; the Flipper shows 4 clean lines of text and saves to SD. *AI: none — the discipline IS the feature.* New: a distraction-free typewriter with zero apps to betray you.

**109. Theremin Flipper** — A distance sensor on GPIO turns hand-waving into buzzer pitch. *AI: on-device smoothing + scale quantization.* New: play actual melodies by waving at your pocket.

**110. Vibration Oracle** — An accelerometer module learns your home's vibration signatures: washer finished, door knocked, dryer done. *AI: on-device pattern learning.* New: your Flipper feels the house.

**111. POV Wand** — Wave a GPIO LED strip through the air and persistence-of-vision paints text in light. *AI: on-device timing sync.* New: long-exposure light graffiti from your pocket.

**112. Cat Herald** — An IR beam across the hallway announces your cat with a custom chime per pet. *AI: on-device beam-break classification (cat vs human vs tumbleweed).* New: a butler for your animals.

**113. Somniloquist** — Records only when sound crosses a threshold overnight; your phone transcribes it by morning. *AI: on-device voice-activity detection + phone transcription.* New: find out what you say in your sleep.

**114. Timelapse Trigger** — IR/GPIO intervalometer for your camera with exposure ramping for day-to-night shoots. *AI: on-device light-trend prediction.* New: pro timelapse control from a device that fits in a coin pocket.

**115. Zen Dolphin** — Meditation bells, a breathing pacer on screen, and generative ambient buzzer patterns. *AI: on-device generative sequencing.* New: a mindfulness device hiding inside a hacker tool.

**116. Rep Ripper** — Strap on an accelerometer module; it counts your reps and roasts you when your form gets lazy. *AI: on-device motion classification.* New: a gym coach with no subscription fee.

**117. Time Capsule** — Seal a message plus today's signal snapshot; it unlocks only after N days via hash time-lock. *AI: on-device cryptography.* New: a message to your future self, enforced by math.

**118. Spirit Scanner** — Rapid RX-only band scans stitched into a playful "ghost box," with the phone's LLM interpreting the "responses." *AI: phone-assisted interpretation of real scanned audio.* New: paranormal radio with a straight face.

**119. Blackout Buddy** — Monitors USB 5V; when power dies it logs the outage, and on return writes you a full incident report. *AI: on-device event logging + trend analysis.* New: a power-outage witness that never sleeps.

**120. Deep Work Gargoyle** — A focus timer with teeth: end your session early and it hits you with a freshly generated roast. *AI: phone LLM writes the roasts; on-device timer.* New: productivity through fear of a tiny demon.
