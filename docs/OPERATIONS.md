# Operations

English | [简体中文](OPERATIONS.zh-CN.md)

## Host setup

Use a dedicated service account on systemd Linux. Install dependencies as root, grant audio-device access and enable linger:

```sh
sudo sh deploy/host-setup.sh
sudo usermod -aG audio "$USER"
sudo loginctl enable-linger "$USER"
```

Log out and back in after changing groups. Rootless Podman requires unique subuid/subgid ranges and crun. Run application commands as the service account:

`install.sh` checks prerequisites before writing application files. Verify the current account has a unique contiguous range of at least 65536 IDs in both `/etc/subuid` and `/etc/subgid`. Renaming a user does not reliably rename these allocations: an administrator must check ownership and unused ranges before correcting them. Do not copy another user's range or keep overlapping name/numeric-UID entries. Enable linger for the final account name; run the installer through that account's SSH login rather than root or a session with stale groups.

```sh
systemctl --user enable --now pipewire pipewire-pulse wireplumber
sh deploy/install.sh
```

## Images and initial DAC selection

Components are mpd, upmpdcli, soloist and web. Pull verified registry digests or import validated OCI exports. Registry visibility is independent of source-repository visibility.

```sh
podman pull ghcr.io/hooyao/hifi-streamer/soloist@sha256:<verified-digest>
```

Write the four immutable references to `~/.config/hifi-streamer/images.json`. Values must be full registry digest references or local `sha256:<image-id>`, not mutable tags. For local bootstrap, tag each image `localhost/hifi-<component>:dev`, then run `python3 deploy/manage.py record-images`.

For validated ARM64 exports from a successful main workflow, download the four `bootstrap-<component>-arm64` artifacts into matching component directories and transfer them to the host. Import the workflow's Docker archives with:

```sh
for component in mpd upmpdcli soloist web; do
    podman load --input "$component/image-arm64.tar.gz" || exit 1
    podman tag "docker.io/library/hifi-$component:test" "localhost/hifi-$component:dev" || exit 1
done
python3 deploy/manage.py record-images
```

The exported names resolve to `docker.io/library/...`; `localhost/...:test` is not the loaded name. Use exports from the same reviewed successful build and correct architecture. Public installation requires public GHCR **packages**, independently of repository visibility; an anonymous manifest/pull failure must be fixed or handled by validated exports before selecting hardware. Do not embed a GitHub token in application config or shell examples.

Qualified multi-architecture releases use `<source-sha>-<workflow-run-id>-<run-attempt>`. `stable` and bare source-SHA tags are compatibility aliases: a scheduled rebuild of the same source can change their digest, including the refreshed Soloist binary. Resolve the qualified release and pin its digest. Compare an export against the registry reference from that same workflow, not an older export against a newly rebuilt source alias. Feature-branch dispatch publishes its qualified release without changing production aliases.

After recording images, bootstrap the web control plane even if the DAC is not connected:

```sh
python3 deploy/manage.py apply
```

Open `http://<device-address>:8080`, select the DAC when it is available. Unset selection reports `dac_unconfigured`; an absent selected DAC reports `dac_missing`. Deployment starts web before hardware discovery, including transient sysfs failures. With no usable selection, it stops all audio services and disables existing audio units to prevent stale device mappings from starting at boot. Recovery regenerates and enables audio services when selected hardware becomes available. The web service remains enabled across reboots.

For command-line DAC selection instead:

```sh
PYTHONPATH=modules/audio-agent python3 - <<'PY'
from pathlib import Path
from hifi.config import Config
from hifi.devices import discover
devices = discover()
for device in devices:
    print(device["id"], device["name"])
with open('/dev/tty') as terminal:
    print("DAC ID: ", end="", flush=True)
    selected = terminal.readline().strip()
Config(Path.home() / ".config/hifi-streamer").update({"dac": selected}, devices)
PY
python3 deploy/manage.py apply
systemctl --user enable --now hifi-web
```

## Web configuration and volume

Open `http://<device-address>:8080`. This development release has no password login. Clients that can reach the endpoint can control the device; use it on the intended LAN. State changes still require matching Origin and the CSRF token from `/api/status`. Old `admin.json` files are ignored. Configure DAC, names, priority and source mode. Enable Spotify, supply its key and pair from the Spotify app.

DLNA direct output has no software mixer. Spotify session volume and PipeWire sink volume are separate. Soloist startup volume defaults to 100% and is configurable from 0 to 100. For unity gain use 100% session and 0dB host sink, then control listening volume on the DAC/amplifier. Lower hardware volume before increasing software volume.

