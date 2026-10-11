#!/bin/sh
# Verified M401A test-fixture workaround, not a generic ARM default.
set -eu
clock=/sys/devices/system/cpu/cpu0/cpufreq
printf '%s' 1200000 > "$clock/scaling_min_freq"
printf '%s' 1200000 > "$clock/scaling_max_freq"
