"""Discover USB audio cards without persisting ALSA enumeration numbers."""
from pathlib import Path


def discover(root=Path('/sys/class/sound')):
    result = []
    for card in sorted(root.glob('card[0-9]*')):
        device = (card / 'device').resolve()
        usb = next((p for p in (device, *device.parents) if (p / 'idVendor').exists()), None)
        if usb is None:
            continue
        def read(name):
            return (usb / name).read_text().strip() if (usb / name).exists() else ''
        vid, pid, serial = read('idVendor'), read('idProduct'), read('serial')
        identity = f'{vid}:{pid}:{serial or usb.name}'
        result.append({'id': identity, 'vendor': vid, 'product': pid, 'serial': serial,
                       'port': usb.name, 'name': read('product'), 'card': int(card.name[4:]),
                       'alsa_id': (card / 'id').read_text().strip(), 'pcm': 0})
    return result


def observe(identity, sound=Path('/sys/class/sound'), usb_root=Path('/sys/bus/usb/devices'),
            nodes=Path('/dev/snd')):
    """Distinguish USB absence from incomplete ALSA enumeration."""
    if not identity:
        return {'availability': 'unconfigured', 'reason': 'dac_unconfigured', 'device': None}
    try:
        cards = discover(sound)
        selected = next((card for card in cards if card['id'] == identity), None)
        usb = None
        for path in usb_root.iterdir():
            if not (path / 'idVendor').exists():
                continue
            read = lambda name: (path / name).read_text().strip() if (path / name).exists() else ''
            current = f"{read('idVendor')}:{read('idProduct')}:{read('serial') or path.name}"
            if current == identity:
                usb = path
                break
        if usb is None:
            return {'availability': 'missing', 'reason': 'dac_missing', 'device': None}
        incarnation = [str(usb.resolve()), (usb / 'devnum').read_text().strip()]
        if selected:
            endpoint = nodes / f"pcmC{selected['card']}D{selected['pcm']}p"
            control = nodes / f"controlC{selected['card']}"
            if endpoint.exists() and control.exists():
                for node in (endpoint, control):
                    stat = node.stat()
                    incarnation.extend([stat.st_rdev, stat.st_ino])
                return {'availability': 'ready', 'reason': None, 'device': selected,
                        'incarnation': tuple(incarnation)}
        return {'availability': 'enumerating', 'reason': 'dac_not_ready', 'device': selected,
                'incarnation': tuple(incarnation)}
    except (OSError, ValueError):
        return {'availability': 'unknown', 'reason': 'discovery_failed', 'device': None}
