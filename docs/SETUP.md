# Setup

## Prereqs

- Python 3.10+ (for the Bridge; not needed for direct Bluetooth/USB-serial mode)
- Flipper Zero on **any** firmware (stock, Momentum, Unleashed…), with a
  microSD card for file features
- USB-C cable (Bridge / USB-serial mode)
- **Quit qFlipper** (desktop/mobile app) before starting — it holds the serial
  port and the bridge won't get a prompt

## Phone setup (Samsung S23 / Android Chrome) — no computer needed

The dashboard can talk **directly** to the Flipper over Bluetooth from Chrome
on Android. No Python, no bridge, no APK.

1. On the Flipper: **Settings → Bluetooth → Enable**. Leave it on.
2. On the phone: pair the Flipper in **system Bluetooth settings** first
   (Settings → Connections → Bluetooth → pair "Flipper …"). The Flipper shows
   a 6-digit passkey — confirm it. This step is required: the Flipper's BLE
   characteristics demand an authenticated/bonded link.
3. Open the dashboard in **Chrome** (not Samsung Internet, not a WebView app).
4. Tap **🔌 Link → 📶 Bluetooth → Connect**, pick your Flipper from the
   picker, and wait for the CLI prompt handshake.
5. Use Terminal / Device / Files / Apps. Playground and Library need the
   Bridge (they run server-side) — the dashboard tells you when they're off.

**Caveats:**
- Web Bluetooth requires a **secure context**: it works on `https://` and
  `http://localhost`, but NOT on plain `http://192.168.x.x`. If you serve the
  dashboard over your LAN, either put TLS in front of it or open Chrome flags
  `chrome://flags/#unsafely-treat-insecure-origin-as-secure` and add your URL.
- Web Serial (🔌 USB Serial button) is **desktop Chrome/Edge only** — it does
  not exist on Android. On the S23, Bluetooth is the only direct transport.
- Bluetooth CLI delivery depends on firmware state (the stock `bt` service
  claims the serial profile for RPC on connect). Verified working path is the
  Bridge; direct-BLE CLI is marked **experimental** until tested on real
  hardware across firmwares.

## BLE profile reference (verified)

The Flipper Zero does **not** use Nordic UART Service. Verified against
multiple working third-party clients and Momentum firmware source analysis:

| Role | UUID |
|---|---|
| Serial service | `8fe5b3d5-2e7f-4a98-2a48-7acc60fe0000` |
| RX — write, phone → Flipper | `19ed82ae-ed21-4c9d-4145-228e62fe0000` |
| TX — **indicate**, Flipper → phone | `19ed82ae-ed21-4c9d-4145-228e61fe0000` |
| Flow control (optional) | `19ed82ae-ed21-4c9d-4145-228e63fe0000` |

## Install (Bridge mode)

```bash
git clone <this-repo> neuroflipper
cd neuroflipper
pip install -r requirements.txt   # flask, pyserial, pyyaml
cp config.yaml.example config.yaml
```

Edit `config.yaml`:

```yaml
serial:
  port: /dev/ttyACM0   # macOS: /dev/tty.usbmodemXXXX  Windows: COM3
```

Find your port:
- Linux: `ls /dev/ttyACM*`
- macOS: `ls /dev/tty.usbmodem*`
- Windows: Device Manager → Ports (COM & LPT)

## First run

```bash
python -m bridge.server
# → Flipper Zero Neuro Cortex Brain bridge on http://127.0.0.1:8787
```

Open that URL. The lil brain does its intro, then:

1. Check the **Device** card — hit *Refresh info*. If it shows an error,
   the port is wrong or qFlipper is holding it.
2. **Terminal** — type `help`, hit Send. You should see the Flipper's
   command list.
3. **Playground** — pick 😈 Gremlin, hit Start. Watch the thought log;
   the mascot bounces when behaviors succeed.

## Playground personalization

```yaml
playground:
  game_allowlist: ["Snake"]        # names from `loader list` on YOUR device
  app_tour_allowlist: ["Sub-GHz"]  # apps Ghost may open for a peek
```

Behaviors that need an allowlist skip themselves gracefully when it's empty.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `no CLI prompt received` | Quit qFlipper / Flipper Lab; replug USB |
| `Permission denied` on `/dev/ttyACM0` | Add yourself to `dialout`: `sudo usermod -aG dialout $USER`, re-login |
| `storage` commands fail | SD card missing/not mounted — file features need it |
| Brain stops immediately | Battery ≤12% (critical interlock) — charge the Flipper |
| Only quiet behaviors run | Quiet hours active (23:00–07:00 default) — see config |
| App names don't match | Run `loader list` in the Terminal card, copy exact names |
