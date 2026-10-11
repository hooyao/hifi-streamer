import json
from pathlib import Path


def load(directory):
    modules = {}
    for path in Path(directory).glob('*/module.json'):
        module = json.loads(path.read_text())
        if module['interface_version'] != 1 or module['id'] in modules:
            raise ValueError('incompatible or duplicate module')
        modules[module['id']] = module
    if 'dlna' not in modules:
        raise ValueError('required DLNA module missing')
    return modules
