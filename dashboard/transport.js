/* Flipper Zero Neuro Cortex Brain — transport-agnostic FlipperConnection.
 *
 * Three transports, one interface:
 *   - BridgeTransport    : HTTP to the local Python bridge (desktop default).
 *                          Full features: CLI, files, apps, playground, library.
 *   - BluetoothTransport : Web Bluetooth straight to the Flipper Zero.
 *                          CLI, files, apps. No playground/library (server-side).
 *   - SerialTransport    : Web Serial (desktop Chrome/Edge, USB).
 *                          CLI, files, apps. No playground/library.
 *
 * BLE PROFILE — VERIFIED, NOT NORDIC UART:
 * The Flipper Zero does NOT expose the standard Nordic UART Service
 * (6E400001-B5A3-F393-E0A9-E50E24DCCA9E). It exposes a proprietary
 * "serial service" used by the official mobile app's RPC channel.
 * UUIDs below are confirmed against multiple independent working clients
 * (see docs/SETUP.md "Phone setup" for sources):
 *   Service : 8fe5b3d5-2e7f-4a98-2a48-7acc60fe0000
 *   RX (host->Flipper, WRITE)        : 19ed82ae-ed21-4c9d-4145-228e62fe0000
 *   TX (Flipper->host, INDICATE)     : 19ed82ae-ed21-4c9d-4145-228e61fe0000
 *   Flow control (optional)          : 19ed82ae-ed21-4c9d-4145-228e63fe0000
 *
 * IMPORTANT CAVEATS (flagged, not silently assumed):
 * 1. TX uses INDICATE (not notify). startNotifications() enables both, but
 *    some stacks need the CCCD written for indications explicitly.
 * 2. Characteristics require an AUTHENTICATED (paired/bonded) link. Pair the
 *    Flipper in the phone's system Bluetooth settings BEFORE connecting here.
 * 3. Raw-CLI-over-BLE delivery depends on firmware state: the stock `bt`
 *    service registers its RPC handler over the serial profile on connect.
 *    Whether plain CLI text is accepted on all firmwares is UNVERIFIED —
 *    test on real hardware (stock / Momentum / Unleashed) before relying.
 * 4. Web Bluetooth needs a secure context (https:// or localhost). Served
 *    from the bridge on a LAN IP it will NOT work without TLS or Chrome's
 *    "insecure origins treated as secure" flag — see docs/SETUP.md.
 * 5. Web Serial is desktop Chrome/Edge only — NOT available on Android.
 *    On the S23, Bluetooth is the only direct transport.
 */

"use strict";

const FLIPPER_BLE = {
  SERVICE: "8fe5b3d5-2e7f-4a98-2a48-7acc60fe0000",
  RX: "19ed82ae-ed21-4c9d-4145-228e62fe0000", // write, host -> Flipper
  TX: "19ed82ae-ed21-4c9d-4145-228e61fe0000", // indicate, Flipper -> host
  FLOW: "19ed82ae-ed21-4c9d-4145-228e63fe0000",
};

const CLI_PROMPT = ">: ";
const CLI_ENTER = "\r";
const CLI_CTRL_C = "\x03";
const BLE_WRITE_CHUNK = 100; // bytes per GATT write; conservative for default MTU

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

/* Chunked writer shared by BLE transports */
async function writeChunked(writeFn, data) {
  const bytes = new TextEncoder().encode(data);
  for (let i = 0; i < bytes.length; i += BLE_WRITE_CHUNK) {
    await writeFn(bytes.slice(i, i + BLE_WRITE_CHUNK));
  }
}

/* ------------------------------------------------------------------ */
/* BridgeTransport — talks to the Python bridge over HTTP              */
/* ------------------------------------------------------------------ */
class BridgeTransport {
  static get kind() { return "bridge"; }
  static get label() { return "Bridge"; }
  static get available() { return true; } // assumed; calls fail gracefully
  static get serverFeatures() { return true; }

  constructor() { this._connected = null; }

  async connect() {
    const r = await fetch("/api/status").then((x) => x.json());
    this._connected = !!r.connected;
    if (!this._connected && r.last_error) throw new Error(r.last_error);
    if (!this._connected) throw new Error("bridge has no Flipper attached");
    return true;
  }
  async disconnect() { this._connected = false; }
  isConnected() { return this._connected === true; }

  async execCli(command, { timeout = 15, stopAfter = null } = {}) {
    const r = await fetch("/api/cli", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command, timeout, stop_after: stopAfter }),
    }).then((x) => x.json());
    if (!r.ok) throw new Error(r.error || "cli failed");
    return r.output;
  }
  async reboot() {
    await fetch("/api/reboot", { method: "POST" });
    return "reboot sent";
  }
}

/* ------------------------------------------------------------------ */
/* RawCliTransport — base for transports that speak CLI bytes directly */
/* ------------------------------------------------------------------ */
class RawCliTransport {
  constructor() {
    this._buf = "";
    this._waiters = []; // {resolve, reject, timer}
    this._onData = this._onData.bind(this);
  }

