"""Low-level Flipper Zero serial CLI connection.

Uses only documented CLI commands (see docs.flipper.net/development/cli).
Single-session: all sends are serialized behind a lock. Interactive commands
(subghz rx, ir rx, rfid read, ...) are bounded with ``stop_after`` — the
bridge sends Ctrl+C (0x03) after N seconds and returns what was captured.
"""
from __future__ import annotations

import threading
import time

import serial

PROMPT = b">: "
CTRL_C = b"\x03"
ENTER = b"\r"


class FlipperError(Exception):
    pass


class FlipperConnection:
    def __init__(self, port: str, baud: int = 230400, read_timeout: float = 1.0):
        self.port = port
        self.baud = baud
        self.read_timeout = read_timeout
        self._ser: serial.Serial | None = None
        self._lock = threading.RLock()
        self.last_error: str | None = None

    # -- connection management -------------------------------------------

    def connect(self) -> bool:
        """Open the serial port and sync to the CLI prompt. Auto-called by send()."""
        with self._lock:
            if self._ser and self._ser.is_open:
                return True
            try:
                self._ser = serial.Serial(
                    self.port, self.baud, timeout=self.read_timeout
                )
                time.sleep(0.4)
                self._ser.reset_input_buffer()
                # Wake the CLI and wait for the prompt
                self._ser.write(ENTER)
                if self._read_until_prompt(timeout=5):
                    self.last_error = None
                    return True
                self.last_error = "no CLI prompt received (is qFlipper holding the port?)"
                self.close()
                return False
            except serial.SerialException as exc:
                self.last_error = str(exc)
                self._ser = None
                return False

    def is_connected(self) -> bool:
        with self._lock:
            return bool(self._ser and self._ser.is_open)

    def close(self) -> None:
        with self._lock:
            try:
                if self._ser:
                    self._ser.close()
            finally:
                self._ser = None

    def reconnect(self) -> bool:
        self.close()
        time.sleep(0.5)
        return self.connect()

    # -- command execution -----------------------------------------------

    def send(self, command: str, timeout: float = 15.0,
             stop_after: float | None = None) -> str:
        """Send one CLI command, return its output (prompt stripped).

        stop_after: for interactive commands, capture output for N seconds,
        then send Ctrl+C and return what was captured.
        """
        with self._lock:
            if not self.connect():
                raise FlipperError(f"not connected: {self.last_error}")
            assert self._ser is not None
            self._ser.reset_input_buffer()
            self._ser.write(command.encode("utf-8", "replace") + ENTER)
            # Echo of the command line comes back first; skip to output.
            output = self._read_until_prompt(timeout=timeout, stop_after=stop_after)
            return self._clean(command, output)

    def interrupt(self) -> None:
        with self._lock:
            if self._ser and self._ser.is_open:
                self._ser.write(CTRL_C)

    # -- internals --------------------------------------------------------

    def _read_until_prompt(self, timeout: float,
                           stop_after: float | None = None) -> str:
        assert self._ser is not None
        buf = b""
        deadline = time.time() + timeout
        stop_at = time.time() + stop_after if stop_after else None
        interrupted = False
        while time.time() < deadline:
            chunk = self._ser.read(256)
            if chunk:
                buf += chunk
                if buf.endswith(PROMPT):
                    break
            else:
                # No data (yet): yield briefly instead of busy-spinning.
                # Real serial reads block on the OS timeout, so this only
                # triggers on dead links — where spinning would pin a CPU.
                time.sleep(0.01)
            if stop_at and time.time() >= stop_at and not interrupted:
                self._ser.write(CTRL_C)
                interrupted = True
                deadline = time.time() + 5  # give it a moment to exit
        return buf.decode("utf-8", "replace")

    @staticmethod
    def _clean(command: str, raw: str) -> str:
        # Strip the echoed command line and the trailing prompt.
        lines = raw.replace("\r\n", "\n").split("\n")
        cleaned: list[str] = []
        skipped_echo = False
        for line in lines:
            if not skipped_echo and line.strip() == command.strip():
                skipped_echo = True
                continue
            cleaned.append(line)
        text = "\n".join(cleaned)
        if text.endswith(">: "):
            text = text[:-3]
        return text.strip("\n")

    # -- convenience wrappers (all real, documented CLI commands) ---------

    def device_info(self) -> str:
        return self.send("info device", timeout=10)

    def storage_list(self, path: str) -> str:
        return self.send(f"storage list {path}", timeout=15)

    def storage_read(self, path: str) -> str:
        return self.send(f"storage read {path}", timeout=20)

    def storage_write(self, path: str, content: str) -> str:
        """Write text in 512-byte chunks via `storage write_chunk` (non-interactive)."""
        return self.storage_write_bytes(path, content.encode("utf-8"))

    def storage_write_bytes(self, path: str, data: bytes) -> str:
        """Write raw bytes (e.g. .fap files) via `storage write_chunk`."""
        out: list[str] = []
        if not data:
            data = b""
        for i in range(0, max(len(data), 1), 512):
            chunk = data[i:i + 512]
            with self._lock:
                if not self.connect():
                    raise FlipperError(f"not connected: {self.last_error}")
                assert self._ser is not None
                cmd = f"storage write_chunk {path} {len(chunk)}"
                self._ser.reset_input_buffer()
                self._ser.write(cmd.encode() + ENTER)
                time.sleep(0.2)
                self._ser.write(bytes(chunk))
                resp = self._read_until_prompt(timeout=15)
                out.append(self._clean(cmd, resp))
        return "\n".join(out)

    def storage_mkdir(self, path: str) -> str:
        return self.send(f"storage mkdir {path}", timeout=10)

    def ensure_dir(self, path: str) -> None:
        """Best-effort mkdir -p for an SD path (ignores 'already exists')."""
        parts = [p for p in path.strip("/").split("/") if p]
        # path like ext/apps/foo.fap -> mkdir /ext/apps (skip the filename)
        cur = ""
        for part in parts[:-1]:
            cur += "/" + part
            try:
                self.storage_mkdir(cur)
            except FlipperError:
                pass

    def storage_remove(self, path: str) -> str:
        return self.send(f"storage remove {path}", timeout=10)

    def loader_list(self) -> str:
        return self.send("loader list", timeout=15)

    def loader_open(self, app: str) -> str:
        return self.send(f"loader open {app}", timeout=15)

    def loader_close(self) -> str:
        return self.send("loader close", timeout=10)

    def reboot(self) -> str:
        # Don't wait for a prompt that will never come back.
        try:
            self.send("power reboot", timeout=3)
        except FlipperError:
            pass
        finally:
            # The device is rebooting: the USB serial link is gone. Drop the
            # stale handle now so the next command reconnects cleanly instead
            # of waiting out a full timeout on a dead fd.
            self.close()
        return "reboot sent"
