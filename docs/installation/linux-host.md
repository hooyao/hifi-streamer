# Linux host installation

English | [简体中文](linux-host.zh-CN.md)

Use this guide to prepare a dedicated systemd Linux host, including x86-64 Ubuntu Server. Follow [operations](../OPERATIONS.md) for application installation and resource limits. Host networking remains an administrator-managed prerequisite.

## Architecture and service account

Check `uname -m`: `x86_64` requires AMD64 images; `aarch64` requires ARM64 images. The OS image must also match the processor's instruction set. Standard Ubuntu Server includes tools useful for SSH maintenance; minimized installations may need additional packages.

Verify SSH public-key authentication before changing networking. Enable linger, grant audio access and reconnect after group changes. Validate subordinate ID allocations with `deploy/preflight.py`. Run application commands as the service account: root's containers are a different namespace. Generate audio units from the destination's DAC discovery rather than copying another host's card numbers or units.

## Multiple Ethernet ports

An installer may configure DHCP only on the connected port. Inspect configuration and runtime state:

```sh
ip -br address
networkctl list
sudo netplan get
systemctl cat systemd-networkd-wait-online.service
systemctl --failed
```

For Netplan/systemd-networkd hosts, every port intended for DHCP needs `dhcp4: true`; an empty Ethernet definition does not enable it. Preserve existing MAC matching, renaming, static addresses, DNS and routes. Ports have distinct MAC addresses and can obtain different leases. Verify the SSH destination after switching ports; do not embed a lease in application source or audio units.

If either port should satisfy startup, use an explicit any-port policy. This example belongs in `/etc/systemd/system/systemd-networkd-wait-online.service.d/90-any-ethernet.conf`; substitute the host's actual interface names and verify the executable path:

```ini
[Service]
ExecStart=
ExecStart=/usr/lib/systemd/systemd-networkd-wait-online --any --ipv4 --interface=enp1s0:routable --interface=enp2s0:routable --timeout=30
```

The late drop-in clears earlier `ExecStart` entries, including Netplan-generated waits for all interfaces. It checks routable IPv4, not DNS. Marking an unused interface optional is a separate policy, suitable when that port should never delay boot.

Back up network files outside `/etc/netplan`. Validate Netplan changes with `netplan generate` and apply them during maintenance with console access available. Reload systemd after changing its drop-in, restart the wait service and inspect its effective command/result. Verify a subsequent boot and DHCP on each intended port. With no address, the bounded wait can still fail. Disabling cloud-init or every online wait is not a general unplugged-port fix.

## Images and authentication

Use all four components from one successful qualified CI release. Resolve its source-SHA/run/attempt tag to immutable registry digests before recording `images.json`. Verify anonymous access, pulled architecture and native CI image identity. Record update baselines using destination-inspected sizes and the matching Soloist expiry. A same-source scheduled rebuild can contain a different Soloist binary; do not mix its metadata with an older image.

Keep API keys in private service-account configuration with mode `0600`. Enter the key through the control plane or transfer only the secret through a helper that never prints it. Do not copy another host's Spotify session instead of pairing. A valid API key can start Soloist while its session remains unauthenticated; select the new renderer in Spotify for first pairing.

Use distinct renderer names on a shared LAN. Tests must target the intended renderer. `dlna_smoke.py --name` matches a prefix, so use one unique on that LAN. Inspect other scripts' discovery behavior before using them with multiple renderers.

## Output and acceptance

Confirm the DAC's physical input, output mode, hardware volume and amplifier settings before comparing loudness. Then inspect the Soloist session, Pulse stream, selected sink and ALSA mixer independently. A 100% startup setting does not establish every live stage's gain.

DLNA uses direct ALSA with `mixer_type "none"`; its fixed digital level is independent of PipeWire output volume. A controller slider must not add software attenuation or change DAC gain through DLNA. See [fixed-level DLNA](../debugging/troubleshooting.md#fixed-level-dlna-and-controller-volume-requests) for rejected requests and capability limitations.

After reboot, verify web access, actual volume, selected-device health and service startup. Test the installed PipeWire/WirePlumber versions instead of assuming another host's behavior. Use the [test guide](../testing/README.md) for formats, controls, rates, persistence and handoffs. Inspect graph rates with bounded batch output:

```sh
pw-top --batch-mode --iterations 3
```

Compare the running selected driver's graph rate with decoded PCM and USB output. An empty monitor result fails observation. Source-rate smoke currently requires a paired, running Soloist because it pauses the real session before injecting synthetic PCM.

DLNA format checks, synthetic PCM, reboot checks and listening acceptance establish different things. They do not collectively replace a completed Spotify→DLNA→Spotify handoff test. Preserve failed assertions or missing final reports as incomplete acceptance until investigated; subsequent manual playback does not erase them.

Keep generated reports, private URLs, device inventories and raw logs outside version control. Documentation contains reproducible procedures and support boundaries.
