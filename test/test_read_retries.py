# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for USB read-error handling, without hardware.

Drives the helper's real Receiver read loop and Bridge state with a fake USB
device that fails in scripted ways. Run from the repository root:

    .venv/bin/python test/test_read_retries.py
"""
import asyncio
import errno
import logging
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bridge"))
import usb.core  # noqa: E402
import x360bridge as xb  # noqa: E402

records = []


class Capture(logging.Handler):
    def emit(self, r):
        records.append(r.getMessage())


logging.getLogger().addHandler(Capture())
logging.getLogger().setLevel(logging.DEBUG)

# input report: data[1]=0x01, data[4]=0x00, data[5]=0x13, 18+ bytes
INPUT = bytes([0x00, 0x01, 0x00, 0xF0, 0x00, 0x13] + [0] * 23)
PRESENT = bytes([0x08, 0x80])


def eio():
    return usb.core.USBError("Input/Output Error", errno=errno.EIO)


class FakeDev:
    idVendor, idProduct, bus, address = 0x045E, 0x0719, 1, 2

    def __init__(self, scripts):
        self.scripts = {ep: list(s) for ep, s in scripts.items()}
        self.lock = threading.Lock()
        self.writes = []

    def read(self, ep, size, timeout):
        with self.lock:
            s = self.scripts.get(ep, [])
            item = s.pop(0) if s else "timeout"
        if item == "timeout":
            time.sleep(0.01)
            raise usb.core.USBTimeoutError("timeout", errno=errno.ETIMEDOUT)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item()
        return item

    def write(self, ep, packet, timeout):
        self.writes.append((ep, bytes(packet)))

    def clear_halt(self, ep):
        pass


def make(scripts, attached=True):
    lost = []
    got = []
    r = xb.Receiver(lambda slot, data, rec: got.append((slot, data)), lambda rec: lost.append(rec))
    r.dev = FakeDev(scripts)
    r.slots = [(i, 0x81 + 2 * i, 0x01 + 2 * i) for i in range(4)]
    r._still_attached = lambda: attached
    return r, lost, got


def run(r, secs):
    r.stop.clear()
    r.threads = [threading.Thread(target=r._read_loop, args=(i,), daemon=True) for i in range(4)]
    for t in r.threads:
        t.start()
    time.sleep(secs)
    r.stop.set()
    for t in r.threads:
        t.join(2)


results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


# 1. two transient EIOs then data: no loss, packet delivered, recovery logged once
records.clear()
r, lost, got = make({0x81: [eio(), eio(), INPUT]})
run(r, 0.6)
check("transient errors are retried, receiver kept", not lost and got == [(0, INPUT)],
      f"lost={len(lost)} got={len(got)}")
check("recovery is logged", any("recovered after 2 read errors" in m for m in records))

# 2. persistent EIO on all four slots: lost exactly once, one warning
records.clear()
r, lost, got = make({ep: [eio()] * 50 for ep in (0x81, 0x83, 0x85, 0x87)})
run(r, 2.5)
warn = [m for m in records if m.startswith("Lost the receiver")]
check("persistent errors give up after retries", len(lost) == 1, f"lost={len(lost)}")
check("only one 'Lost the receiver' line", len(warn) == 1, f"lines={len(warn)}")

# 3. ENODEV: lost immediately, no retry
records.clear()
r, lost, got = make({0x81: [usb.core.USBError("No such device", errno=errno.ENODEV)]})
t0 = time.monotonic()
r.stop.clear()
th = threading.Thread(target=r._read_loop, args=(0,), daemon=True)
th.start(); th.join(2)
check("ENODEV is treated as unplugged at once", len(lost) == 1 and time.monotonic() - t0 < 0.2)

# 4. EIO while the device is gone from the bus: lost immediately
records.clear()
r, lost, got = make({0x81: [eio()]}, attached=False)
r.stop.clear()
th = threading.Thread(target=r._read_loop, args=(0,), daemon=True)
th.start(); th.join(2)
check("EIO with receiver gone from the bus is a loss", len(lost) == 1 and not any("retrying" in m for m in records))

# 5. phantom controller: a packet in flight after the loss must not revive a pad
loop = asyncio.new_event_loop()
b = xb.Bridge(loop, 0.15)
b.flush = lambda: None
old = xb.Receiver(b.on_packet, b.on_receiver_lost)
old.dev = FakeDev({})
old.slots = [(i, 0x81 + 2 * i, 0x01 + 2 * i) for i in range(4)]
records.clear()
b.on_packet(1, PRESENT, old)
was = b.pads[1]["connected"]
old._lost(eio())                      # slot 1's thread hits the error...
b.on_packet(1, INPUT, old)            # ...while slot 2's thread delivers its last packet
b.on_packet(0, PRESENT, old)
loop.run_until_complete(asyncio.sleep(0))  # let _receiver_lost run
b.on_packet(3, INPUT, old)            # a straggler after the clean-up already ran
check("pad connected before the loss", was)
check("no phantom controller after the loss",
      not any(p["connected"] for p in b.pads) and not b.receiver_present,
      str([p["connected"] for p in b.pads]))
check("no 'connected' log after the loss",
      not any("connected" in m for m in records[records.index(next(m for m in records if m.startswith("Lost"))):]))

# 6. a fresh receiver after the loss works and lights its own LED
new = xb.Receiver(b.on_packet, b.on_receiver_lost)
new.dev = FakeDev({})
new.slots = old.slots
b.on_packet(0, PRESENT, new)
check("new receiver's controllers connect", b.pads[0]["connected"])
check("LED set on the packet's own receiver", any(w[1][:4] == bytes([0, 0, 0x08, 0x46]) for w in new.dev.writes))

# 7. close() during a retry wait returns promptly and never reports a loss
r, lost, got = make({0x81: [eio()] * 3})
r.stop.clear()
r.threads = [threading.Thread(target=r._read_loop, args=(0,), daemon=True)]
r.threads[0].start()
time.sleep(0.03)
t0 = time.monotonic()
r.stop.set()
r.threads[0].join(2)
check("stop during retry exits quickly without a loss", not lost and time.monotonic() - t0 < 0.5)

print(f"\n{sum(ok for _, ok in results)}/{len(results)} passed")
sys.exit(0 if all(ok for _, ok in results) else 1)
