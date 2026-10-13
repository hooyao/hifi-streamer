# Troubleshooting

English | [简体中文](troubleshooting.zh-CN.md)

## No sound

Inspect actual playback and route independently:

```sh
pactl list short sinks
pactl list short sink-inputs
pw-link -l
cat /proc/asound/card*/stream0
```

A playing UI does not prove hardware output. Confirm the selected USB DAC is present, the stream targets it and the sink is not suspended. Keep one audio server: PipeWire Pulse; do not start a second PulseAudio daemon.

## Low volume or unexpected rate

Check source session volume, sink-input volume, sink volume and hardware mixer. Fresh Soloist initial_volume and host output default to 100%; an existing sink at 40% still adds about 23.9dB attenuation. Inspect the actual host-volume readout in the control plane; muted or unavailable output is shown explicitly. Lower hardware listening volume before correcting gain.

Check `pw-metadata -n settings 0` and the installed allowed-rates configuration. A 44.1kHz stream at 48kHz indicates resampling. DSD64 DoP uses 176.4kHz transport; do not interpret it as a Spotify format.

Compare decoded PCM to the running driver graph and USB rate. `clock.rate` metadata is a default preference and can remain 44100 while an allowed driver graph runs at 48000; it is insufficient by itself to diagnose conversion. Use `pw-top`/negotiated node formats and USB feedback. Correct a source `rate_error` or retry a supported format; do not force 44100 to hide it. Rate changes park the stream before closing/reopening the selected sink because a live Pulse client can otherwise keep the DAC occupied.

## Busy or missing DAC

MPD must keep a standby output available after a standalone restart. Its persisted direct-output state may be disabled; if both outputs are disabled, a new DLNA request can fail before arbitration observes a playing edge. Deployment enables standby at startup and disables it during direct playback handoff.

`Device or resource busy` indicates another owner. Confirm MPD direct output and PipeWire are not active on the DAC together. Do not use software state alone as proof of release.

`No such device` requires fresh USB discovery. Re-enumeration can invalidate a container bind mount even when the card number is unchanged. Preserve session data while rebuilding mappings.

Kernel `cannot set/get freq ... err -71` means a USB protocol transaction failed, not that Spotify selected the wrong audio format. If it is followed by `USB disconnect` and the DAC disappears from `lsusb`, service restarts cannot restore a device that the kernel no longer enumerates. Check physical DAC power/input, cable, port and supply; disconnect unrelated USB storage for a controlled comparison. Power-cycle the DAC when needed and verify enumeration before replay. A successful comparison does not by itself prove the removed storage or cable was the cause. Do not add endless controller resets to the audio recovery loop.

## Pops and discontinuities

Isolate the path: ALSA-only generated tone, PipeWire tone, then the service stream. Record CPU frequency, USB errors, route and timing under the same conditions. Do not keep changing several variables simultaneously.

On the qualified M401A/kernel profile, CPU PLL errors during scaling are associated with discontinuities; fixed 1.2GHz is a tested workaround. See [hardware profile](../testing/m401a.md). Larger buffers alone are not an established fix. Tone/rate checks do not replace listening acceptance.

## Rootless services

Check the service account's audio group, subuid/subgid allocation and linger. Use its `systemctl --user` and `podman`; root's containers are a different namespace. Read XDG_RUNTIME_DIR instead of hard-coding a UID.

## Soloist startup and control

The binary needs its compatible glibc and runtime libraries in the container. Enable the loopback WebSocket endpoint for actual state/control. Inspect version and build expiry; exit 10 must not be restarted forever.

Podman 4.3 rejects uid/gid options on the tested tmpfs mount. The cache uses a dedicated 128MiB tmpfs with mode 1777 inside the isolated container. Mount the Pulse socket directory, not a stale single socket.

## Protocol and update failures

Valid HTTP MP3 accompanied by `cannot seek!`, `mpg123_getformat() failed` and `unrecognized file` can indicate a decoder callback defect rather than a corrupt file or NAS authentication failure. Confirm HTTP 200/206, audio/mpeg and MPEG frame headers without publishing temporary media URLs. The patched mpg123 callback accepts bounded SET/CUR/known-END positions and registers audio/mpeg. Qualify both file decoding and HTTP transport; a plugin appearing in `decoders` alone does not establish stream compatibility. Preserve the 16MiB implicit-cache and 128MiB container budgets.

Compare the controller's original-file metadata with the actual delivered container and decoded rate. An original high-rate FLAC can arrive as 44.1kHz MP3 when a controller converts it; increasing the DAC rate cannot recover that source. Verify the renderer's protocol advertisement before attributing a controller change to the decoder. Stop all controllers during synthetic tests and reject a fixture URI replaced by another playback request.

For cgroup OOM or increasing HTTP playback memory, see [MPD memory budgets](mpd-memory.md).

HTTP seek requires Range support from the media source. Renderer capabilities must match actual output controls; do not add unsupported MPD parameters such as close_on_pause.

Update candidates require immutable references, compatible metadata, enough space, idle output and a viable rollback version. Use recent bounded logs; do not publish credentials or full inspect output.
