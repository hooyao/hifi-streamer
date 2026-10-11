#!/bin/sh
# Temporary hardware diagnostic; restores CPU limits even when playback fails.
set -eu
test "$(id -u)" = 0
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
cat "$clock/scaling_cur_freq"
if [ "${2:-buffered}" = default ]; then
  aplay -v -D hw:CARD=II,DEV=0 "$1"
else
  aplay --buffer-time=500000 --period-time=100000 -v -D hw:CARD=II,DEV=0 "$1"
fi
