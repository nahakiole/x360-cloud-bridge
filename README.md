# X360 Cloud Bridge

Use your **Xbox 360 wireless controller** (with the USB wireless receiver) to play
**Xbox Cloud Gaming**, **GeForce NOW** and browser games in Chrome on a modern Mac,
including Apple Silicon.

No kernel extension, no driver, and no changes to SIP, AMFI or NVRAM.

> This is a fork of [Maverserker/x360-cloud-bridge](https://github.com/Maverserker/x360-cloud-bridge)
> that fixes controllers dropping out for a few seconds during play, and adds a
> one-command setup. See [What this fork changes](#what-this-fork-changes).

[Leer en español](README.es.md)

## Quick start

You need a Mac with [Homebrew](https://brew.sh), Google Chrome and the Xbox 360
wireless receiver plugged in.

```bash
git clone https://github.com/nahakiole/x360-cloud-bridge.git
cd x360-cloud-bridge
./install.sh
```

`install.sh` installs `libusb` with Homebrew if it's missing, sets up a Python
environment in `.venv`, and shows you the extension folder. Then load the
extension in Chrome, once:

1. Open `chrome://extensions`
2. Turn on **Developer mode** (top right)
3. Click **Load unpacked** and pick the `extension` folder. The installer copied its
   path to your clipboard: press `Cmd+Shift+G` in the dialog and paste.

Every time you want to play:

```bash
./start.sh
```

Turn on the controller with the Guide button and open
[xbox.com/play](https://www.xbox.com/play), [play.geforcenow.com](https://play.geforcenow.com)
or a game on `localhost`. The controller shows up as a regular Xbox controller.
Leave the terminal open while you play and press `Ctrl+C` to stop.

If a page was already open before you loaded the extension, reload it. **Quit Steam**
before you play: it grabs the receiver while it runs.

## What this fork changes

Version 0.1.1. The full list is in the [changelog](CHANGELOG.md).

### The problem

With two controllers playing for a couple of hours, both controllers would vanish a
few times per session and come back after a few seconds. The helper's log showed:

```
12:53:41 Lost the receiver ([Errno 5] Input/Output Error)
12:53:43 Receiver 045e:0719 ready, 4 controller slots
12:53:43 Controller 1 connected
12:53:49 Controller 1 disconnected
12:53:56 Controller 1 connected
```

Moving the receiver from a hub straight into the MacBook didn't help. The macOS
kernel log (`/usr/bin/log show`) explained why: at those moments the receiver
**never left the USB bus**. There was no disconnect, no re-enumeration, no sleep
or power change, and no other app opening it. A single USB read had failed.

The original helper treated *any* read error as "the receiver was unplugged". It
closed the device, cleared every controller, reopened the receiver, and each
controller then had to re-sync. That reset, not the hardware, was what players
saw.

The kernel log also showed constant transfer aborts on all four controller
endpoints, about 16 per second. On macOS, libusb aborts the pending transfer on
every read timeout, and the helper used a 250 ms timeout. That churn is the most
likely source of the occasional failed read.

### The fix

- **Failed reads are retried.** A read error is retried up to 5 times with a short,
  growing pause, and the slot logs when it recovers. The receiver only counts as
  lost if libusb says the device is gone (`ENODEV`), it's no longer found on the
  bus, or the errors keep coming.
- **Longer read timeout.** 1 s instead of 250 ms, so about four times fewer
  aborts. Packets still arrive the moment they're sent.
- **No phantom controllers.** After a receiver loss, a packet still in flight on
  another slot's thread could mark a controller as connected again. Those packets
  are now ignored.
- **One log line per loss** instead of one per reader thread, and player LEDs are
  set on the right receiver while it reopens.
- **One-command setup.** `./install.sh` does the whole setup, and `./start.sh` runs
  it automatically the first time.

A transient error now looks like this in the log, and the game never notices:

```
USB read error on slot 1 ([Errno 5] Input/Output Error), retrying
Slot 1 recovered after 1 read error
```

The fix doesn't help when a *single* controller drops on its own, for example
`Controller 2 disconnected` with nothing else around it. That is the controller's
wireless link fading: try fresh batteries and keep the receiver in sight.

## How it works

macOS has never supported the Xbox 360 wireless receiver. The old 360Controller
kext stopped working years ago. Newer userspace drivers can read the receiver, but
to show up as a system-wide gamepad they need an Apple-restricted entitlement, which
means weakening macOS security (`amfi_get_out_of_my_way`), and that doesn't even work
on current macOS 26 releases.

Cloud gaming runs in the browser, so the controller only needs to exist **inside the
page**. This project skips the operating system entirely:

```
Xbox 360 receiver ──USB──▶ helper (Python + libusb) ──WebSocket 127.0.0.1:8360──▶ Chrome extension
                                                                                      │
                               navigator.getGamepads() in xbox.com / GeForce NOW ◀────┘
```

- **Helper** (`bridge/x360bridge.py`): talks to the receiver directly through libusb.
  It decodes up to 4 controllers, lights each one's player LED and drives rumble.
- **Extension** (`extension/`): adds the controllers to the page's Gamepad API as
  standard Xbox 360 gamepads, fires `gamepadconnected` / `gamepaddisconnected`, and
  forwards `vibrationActuator` effects back to the controller.

The extension's toolbar popup shows whether the helper is running, whether the
receiver was found, and the live state of each controller.

## Requirements

- macOS 13 or newer (tested on macOS 26, Apple Silicon)
- An Xbox 360 wireless receiver (`045e:0291`, `045e:0719` or the `045e:02a9` clones)
- [Homebrew](https://brew.sh) and Python 3.10 or newer (`brew install python` if you
  don't have it; `install.sh` checks)
- Google Chrome. Other Chromium browsers (Edge, Brave) should work but are untested.

## Options

```bash
./start.sh --deadzone 0.2   # raise if the sticks drift (default 0.15)
./start.sh --simulate       # fake controller, no receiver needed (for development)
./start.sh -v               # debug logging, including every retried read
```

Older controllers often don't fully re-center their sticks. If your character or camera
moves by itself, increase `--deadzone`. Values between 0.15 and 0.25 usually work.

## Testing

- **Read-error handling, no hardware:**
  `.venv/bin/python test/test_read_retries.py` runs the helper's real read loop
  against a fake USB device that fails in scripted ways. It checks retries, a real
  unplug, a single loss report, and that no phantom controller appears.
- **Browser side, no hardware:** run `./start.sh --simulate`, then serve the test page
  with `cd test && python3 -m http.server 8000` and open
  `http://localhost:8000/gamepad-test.html`. You should see a controller whose left
  stick moves in circles, and a "Test rumble" button.
- **With your controller:** the same test page, or
  [gamepad-tester.com](https://gamepad-tester.com) (the extension is enabled there too).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Popup says *Helper: not running* | Start `./start.sh` and keep the terminal open |
| Helper says *Receiver is in use by another program* | **Steam** grabs the receiver while it runs. Quit Steam; the helper retries every 2 s |
| Helper says *No Xbox 360 wireless receiver found* | Check that `system_profiler SPUSBDataType` lists vendor `045e`. Try another port |
| Controller connected in the popup but not in the game | Reload the game tab. Make sure the site is in the list below |
| Controller won't pair | Press the receiver's button (green light blinks), then the small connect button on the top of the controller |
| One controller drops now and then, the other stays | Its wireless link is fading: fresh batteries, less distance, nothing in between |
| *Lost the receiver* comes back again and again | Run `/usr/bin/log show --last 30m --predicate 'eventMessage CONTAINS "hardware connection lost"'`. If the receiver is listed, the USB connection really drops: try another port or cable. If not, run with `-v` and open an issue with the log |

**Supported sites:** `www.xbox.com`, `play.geforcenow.com`, `gamepad-tester.com`,
`hardwaretester.com` and `localhost`. To add another site, add it to both
`content_scripts` entries in `extension/manifest.json`.

## Limitations

- Only works in the browser. It does **not** work with the native GeForce NOW app,
  native Mac games or Steam. For those, macOS needs a real system-level gamepad (see
  *How it works*).
- The helper must be running while you play.
- The headset port and chatpad are not supported.
- Tested with original controllers on `045e:0291` and `045e:0719` receivers, with up to
  two controllers at once. Reports from other receivers and bigger setups are welcome.

## Security

- The helper only listens on `127.0.0.1` and only accepts WebSocket connections from
  Chrome extensions and `localhost` pages. Other websites are rejected (HTTP 403).
- The extension requests no special permissions. It runs only on the sites listed above.
- Nothing is installed system-wide apart from Homebrew's `libusb`, and no network
  access is used beyond localhost.

## Contributing

Issues and pull requests are welcome. Some ideas:

- A **WebUSB-only version** that reads the receiver directly from the extension, with no helper
- Start the helper automatically on login (launchd agent)
- Battery level reporting
- Firefox support
- Testing other receivers and clones, and more cloud-gaming sites

To work on it, `./start.sh --simulate` plus the test page give you a full loop without
hardware. After changing the extension, click the reload icon in `chrome://extensions`
and refresh the page.

## Credits

- [Maverserker](https://github.com/Maverserker/x360-cloud-bridge) wrote the original
  project: the helper, the extension and the docs this README builds on.
- The Xbox 360 wireless protocol is documented by the Linux kernel's
  [`xpad`](https://github.com/torvalds/linux/blob/master/drivers/input/joystick/xpad.c) driver.

## License

[GPL-3.0-or-later](LICENSE), like the original. You can use, study, share and modify
this project; if you distribute a modified version, it must also be released under
the GPL with its source code.
