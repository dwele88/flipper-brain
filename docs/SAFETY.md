# Safety

Flipper Brain is a personal-hardware toy and learning tool. These rules are
hard constraints — they protect your hardware and your freedom.

## Radio: RX only, forever

- The playground **listens** (`subghz rx`, `ir rx`, `rfid read`) and **never
  transmits**. No `subghz tx`, no `tx_from_file`, no jamming, no replaying
  captured signals, no rolling-code anything.
- Scans are time-bounded (Ctrl+C after N seconds) so the radio never sits
  hot.
- Library SubGHz captures are reference material, not ammunition.

## Your property only

- No credential cloning, no BadUSB automation against other machines, no
  NFC/RFID emulation of anything that isn't yours.
- BadUSB payloads from the library are text — read them before installing,
  run them only on your own machines.
- Nothing in this repo is aimed at anyone else's property, ever.

## Device protection

- **Battery interlocks:** ≤25% → low-power behaviors only; ≤12% → the brain
  stops itself. Lithium cells degrade when abused.
- **Rate limits:** max 30 actions/hour default; per-behavior cooldowns.
- **Quiet hours:** no buzzer/vibro/bright LED 23:00–07:00 by default.
- File writes stay under `/ext` (SD card). The bridge never touches
  `update`/`factory_reset`, and `power off` isn't exposed via the API
  (reboot is, for recovery).

## Honesty

- Thought lines reflect real decision inputs. If state is unknown, the brain
  says so.
- `docs/API.md` marks `/api/screen` as 501/planned — no fake endpoints.
- CLI parsers are best-effort and documented as such.

If a behavior idea violates any of the above, it doesn't ship. Simple as.
