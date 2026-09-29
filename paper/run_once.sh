#!/bin/sh
set -eu
utc_hour=$(date -u +%H)
utc_minute=$(date -u +%M)
[ "$utc_hour" = "00" ] || exit 0
[ "$utc_minute" -ge 10 ] || exit 0
cd "$(dirname "$0")/.."
export PYTHONPATH=src
"${PYTHON_BIN:-python3}" -m keel paper
