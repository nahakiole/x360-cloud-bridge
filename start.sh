#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Starts the x360-cloud-bridge helper. If libusb or the Python environment is
# missing (first run), it runs ./install.sh first. Any arguments are passed
# through, e.g. ./start.sh --deadzone 0.2
set -e
cd "$(dirname "$0")"

has_libusb() { [ -e /opt/homebrew/lib/libusb-1.0.dylib ] || [ -e /usr/local/lib/libusb-1.0.dylib ]; }
if ! has_libusb || [ ! -x .venv/bin/python ]; then
  echo "First run: setting things up with ./install.sh ..."
  ./install.sh --no-open
  echo
fi

exec .venv/bin/python bridge/x360bridge.py "$@"
