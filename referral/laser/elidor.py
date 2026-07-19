"""
elidor.py — minimal, safe GRBL sender for the Elidor Z6 (12W) diode laser.

Hub-aware: the Elidor's USB-serial bridge enumerates through the USB hub, so
/dev/ttyUSB numbering is not stable. Default port is the udev symlink
/dev/taza-laser (pinned by 99-taza-laser.rules); if that's absent we autodetect
by opening each /dev/ttyUSB* and looking for the GRBL welcome banner.

Safety posture:
  * connect()/handshake never enable the diode.
  * Nothing here powers the laser except stream(), and stream() refuses to run
    unless armed=True is passed explicitly.
  * soft_reset() (0x18) is sent on connect and on close to leave GRBL idle.

This is intentionally a small, auditable char-counting streamer rather than a
dependency on LightBurn — it's what the automated per-spatula burn path needs.
"""

from __future__ import annotations

import glob
import time

import serial  # pyserial

DEFAULT_PORT = "/dev/taza-laser"
BAUD = 115200
SOFT_RESET = b"\x18"  # Ctrl-X


class ElidorError(RuntimeError):
    pass


def _looks_like_grbl(text: str) -> bool:
    """True if `text` contains anything a live GRBL controller would emit —
    the boot banner, a status frame like <Idle|...>, an 'ok', or an error.
    We accept any of these because this Elidor's CH340 board does NOT reset on
    DTR, so we can't count on catching the power-on banner."""
    t = (text or "").lower()
    if "grbl" in t or "error:" in t:
        return True
    if any(s in t for s in ("<idle", "<run", "<hold", "<alarm", "<jog", "<door")):
        return True
    return "ok" in t.split()


class Elidor:
    def __init__(self, port: str | None = None, baud: int = BAUD, timeout: float = 2.0):
        self.port = port or DEFAULT_PORT
        self.baud = baud
        self.timeout = timeout
        self.ser: serial.Serial | None = None
        self.banner: str = ""

    # -- connection -------------------------------------------------------
    def connect(self, dtr_reset: bool = False) -> str:
        """Open the port (autodetecting if needed) and confirm GRBL responds.
        Does NOT enable the laser.

        dtr_reset defaults False: this Elidor Z6's CH340 board does NOT wire DTR
        to the MCU reset (confirmed on the N100), so toggling DTR yields no boot
        banner. Instead we probe with a status query, which GRBL answers whether
        or not it just booted. Pass dtr_reset=True only for boards known to reset
        on DTR.
        """
        port = self._resolve_port()
        self.ser = serial.Serial(port, self.baud, timeout=self.timeout)
        self.port = port
        if dtr_reset:
            self.ser.setDTR(False)
            time.sleep(0.1)
            self.ser.reset_input_buffer()
            self.ser.setDTR(True)
            time.sleep(2.0)  # GRBL boot
        self.banner = self._probe()
        if not _looks_like_grbl(self.banner):
            # A soft reset re-emits the banner on boards that reset; harmless otherwise.
            self.ser.write(SOFT_RESET)
            time.sleep(1.5)
            self.banner += self._probe()
        if not _looks_like_grbl(self.banner):
            raise ElidorError(
                f"No GRBL response from {port} at {self.baud} baud. Got: {self.banner!r}"
            )
        return self.banner.strip()

    def _probe(self) -> str:
        """Elicit a GRBL response WITHOUT resetting the board: newline wake, then
        a real-time '?' status query and '$I'. Returns whatever came back."""
        assert self.ser
        self.ser.reset_input_buffer()
        self.ser.write(b"\r\n")
        time.sleep(0.2)
        out = self._read_all()
        self.ser.write(b"?")           # real-time status query — no newline
        time.sleep(0.2)
        out += self._read_all()
        self.ser.write(b"$I\n")
        time.sleep(0.3)
        out += self._read_all()
        return out

    def _resolve_port(self) -> str:
        candidates = [self.port] + sorted(glob.glob("/dev/ttyUSB*")) + sorted(glob.glob("/dev/ttyACM*"))
        seen, ordered = set(), []
        for c in candidates:
            if c and c not in seen:
                seen.add(c)
                ordered.append(c)
        last_err = None
        for c in ordered:
            try:
                s = serial.Serial(c, self.baud, timeout=1.0)
            except (serial.SerialException, OSError) as e:
                last_err = e
                continue
            try:
                # Probe without DTR reset (CH340-safe): wake + status query.
                s.reset_input_buffer()
                s.write(b"\r\n"); time.sleep(0.2)
                s.write(b"?"); time.sleep(0.2)
                data = s.read(s.in_waiting or 128).decode("ascii", "replace")
                if _looks_like_grbl(data):
                    s.close()
                    return c
            finally:
                if s.is_open:
                    s.close()
        raise ElidorError(f"No GRBL device found on {ordered} (last error: {last_err})")

    # -- low level --------------------------------------------------------
    def _read_all(self) -> str:
        assert self.ser
        time.sleep(0.05)
        return self.ser.read(self.ser.in_waiting or 1).decode("ascii", "replace")

    def send_line(self, line: str, wait: float = 0.3) -> str:
        """Send one command line and return GRBL's reply. For query/config
        lines like $I, $$, $H — NOT for streaming a job."""
        if not self.ser:
            raise ElidorError("not connected")
        self.ser.write((line.strip() + "\n").encode("ascii"))
        time.sleep(wait)
        return self._read_all().strip()

    def info(self) -> dict:
        """Return $I build info and $$ settings (read-only)."""
        return {"I": self.send_line("$I"), "settings": self.send_line("$$", wait=0.6)}

    # -- streaming (the only thing that can fire the laser) ---------------
    def stream(self, gcode_lines, armed: bool = False, on_line=None):
        """Stream a G-code job using simple send-response flow control.

        armed must be True or this refuses to run — a guard so an accidental
        call can never fire the diode. Caller is responsible for confirming the
        material is placed, focus is set, and a human is supervising.
        """
        if not armed:
            raise ElidorError("stream() called without armed=True — refusing to fire the laser")
        if not self.ser:
            raise ElidorError("not connected")
        self.ser.write(SOFT_RESET)
        time.sleep(1.0)
        self._read_all()
        for i, raw in enumerate(gcode_lines):
            line = raw.strip()
            if not line or line.startswith(";"):
                continue
            self.ser.write((line + "\n").encode("ascii"))
            # Block until GRBL acks this line (ok / error).
            resp = ""
            deadline = time.time() + 30
            while "ok" not in resp and "error" not in resp:
                resp += self._read_all()
                if time.time() > deadline:
                    raise ElidorError(f"timeout waiting for ack on line {i}: {line!r}")
                time.sleep(0.01)
            if on_line:
                on_line(i, line, resp.strip())
            if "error" in resp:
                raise ElidorError(f"GRBL error on line {i} ({line!r}): {resp.strip()}")

    def laser_off(self):
        """Belt-and-suspenders: command the laser off and idle the controller."""
        if self.ser:
            self.ser.write(b"M5\n")
            time.sleep(0.2)
            self.ser.write(SOFT_RESET)
            time.sleep(0.2)
            self._read_all()

    def close(self):
        try:
            self.laser_off()
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()
