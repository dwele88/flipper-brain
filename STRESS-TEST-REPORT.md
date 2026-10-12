# NeuroFlipper — Stress Test Report

**Date:** 2026-10-12
**Scope:** software-only (no Flipper hardware attached — serial layer mocked with a faithful Flipper CLI emulator)
**Method:** adversarial harness (`/tmp/stress/stress.py`) — Flask test client + mocked `serial` module + real playground loop threads + node-based dashboard logic probes

## Headline

- **Checks run:** 1,666 (final clean run: 1,666/1,666 passed)
- **Bugs found:** 13 real bugs (3 CRITICAL, 5 HIGH, 4 MEDIUM, 1 LOW-severity cluster)
- **Bugs fixed:** all 13, each verified by a dedicated regression check
- **Bugs remaining:** 0 known in software. Hardware-dependent items listed at the end.

## Bugs found and fixed

### CRITICAL

1. **`bridge/library.py` — path traversal in `sd_path_for`** — `repo_path="Applications/../../etc"` mapped to `/ext/apps/../../etc` and was sent straight to the Flipper's `storage` CLI, escaping the `/ext` sandbox toward `/int`. Fixed: `_safe_repo_path()` rejects `.`/`..`/empty segments and absolute paths; enforced in `sd_path_for`, `download`, and `cached_path`.
2. **`bridge/library.py` — cache-dir escape in `download`/`cached_path`** — `repo_path="../../evil.txt"` resolved outside `~/.flipper-brain/library-cache` (arbitrary host file write). Fixed by the same `_safe_repo_path()` gate.
3. (Same root cause as 1, second vector via nested `..`.)

### HIGH

4. **`bridge/server.py:/api/cli` — `timeout="abc"` → HTTP 500** (`float()` ValueError uncaught). Fixed: numeric validation, must be 0–120 → 400 otherwise.
5. **`bridge/server.py:/api/cli` — `stop_after="xyz"` → HTTP 500** (TypeError). Fixed: same validation.
6. **`bridge/server.py:/api/playground/start` — `interval="abc"` → HTTP 500** (`int()` before the try block). Fixed: validated → 400.
7. **`bridge/server.py:/api/playground/thoughts` — `since="abc"` → HTTP 500**. Fixed: validated → 400.
8. **`playground/engine.py` — race: `stop()` during slow `sense()` → `AssertionError` kills the loop thread.** `stop()` clears `_mood` after `join(timeout=8)`; a thread still inside `sense()` (slow/unresponsive device) then calls `_decide` with `_mood=None` → assert → dead thread, traceback in logs. Reproduced deterministically with a slow mock. Fixed: `_decide` stands down gracefully on `_mood=None` instead of asserting.
9. **`bridge/flipper.py` — `reboot()` never closed the stale connection.** After reboot the USB link is gone; every subsequent command waited out its full timeout (up to 15s+) on a dead fd, making the bridge look hung. Worse, the slowdown made `stop()`'s `join(8)` time out, spawning zombie playground threads that compounded the contention. Fixed: `reboot()` now `close()`s the port; the next command reconnects cleanly.

### MEDIUM

10. **`playground/moods/explorer.py` — `b_library_spotlight` blocked the loop on network I/O.** `lib.search()` → GitHub tree fetch (60s timeout) ran synchronously inside the sense-decide-act loop — one slow network and the "autonomous" brain froze for up to a minute. Fixed: runs in a worker thread with a 10s cap, fails gracefully.
11. **`playground/engine.py` — zombie threads could resurrect.** A thread surviving `stop()`'s `join(8)` would resume looping after the next `start()` cleared `_stop` — two threads driving one Flipper. Fixed: generation counter; stale generations exit at the next loop check.
12. **`bridge/library.py:get_tree` — corrupt `tree.json` cache → uncaught `JSONDecodeError` → API 500.** Fixed: corrupt cache falls through to re-fetch. Non-JSON fetch payloads and `download()` network errors are now wrapped in `LibraryError` (400/502) instead of leaking raw exceptions as 500s.
13. **`playground/engine.py` — `interval=1e18` → `OverflowError` in `Event.wait`, killing the loop thread.** Fixed: interval clamped to [5, 86400].