First inspect `pactl list sinks` and `pactl list sink-inputs`: a DAC sink at 40% adds approximately −23.9dB even when Spotify shows 100%. Pause playback and lower DAC/amplifier volume before setting the selected sink to unity. The Spotify startup setting does not change the host sink. With a selected usable DAC, the following changes only its PipeWire sink:

```sh
PYTHONPATH=modules/audio-agent python3 - <<'PY'
from pathlib import Path
from hifi.runtime import Runtime
from hifi.pipewire import run
runtime = Runtime(Path.cwd(), Path.home()/'.config/hifi-streamer')
run('pactl', 'set-sink-volume', runtime.hardware.sink(), '100%')
PY
```

Verify 100%/0dB again after restart or re-enumeration. WirePlumber persists the selected route volume; recovery preserves gain. Fresh application configuration initializes its first available DAC to 100% once, including a DAC connected after installation. Reinstalling an existing configuration or recovering output does not force gain back to 100%. New WirePlumber routes also default to unity. A fresh Spotify installation also needs first pairing in the Spotify device list: an API key alone does not create a logged-in session. Missing hardware can stop the player during protective recovery and remove its advertisement until paused readiness returns.

The **Host output volume** form applies immediately without restarting source containers. Its current readout comes from the selected PipeWire sink; unavailable output disables the control, and mute remains unchanged. Adjustments accept integer 0–100%. `GET /api/status` exposes `output.volume`; `POST /api/output/volume` accepts `{"percent":60}` with matching Origin and the status CSRF token. This changes PipeWire sources such as Spotify, not DLNA direct ALSA. Soloist startup volume is a separate source setting.

## Source sample rate

Spotify follows Soloist's decoded Pulse PCM rather than a fixed 44.1kHz policy. Inspect `/api/status` under `sources.spotify.pcm_rate`, `pactl list sink-inputs`, and the selected `/proc/asound/card<runtime-card>/stream0`. The default clock/standby rate is a baseline, not a forced source rate. Missing PCM waits; ambiguous or unsupported formats report a source error without a hidden fixed fallback. Playback rates must be supported by both USB playback capabilities and the active host allowed-rates setting.

If Soloist supplies 44.1kHz for every track, output remains 44.1kHz because that is the observable decoded format. Matching rate does not prove the encoded-file rate, bit-perfect delivery or absence of upstream processing. Live format changes can introduce a short interruption; gain/mute remain unchanged. DLNA retains its separate direct ALSA path.

[Spotify's Soloist announcement](https://developer.spotify.com/blog/2026-08-13-introducing-spotify-soloist) specifies lossless up to 24-bit/44.1kHz. A 44.1kHz result is therefore expected for current Spotify lossless music; dynamic host following does not add upstream 96/192kHz content.

## Budgets

| Resource | Limit |
| --- | --- |
| Agent | 96MiB, 32 tasks |
| MPD / upmpdcli / Soloist / web | 128 / 96 / 256 / 32MiB |
| Container processes | 64 PIDs each |
| Agent log | 1MiB current + 2 backups |
| Container log | 2MiB k8s-file |
| Host journal | 32MiB persistent, 16MiB runtime, 4MiB files, 7 days |
| Soloist cache | 128MiB tmpfs, 100MB binary cache target |
| Diagnostics | 200 lines / 64KiB |
| Image gates: MPD / upmpdcli / Soloist / web | 200 /160 /180 /40MiB uncompressed |

Journal limits affect the whole host. Podman events and web access logging are disabled. Sessions persist; cache does not. Podman vfs storage can exceed final image size due to duplicated layers. Preserve current/rollback images; avoid global prune on shared hosts.

## Updates

```sh
python3 deploy/update.py release.json
```

Soloist and web update independently. MPD/upmpdcli need a coordinated DLNA release. Record verified current metadata in `<component>-release.json` first.

Manifests contain component, immutable image, device-inspected size and data_version=1; Soloist also has expires_at from its binary build timestamp. Updates require idle output, space, compatible data and an unexpired rollback image. A process lock serializes updates. Failure restores the original service and metadata; HTTP/WebSocket health checks do not replace audio acceptance.

The daily timer reads HTTPS channels from `update-channels.json` and stores candidates. No channels means no network requests. Web update/rollback uses those verified candidates.

## Inspection

```sh
systemctl --user is-active hifi-agent hifi-mpd hifi-upmpdcli hifi-soloist hifi-web
podman stats --no-stream
journalctl --user -u hifi-agent -n 50 --no-pager
```

Do not publish raw inspection output containing secrets. See [troubleshooting](debugging/troubleshooting.md) and [testing](testing/README.md).