  /* subclass hooks */
  async _open() { throw new Error("not implemented"); }
  async _close() { throw new Error("not implemented"); }
  async _writeBytes(bytes) { throw new Error("not implemented"); }

  _onData(text) {
    this._buf += text;
    this._pump();
  }
  _pump() {
    const idx = this._buf.indexOf(CLI_PROMPT);
    if (idx === -1) return;
    const chunk = this._buf.slice(0, idx);
    this._buf = this._buf.slice(idx + CLI_PROMPT.length);
    const w = this._waiters.shift();
    if (w) { clearTimeout(w.timer); w.resolve(chunk); }
    if (this._buf.includes(CLI_PROMPT)) this._pump();
  }

  async _readPrompt(timeoutMs) {
    if (this._buf.includes(CLI_PROMPT)) {
      const idx = this._buf.indexOf(CLI_PROMPT);
      const chunk = this._buf.slice(0, idx);
      this._buf = this._buf.slice(idx + CLI_PROMPT.length);
      return chunk;
    }
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        const i = this._waiters.indexOf(w);
        if (i !== -1) this._waiters.splice(i, 1);
        reject(new Error("CLI prompt timeout"));
      }, timeoutMs);
      const w = { resolve, reject, timer };
      this._waiters.push(w);
    });
  }

  _clean(command, raw) {
    const lines = raw.replace(/\r\n/g, "\n").split("\n");
    let skipped = false;
    const out = [];
    for (const line of lines) {
      if (!skipped && line.trim() === command.trim()) { skipped = true; continue; }
      out.push(line);
    }
    return out.join("\n").replace(/\n+$/, "");
  }

  async execCli(command, { timeout = 15, stopAfter = null } = {}) {
    if (!this.isConnected()) throw new Error("not connected");
    this._buf = "";
    this._waiters.length = 0;
    await writeChunked((b) => this._writeBytes(b),
      command + CLI_ENTER);
    if (stopAfter) {
      // interactive command: capture for N seconds, then Ctrl+C
      const cap = (async () => {
        await sleep(stopAfter * 1000);
        await writeChunked((b) => this._writeBytes(b), CLI_CTRL_C);
      })();
      const raw = await this._readPrompt((stopAfter + 8) * 1000);
      await cap;
      return this._clean(command, raw);
    }
    const raw = await this._readPrompt(timeout * 1000);
    return this._clean(command, raw);
  }

  async reboot() {
    // don't wait for a prompt that will never come back
    try {
      this._buf = "";
      await writeChunked((b) => this._writeBytes(b), "power reboot" + CLI_ENTER);
      await sleep(1500);
    } catch (e) { /* link died mid-reboot: expected */ }
    return "reboot sent";
  }
}

/* ------------------------------------------------------------------ */
/* BluetoothTransport — Web Bluetooth -> Flipper serial service         */
/* ------------------------------------------------------------------ */
class BluetoothTransport extends RawCliTransport {
  static get kind() { return "bluetooth"; }
  static get label() { return "Bluetooth"; }
  static get available() {
    return typeof navigator !== "undefined" && "bluetooth" in navigator;
  }
  static get serverFeatures() { return false; }

  constructor() {
    super();
    this.device = null;
    this._rx = null;
    this._tx = null;
    this._onDisconnect = this._onDisconnect.bind(this);
    this.onDisconnect = null; // set by FlipperConnection
  }

  isConnected() {
    return !!(this.device && this.device.gatt && this.device.gatt.connected);
  }

  async connect() {
    // NOTE: must be called from a user gesture (button click).
    this.device = await navigator.bluetooth.requestDevice({
      filters: [{ services: [FLIPPER_BLE.SERVICE] }],
      optionalServices: [FLIPPER_BLE.SERVICE],
    });
    this.device.addEventListener("gattserverdisconnected", this._onDisconnect);
    const server = await this.device.gatt.connect();
    const svc = await server.getPrimaryService(FLIPPER_BLE.SERVICE);
    this._rx = await svc.getCharacteristic(FLIPPER_BLE.RX);
    this._tx = await svc.getCharacteristic(FLIPPER_BLE.TX);
    // TX is INDICATE on the Flipper; startNotifications covers both.
    await this._tx.startNotifications();
    this._tx.addEventListener("characteristicvaluechanged",
      (e) => this._onData(new TextDecoder().decode(e.target.value)));
    // wake the CLI and wait for the prompt
    this._buf = "";
    await writeChunked((b) => this._writeBytes(b), CLI_ENTER);
    try {
      await this._readPrompt(6000);
    } catch (e) {
      throw new Error("connected, but no CLI prompt — pair in system Bluetooth " +
        "settings first, and see docs/SETUP.md (firmware BLE-CLI state unverified)");
    }
    return true;
  }

  _onDisconnect() {
    this.device = null; this._rx = null; this._tx = null;
    if (this.onDisconnect) this.onDisconnect();
  }

  async _writeBytes(bytes) {
    if (!this._rx) throw new Error("not connected");
    await this._rx.writeValue(bytes);
  }

  async _open() { return this.connect(); }
  async _close() { return this.disconnect(); }