### LOW

14. **`bridge/server.py` — malformed `config.yaml` crashed the bridge at startup** (raw `yaml.ScannerError`). Now warns on stderr and boots with defaults.
15. **Non-numeric `baud:` crashed app creation.** Now warns and falls back to 230400.
16. **`_read_until_prompt` busy-spun at 100% CPU** when reads returned empty instantly (dead link). Now yields 10ms per empty read.

### Hardening (no bug, defense in depth)

- `_require_ext` now also rejects `%2e`/`%2f` encoded segments.
- Dashboard: `transport.js` loads before `app.js`; all `getElementById` targets verified present in `index.html`; `_pump`/`_clean` prompt-splitting logic unit-tested in node (split-packet, double-prompt, timeout paths).

## What was verified working

- All 24 API routes: valid calls, malformed JSON, missing fields, wrong methods, 11-vector path-traversal battery (all blocked), 100KB commands, 200KB file writes (391-chunk roundtrip byte-exact), unicode/emoji, newline injection, RPC-session guard.
- 50-thread × 12-request concurrency: zero 500s, zero errors (RLock serializes correctly).
- 200 sequential rapid-fire requests: 200/200.
- Playground: 47 full sense→decide→act cycles; no immediate behavior repeats; every thought carries real inputs (`[batt …]`, decision notes, behavior detail); memory persists across restart; all 27 behaviors across 5 moods execute with valid result shapes.
- Interlocks: critical battery (≤12%) stops the brain; low battery (≤25%) restricts to `low_power` behaviors; rate limiter (30/hr) rests the loop; quiet hours restrict to `quiet` behaviors; explorer follows up on uninvestigated real scan findings.
- Sense parsers: 1,000 fuzz inputs (garbage, unicode, overflows, format confusions) — zero exceptions, zero out-of-range values.
- Library: traversal/escape/corruption/network-failure matrices all contained.
- Config: missing/malformed/empty/unknown-section/bad-baud matrices.
- Memory: corrupt JSON recovers to defaults; 200 concurrent records all persist.

## Fuzzing totals

- Sense parsers: 1,000 randomized inputs
- `/api/cli`: 100 fuzzed commands (null bytes, shell metachars, 5KB payloads, unicode)
- Traversal battery: 11 paths × 5 file routes = 55
- Numeric abuse: timeout/stop_after/interval/since × malformed values

## Needs real Flipper hardware (could not verify in software)

1. Serial CLI session behavior: prompt sync, `write_chunk` binary protocol, Ctrl+C interactive bounds.
2. `sense.py` parser output formats across stock / Momentum / Unleashed firmwares (parsers are best-effort by design).
3. `/api/screen` (501/planned) — no stock CLI screenshot command exists.
4. Game/app allowlist names from real `loader list`.
5. `wav_player` / `unirf` / `picopass` SD path mappings (marked verify-on-device in docs).
6. Web Bluetooth GATT UUIDs and BLE-CLI behavior (documented as unverified in `dashboard/transport.js`).
7. GitHub API rate-limit behavior for the library tree fetch.

## Files changed by this stress test

- `bridge/flipper.py` — reboot closes stale port; 10ms yield on empty reads
- `bridge/server.py` — numeric validation on 4 routes (400s not 500s); malformed-YAML and bad-baud fallbacks; `%2e` hardening in `_require_ext`
- `bridge/library.py` — `_safe_repo_path()` gate on all entry points; corrupt-cache recovery; `LibraryError` wrapping for fetch/parse/download failures
- `playground/engine.py` — `_decide` graceful stand-down; generation counter against zombies; interval clamp [5, 86400]
- `playground/moods/explorer.py` — `b_library_spotlight` 10s network cap

No git operations performed. Nothing pushed or published.
