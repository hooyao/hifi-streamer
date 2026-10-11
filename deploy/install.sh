#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
repo=$(pwd)
install -d "$HOME/.config/pipewire/pipewire.conf.d"
install -m 644 "$repo/modules/audio-runtime/10-rates.conf" "$HOME/.config/pipewire/pipewire.conf.d/hifi-rates.conf"
install -d -m 700 "$HOME/.config/hifi-streamer" "$HOME/.config/containers" "$HOME/.config/systemd/user"
# Defaults are local to this rootless account; no rootful management socket is exposed.
cat > "$HOME/.config/containers/containers.conf" <<'EOF'
[containers]
log_driver="k8s-file"
log_size_max=2097152
[engine]
events_logger="none"
EOF
PYTHONPATH="$repo/modules/audio-agent" python3 -c 'from hifi.config import Config; from pathlib import Path; Config(Path.home()/".config/hifi-streamer")'
cat > "$HOME/.config/systemd/user/hifi-agent.service" <<EOF
[Unit]
Description=HiFi Streamer audio agent
After=network-online.target pipewire-pulse.service
[Service]
Environment=PYTHONPATH=$repo/modules/audio-agent
ExecStart=/usr/bin/python3 -m hifi --repo $repo
Restart=on-failure
RestartSec=5
MemoryMax=96M
TasksMax=32
StandardOutput=null
StandardError=journal
LogRateLimitIntervalSec=30s
LogRateLimitBurst=20
[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now hifi-agent
cat > "$HOME/.config/systemd/user/hifi-update-check.service" <<EOF
[Unit]
Description=HiFi Streamer bounded update observation
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $repo/deploy/check-updates.py
MemoryMax=48M
StandardOutput=null
StandardError=journal
EOF
cat > "$HOME/.config/systemd/user/hifi-update-check.timer" <<'EOF'
[Unit]
Description=HiFi Streamer daily update observation
[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true
[Install]
WantedBy=timers.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now hifi-update-check.timer
echo 'Admin password is stored in ~/.config/hifi-streamer/admin.json (private file).'