  async disconnect() {
    try {
      if (this._tx) { try { await this._tx.stopNotifications(); } catch (e) {} }
      if (this.device && this.device.gatt.connected) this.device.gatt.disconnect();
    } finally {
      this.device = null; this._rx = null; this._tx = null;
    }
  }
}

/* ------------------------------------------------------------------ */
/* SerialTransport — Web Serial (desktop Chrome/Edge, USB)              */
/* ------------------------------------------------------------------ */
class SerialTransport extends RawCliTransport {
  static get kind() { return "serial"; }
  static get label() { return "USB Serial"; }
  static get available() {
    return typeof navigator !== "undefined" && "serial" in navigator;
  }
  static get serverFeatures() { return false; }

  constructor() {
    super();
    this.port = null;
    this._reader = null;
    this._writer = null;
    this._readLoop = null;
  }

  isConnected() { return !!(this.port && this.port.readable); }

  async connect() {
    // NOTE: must be called from a user gesture (button click).
    this.port = await navigator.serial.requestPort();
    await this.port.open({ baudRate: 230400 });
    const dec = new TextDecoderStream();
    this.port.readable.pipeTo(dec.writable);
    this._reader = dec.readable.getReader();
    this._writer = this.port.writable.getWriter();
    this._readLoop = (async () => {
      try {
        while (true) {
          const { value, done } = await this._reader.read();
          if (done) break;
          this._onData(value);
        }
      } catch (e) { /* closed */ }
    })();
    await sleep(400);
    this._buf = "";
    await this._writeBytes(new TextEncoder().encode(CLI_ENTER));
    try {
      await this._readPrompt(6000);
    } catch (e) {
      throw new Error("port opened, but no CLI prompt (is qFlipper holding it?)");
    }
    return true;
  }

  async _writeBytes(bytes) {
    if (!this._writer) throw new Error("not connected");
    await this._writer.write(bytes);
  }
  async _open() { return this.connect(); }

  async _close() { return this.disconnect(); }
  async disconnect() {
    try {
      if (this._reader) { try { await this._reader.cancel(); } catch (e) {} }
      if (this._writer) { try { await this._writer.releaseLock(); } catch (e) {} }
      if (this.port) await this.port.close();
    } finally {
      this.port = null; this._reader = null; this._writer = null;
    }
  }
}

/* ------------------------------------------------------------------ */
/* FlipperConnection — one interface, swappable transport              */
/* ------------------------------------------------------------------ */
const TRANSPORTS = { BridgeTransport, BluetoothTransport, SerialTransport };

class FlipperConnection {
  constructor() {
    this.transport = null;
    this.kind = null;
    this._statusCb = null;
  }

  static available() {
    return Object.values(TRANSPORTS)
      .filter((T) => T.available)
      .map((T) => ({ kind: T.kind, label: T.label,
        serverFeatures: T.serverFeatures }));
  }

  onStatus(cb) { this._statusCb = cb; }
  _emit(state, detail) {
    if (this._statusCb) this._statusCb({ kind: this.kind, state, detail });
  }

  async connect(kind) {
    const T = TRANSPORTS[{ bridge: "BridgeTransport",
      bluetooth: "BluetoothTransport", serial: "SerialTransport" }[kind]];
    if (!T) throw new Error("unknown transport: " + kind);
    if (!T.available) throw new Error(T.label + " not available in this browser");
    await this.disconnect();
    this.transport = new T();
    this.kind = kind;
    if (this.transport instanceof BluetoothTransport) {
      this.transport.onDisconnect = () => {
        this.transport = null; this.kind = null;
        this._emit("disconnected", "link lost");
      };
    }
    this._emit("connecting");
    try {
      await this.transport.connect();
      this._emit("connected");
      return true;
    } catch (e) {
      this.transport = null; this.kind = null;
      this._emit("disconnected", e.message);
      throw e;
    }
  }

  async disconnect() {
    if (this.transport) {
      try { await this.transport.disconnect(); } catch (e) {}
      this.transport = null; this.kind = null;
      this._emit("disconnected");
    }
  }

  async reconnect() {
    const kind = this.kind;
    if (!kind) throw new Error("nothing to reconnect");
    return this.connect(kind);
  }

  isConnected() { return !!(this.transport && this.transport.isConnected()); }
  get serverFeatures() {
    if (!this.transport) return false;
    return this.transport.constructor.serverFeatures;
  }

  /* ---- unified command surface (works on every transport) ---- */
  async execCli(command, opts) {
    if (!this.transport) throw new Error("not connected");
    return this.transport.execCli(command, opts);
  }
  deviceInfo() { return this.execCli("info device", { timeout: 10 }); }
  storageList(path) { return this.execCli(`storage list ${path}`, { timeout: 15 }); }
  loaderList() { return this.execCli("loader list", { timeout: 15 }); }
  loaderOpen(name) { return this.execCli(`loader open ${name}`, { timeout: 15 }); }
  reboot() {
    if (!this.transport) throw new Error("not connected");
    return this.transport.reboot();
  }
}

// expose for app.js
window.FlipperConnection = FlipperConnection;
window.FLIPPER_BLE = FLIPPER_BLE;
