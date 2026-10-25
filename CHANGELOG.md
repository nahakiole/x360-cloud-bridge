# Changelog

## 0.1.1 (2026-10-25)

Fixes controllers dropping out for a few seconds every so often.

### Fixed

- **A single USB read error no longer resets the receiver.** Before, any failed
  read (`[Errno 5] Input/Output Error`) was treated as the receiver being
  unplugged: the helper closed it, cleared every controller and reopened it, and
  each controller then had to re-sync. The macOS kernel log showed the receiver
  never actually left the USB bus when this happened. Now a failed read is
  retried up to 5 times with a short, growing pause. The receiver only counts as
  gone if it really is gone from the bus, if libusb reports `ENODEV`, or if the
  errors keep coming.
- **No more phantom controllers after a receiver loss.** A packet that was
  already in flight on another slot's reader thread could mark a controller as
  connected right after the receiver was dropped. Packets from a receiver that
  has been given up on are now ignored.
- **"Lost the receiver" is logged once**, not once per reader thread.
- **Player LEDs are set on the right receiver** while it is being reopened.

### Changed

- **Read timeout raised from 250 ms to 1 s.** On macOS every read timeout aborts
  the pending USB transfer. With four controller slots that was about 16 aborts
  per second, all the time. Packets still arrive immediately; only the idle wait
  is longer.
- **New log lines** when a read error is retried and when the slot recovers.
- **`./install.sh`** does the whole setup: installs libusb with Homebrew if
  needed, picks Python 3.10 or newer, creates `.venv`, and shows the extension
  folder for Chrome. `./start.sh` runs it automatically on the first start.

### Added

- `test/test_read_retries.py`: tests for the read-error handling that need no
  hardware.

## 0.1.0 (2026-10-06)

First release by [Maverserker](https://github.com/Maverserker/x360-cloud-bridge).
