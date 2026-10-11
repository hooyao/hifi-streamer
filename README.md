# HiFi Streamer

English | [简体中文](README.zh-CN.md)

A modular network audio renderer for low-cost Linux ARM devices and external USB DACs.

HiFi Streamer receives DLNA audio through upmpdcli and MPD, and Spotify Connect audio through Soloist. A host agent coordinates access to one DAC, while a web interface provides device selection and source configuration.

## Features

- Required DLNA renderer with direct ALSA output, source-rate PCM playback and device-dependent DSD over PCM (DoP).
- Optional Spotify Connect source using Soloist and the host PipeWire Pulse server.
- Automatic source handoff, configurable priority and fixed-source modes.
- USB DAC identification and recovery after unplug/replug.
- Rootless Podman containers, bounded logs, resource limits and image-size gates.
- Independently versioned source adapters for future integrations.

## Project status

The initial implementation is under validation. It is not yet a generally qualified production release.

Current hardware coverage is documented in the [test guide](docs/testing/README.md). Gapless playback, Native DSD and compatibility with arbitrary controllers or DACs are not certified. Roon, Apple Music and Amazon Music are not implemented.

## Requirements

- Linux with systemd, Python 3.11 or later and an audio-capable USB DAC.
- Podman 4.3 or later with crun and rootless user namespaces.
- PipeWire, pipewire-pulse and WirePlumber.
- A dedicated service account with audio-device access and systemd linger.
- A LAN that permits DLNA discovery and access to the controller-provided audio URLs.
- A Soloist API key and a compatible Spotify account for Spotify playback.

ARM64 and AMD64 images are built by GitHub Actions. Hardware qualification currently covers the [M401A profile](docs/testing/m401a.md).

## Getting started

Clone the repository on the target host:

```sh
git clone https://github.com/hooyao/hifi-streamer.git
cd hifi-streamer
sudo sh deploy/host-setup.sh
```

Continue with [installation and configuration](docs/OPERATIONS.md) to provision the service account, load immutable images, select the DAC and start the services. Image-registry access must be verified before installation; an OCI export from a successful build is an alternative bootstrap input.

Open `http://<device-address>:8080` after deployment. Use the generated device-admin password, configure the DAC and enable Spotify only when its API key is available. Playback volume is controlled by the source and DAC; verify both before listening.

## Audio paths

```text
DLNA controller -> upmpdcli -> MPD -> ALSA -> USB DAC
Spotify app     -> Soloist -> PipeWire    -> USB DAC
Web UI          -> audio-agent -> source adapters and DAC arbitration
```

MPD decodes compressed audio. DoP transports DSD in PCM frames; neither the configuration nor sample-rate inspection proves bit-perfect output.

## Testing

Run dependency-free unit tests on Linux:

```sh
python3 -m unittest discover -s tests -v
```

Hardware tests can change playback state. See the [test guide](docs/testing/README.md) for DLNA, source-handoff, restart, hotplug and soak tests.

## Documentation

- [Operations](docs/OPERATIONS.md)
- [Architecture](docs/design/AUDIO-ARCHITECTURE.md)
- [Source-module contract](docs/design/SOURCE-MODULES.md)
- [Troubleshooting](docs/debugging/troubleshooting.md)
- [Testing](docs/testing/README.md)

## Contributing

Changes use OpenSpec to define behavior, implementation decisions and verifiable acceptance criteria. See [Contributing](CONTRIBUTING.md) for the proposal, specification, implementation and review workflow.

Code comments and docstrings are written in English. Maintained documentation has English and Simplified Chinese editions with reciprocal language links.

## License

A project license has not been selected. Dependencies and bundled binaries retain their upstream license terms.
