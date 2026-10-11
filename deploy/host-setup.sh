#!/bin/sh
set -eu
test "$(id -u)" = 0
apt-get update
apt-get install -y --no-install-recommends podman crun uidmap slirp4netns pipewire pipewire-pulse wireplumber pulseaudio-utils alsa-utils flac python3 psmisc
install -d /etc/systemd/journald.conf.d
install -m 644 "$(dirname "$0")/journald-hifi.conf" /etc/systemd/journald.conf.d/hifi-streamer.conf
systemctl restart systemd-journald
echo 'Enable linger for the selected service account and run install.sh as that account.'
