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
