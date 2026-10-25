#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# One-time setup for x360-cloud-bridge on macOS:
#   1. installs libusb with Homebrew if it is missing
#   2. creates the Python environment in .venv (needs Python 3.10 or newer)
#   3. shows you where the Chrome extension is so you can load it
# Safe to run again; it only does what is still missing.
#
#   ./install.sh            full setup
#   ./install.sh --no-open  don't open Finder or touch the clipboard (used by start.sh)
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

OPEN=1
for arg in "$@"; do
  case "$arg" in
    --no-open) OPEN=0 ;;
    -h|--help) sed -n '3,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$*" >&2; exit 1; }

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Note: this project is made for macOS. On Linux the kernel's xpad driver already supports the receiver."
fi

bold "1/3 libusb"
has_libusb() { [ -e /opt/homebrew/lib/libusb-1.0.dylib ] || [ -e /usr/local/lib/libusb-1.0.dylib ]; }
if has_libusb; then
  ok "libusb is installed"
elif command -v brew >/dev/null 2>&1; then
  echo "  Installing libusb with Homebrew..."
  brew install libusb
  has_libusb || fail "libusb still not found after brew install"
  ok "libusb installed"
else
  fail "Homebrew is needed to install libusb. Get it from https://brew.sh, then run ./install.sh again."
fi

bold "2/3 Python environment"
py_ok() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; }
if [ -x .venv/bin/python ] && py_ok .venv/bin/python && .venv/bin/python -c 'import usb, websockets' 2>/dev/null; then
  ok ".venv is ready ($(.venv/bin/python --version))"
else
  PY=""
  for candidate in python3 python3.14 python3.13 python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1 && py_ok "$candidate"; then PY="$candidate"; break; fi
  done
  [ -n "$PY" ] || fail "Python 3.10 or newer is needed. Install it with:  brew install python"
  echo "  Creating .venv with $($PY --version)..."
  rm -rf .venv
  "$PY" -m venv .venv
  .venv/bin/pip install --quiet --disable-pip-version-check -r bridge/requirements.txt
  ok ".venv created"
fi

bold "3/3 Chrome extension"
EXT="$ROOT/extension"
if [ "$OPEN" = 1 ]; then
  printf '%s' "$EXT" | pbcopy 2>/dev/null && CLIP=1 || CLIP=0
  open -R "$EXT/manifest.json" 2>/dev/null || true
fi
cat <<EOF
  Load it once in Chrome:
    1. Open chrome://extensions
    2. Turn on "Developer mode" (top right)
    3. Click "Load unpacked" and pick this folder:
       $EXT
EOF
if [ "$OPEN" = 1 ]; then
  [ "${CLIP:-0}" = 1 ] && echo "       (The path is on your clipboard: in the folder dialog press Cmd+Shift+G and paste.)"
  echo "       (It is also shown in Finder; you can drag the folder into the dialog.)"
fi

if pgrep -xq steam_osx 2>/dev/null || pgrep -xq Steam 2>/dev/null; then
  echo
  echo "  Heads-up: Steam is running. It grabs the receiver, so quit Steam before you play."
fi

echo
bold "Done. Start the bridge with:  ./start.sh"
