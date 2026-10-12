# Bridge API

Base URL: `http://127.0.0.1:8787`. All responses are JSON with `ok: true/false`.
Every endpoint below is implemented in `bridge/server.py` — 1:1, nothing
documented that doesn't exist.

> **Direct transports:** the dashboard can also bypass the bridge entirely
> (Web Bluetooth / Web Serial — see [SETUP.md](SETUP.md) "Phone setup").
> In that case the dashboard speaks the Flipper CLI directly through the
> `FlipperConnection` interface in `dashboard/transport.js`; the HTTP API
> below is unused except Playground/Library, which are bridge-only.

## Transport interface (`dashboard/transport.js`)

`FlipperConnection` — one interface, swappable transport:

| Method | Description |
|---|---|
| `FlipperConnection.available()` | `[{kind, label, serverFeatures}]` — kinds the browser supports (`bridge` always listed; `bluetooth` needs Web Bluetooth; `serial` needs Web Serial) |
| `connect(kind)` | `"bridge"` \| `"bluetooth"` \| `"serial"`. Must be called from a user gesture for bluetooth/serial (browser picker requirement) |
| `disconnect()` / `reconnect()` | — |
| `isConnected()` | — |
| `onStatus(cb)` | `cb({kind, state, detail})` — `state`: `connecting` \| `connected` \| `disconnected` |
| `execCli(command, {timeout?, stopAfter?})` | send one CLI command, return output with echo + prompt stripped. `stopAfter` (s) bounds interactive commands via Ctrl+C |
| `deviceInfo()` | `info device` |
| `storageList(path)` | `storage list <path>` |
| `loaderList()` / `loaderOpen(name)` | `loader list` / `loader open <name>` |
| `reboot()` | `power reboot` (no prompt wait) |
| `serverFeatures` | `true` only on the bridge transport — gates Playground + Library UI |

Transports: `BridgeTransport` (HTTP → `/api/cli`), `BluetoothTransport`
(Web Bluetooth → Flipper serial GATT service, TX via **indicate**), and
`SerialTransport` (Web Serial, 230400 baud) which share the `RawCliTransport`
base (prompt framing `>: `, `\r` enter, `\x03` interrupt, 100-byte BLE writes).

## Device

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| GET | `/api/status` | — | `{connected, port, baud, last_error, playground}` |
| GET | `/api/device` | — | `{info}` — raw `info device` output |
| POST | `/api/cli` | `{command, timeout?, stop_after?}` | `{output}` — any CLI command. `stop_after` (seconds) bounds interactive commands by sending Ctrl+C |
| POST | `/api/reboot` | — | reboots via `power reboot` |
| GET | `/api/screen` | — | **501 planned** — stock CLI has no screenshot command (needs on-device verification) |

```bash
curl -X POST localhost:8787/api/cli -H 'Content-Type: application/json' \
  -d '{"command":"neofetch"}'
curl -X POST localhost:8787/api/cli -H 'Content-Type: application/json' \
  -d '{"command":"subghz rx 433920000 0","stop_after":8}'   # RX-only listen
```

## Files (`/ext` = SD card, `/int` = internal)

All file endpoints are confined to `/ext` — requests for `/int` or paths
with `..` are rejected with 400. The bridge never exposes internal storage.

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| GET | `/api/files?path=/ext` | — | `{path, listing}` — `storage list` |
| GET | `/api/file?path=/ext/x.txt` | — | `{path, content}` — `storage read` |
| POST | `/api/file` | `{path, content}` | writes via chunked `storage write_chunk` |
| DELETE | `/api/file` | `{path}` | `storage remove` |
| POST | `/api/mkdir` | `{path}` | `storage mkdir` |

## Library (UberGuidoZ/Flipper collection)

Browse/search/install files from the community collection. See
[LIBRARY.md](LIBRARY.md) for the category → SD path mapping and caching.

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| GET | `/api/library/categories` | — | `{repo, categories: [{name, sd_path, installable, note}]}` |
| GET | `/api/library/browse?category=BadUSB` | `category`, `path?` | `{category, files: [{path, name, size}]}` |
| GET | `/api/library/search?q=snake` | `q` | `{results: [{path, size}]}` (max 50) |
| POST | `/api/library/install` | `{repo_path}` | `{repo_path, sd_path, bytes}` — downloads (cached) + pushes to the Flipper SD |
| GET | `/api/library/installed?category=Infrared` | `category` | `{sd_path, installed}` — raw `storage list` of the mapped SD dir |

```bash
curl "localhost:8787/api/library/search?q=tetris"
curl -X POST localhost:8787/api/library/install -H 'Content-Type: application/json' \
  -d '{"repo_path":"BadUSB/demo.txt"}'
```

## Apps

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| GET | `/api/apps` | — | `{apps}` — `loader list` |
| POST | `/api/apps/launch` | `{name}` | `loader open <name>` (exact name from the list) |
| POST | `/api/apps/close` | — | `loader close` |

## Playground

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| GET | `/api/playground/moods` | — | `{moods: {key: {label, emoji, description}}}` |
| POST | `/api/playground/start` | `{mood, interval?}` | starts the sense→decide→act loop |
| POST | `/api/playground/stop` | — | stops the loop |
| GET | `/api/playground/status` | — | `{running, mood, interval, cycle, last_event}` |
| GET | `/api/playground/thoughts?since=N` | — | `{thoughts: [{id, ts, mood, text, event}], cursor}` |
| GET | `/api/playground/stream` | — | Server-Sent Events stream of thoughts |

Moods: `gremlin`, `explorer`, `dj`, `ghost`, `surprise`.

```bash
curl -X POST localhost:8787/api/playground/start -H 'Content-Type: application/json' \
  -d '{"mood":"explorer","interval":30}'
curl localhost:8787/api/playground/thoughts?since=0
```

## Eyes & Ears (phone senses)

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/eyes/frame` | `{t, w, h, px}` — base64 grayscale bytes, `len == w*h` | `{brightness, motion, zones[9], signature}` — brightness/motion 0..1, 3×3 zone map |
| POST | `/api/ears` | `{t, level, bass, mid, treble}` — all 0..1 | `{level, bass, mid, treble}` echoed |

Frames are ~48×36 grayscale at ~1/sec from the dashboard. The bridge keeps
only the previous frame in memory (for motion); persistent learning lives in
`playground/vision_memory.json` and `playground/hearing_memory.json`. Samples
older than 10s are treated as unknown. See [EYES.md](EYES.md).

## Voice & remote brain control

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/voice` | `{text}` | `{reply, action}` — personality-voiced reply + optional action (`mood`/`trigger`/`stop`/`library_results`) |
| POST | `/api/brain` | `{action: "mood", mood}` | switches playground mood (starts it if idle) |
| POST | `/api/brain` | `{action: "trigger"}` | one immediate sense→decide→act cycle |
| POST | `/api/brain` | `{action: "speak", text, event?}` | pushes a line to the thought log (mascot reacts) |
| POST | `/api/input` | `{key: up\|down\|left\|right\|ok\|back}` | **501** — input injection is unverified on stock firmware; never faked |

Voice is command-pattern matching, not freeform chat — see [VOICE.md](VOICE.md).
