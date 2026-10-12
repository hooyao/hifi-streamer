#!/bin/sh
set -eu
if [ "${1:-}" = "--version" ]; then exec soloist --version; fi
test -s /run/secrets/spotify-key
exec soloist --device-name "${DEVICE_NAME:-HiFi Streamer Spotify}" --api-key "$(cat /run/secrets/spotify-key)" --initial-volume "${INITIAL_VOLUME:-100}" --cache-size 100 --ws 127.0.0.1:24879
