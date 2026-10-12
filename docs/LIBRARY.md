# Library — UberGuidoZ/Flipper file collection

Flipper Brain can browse and install files from
[UberGuidoZ/Flipper](https://github.com/UberGuidoZ/Flipper) (17k+ stars),
the community-standard all-in-one Flipper Zero file collection: apps,
BadUSB payloads, IR remotes, SubGHz captures, NFC/RFID dumps, music, and more.

Credit: all files belong to their authors via that repo — we're a client, not
a mirror. Support UberGuidoZ's work through the links on their repo.

## How it works

- **On demand, never vendored.** The repo is gigabytes; we fetch only what you
  ask for, via `raw.githubusercontent.com` for files and the GitHub API for
  the file tree.
- **Cache:** `~/.flipper-brain/library-cache/`
  - `tree.json` — repo file tree, refreshed every 24h
  - `files/<repo-path>` — downloaded files. **Never re-downloaded while cached.**
    Delete the cache folder to force a fresh pull.
- **Install:** cached file → pushed to the Flipper SD card in 512-byte
  `storage write_chunk`s (byte-exact, safe for `.fap` binaries).

## Category → SD path mapping

| Collection | Installs to | One-click? |
|---|---|---|
| Applications | `/ext/apps` | ✅ |
| BadUSB | `/ext/badusb` | ✅ |
| Infrared | `/ext/infrared` | ✅ |
| Sub-GHz | `/ext/subghz` | ✅ |
| NFC | `/ext/nfc` | ✅ |
| RFID | `/ext/lfrfid` | ✅ |
| Music_Player | `/ext/music` | ✅ |
| Wav_Player | `/ext/wav_player` | ✅ (verify on-device) |
| unirf | `/ext/unirf` | ✅ (verify on-device) |
| subplaylist | `/ext/subghz` | ✅ |
| picopass | `/ext/picopass` | ✅ (verify on-device) |
| iButton | `/ext/ibutton` | ✅ |
| GPIO, Graphics, docs… | — | browse only |

"Verify on-device" = the SD location is our best mapping; confirm the app
picks the files up on your firmware.

## Dashboard

The **Library** tab: pick a category (shows its SD destination), browse or
search, hit **install**. Every install is logged in the terminal card.

## Playground use

- **Ghost** `library_tour`: spotlights a random library app and tells you
  whether it's already on your Flipper.
- **DJ** `crate_dig`: installs a random library track to `/ext/music` —
  the install is reported in the thought log (install-on-demand, always logged).
- **Explorer** `library_spotlight`: references a random library SubGHz
  capture as inspiration. Passive reference only — nothing is transmitted.

## API

See [API.md](API.md): `/api/library/categories`, `/browse`, `/search`,
`/install`, `/installed`.

## Safety notes

- `.fap` files are binaries from a third-party repo. Prefer the official
  app catalog for anything security-sensitive; the library is a convenience.
- BadUSB payloads are **text** — read them before installing, and only ever
  run them against your own machines (see [SAFETY](SAFETY.md)).
- SubGHz captures are reference material. The playground never transmits.
