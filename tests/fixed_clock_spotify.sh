#!/bin/sh
# Device-only diagnosis: restore CPU limits, no persistent host changes.
set -eu
test "$(id -u)" = 0
account=$1
repo=$2
clock=/sys/devices/system/cpu/cpu0/cpufreq
old_min=$(cat "$clock/scaling_min_freq")
old_max=$(cat "$clock/scaling_max_freq")
restore() {
  printf '%s' "$old_min" > "$clock/scaling_min_freq"
  printf '%s' "$old_max" > "$clock/scaling_max_freq"
}
trap restore EXIT HUP INT TERM
printf '%s' 1200000 > "$clock/scaling_min_freq"
printf '%s' 1200000 > "$clock/scaling_max_freq"
service_uid=$(id -u "$account")
runuser -u "$account" -- env XDG_RUNTIME_DIR="/run/user/$service_uid" PYTHONPATH="$repo/modules/audio-agent" \
  python3 "$repo/tests/spotify_fixed_path.py" "$repo"
