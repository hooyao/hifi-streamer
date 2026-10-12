import shlex
import socket
import uuid


class MPD:
    def __init__(self, hardware, host='127.0.0.1', port=6600):
        self.hardware, self.host, self.port = hardware, host, port
        self.instance = str(uuid.uuid4())

    def command(self, text):
        with socket.create_connection((self.host, self.port), timeout=2) as sock:
            sock.settimeout(2)
            stream = sock.makefile('rwb')
            if not stream.readline().startswith(b'OK MPD '):
                raise RuntimeError('invalid MPD greeting')
            stream.write((text + '\n').encode())
            stream.flush()
            rows = []
            while True:
                line = stream.readline().decode().strip()
                if line == 'OK':
                    return rows
                if line.startswith('ACK') or not line:
                    raise RuntimeError('MPD command failed')
                rows.append(line)

    def output(self, name, enabled):
        outputs, current = {}, None
        for row in self.command('outputs'):
            key, _, value = row.partition(': ')
            if key == 'outputid':
                current = value
            elif key == 'outputname':
                outputs[value] = current
        if name not in outputs:
            raise RuntimeError('MPD output missing')
        self.command(('enableoutput ' if enabled else 'disableoutput ') + outputs[name])

    def snapshot(self):
        values = dict(row.split(': ', 1) for row in self.command('status') if ': ' in row)
        return {'running': True, 'authenticated': True, 'active': True,
                'playback': {'play':'playing', 'pause':'paused', 'stop':'stopped'}.get(values.get('state'), 'unknown'),
                'health': 'healthy', 'format': values.get('audio'), 'elapsed': values.get('elapsed'),
                'error': values.get('error')}

    def release(self):
        if self.snapshot()['playback'] != 'stopped':
            self.command('pause 1')
        self.output('standby', True)
        self.output('direct', False)

    def acquire(self, generation):
        self.hardware.for_direct()
        # Resume before exposing the DAC so a subsequent controller Pause wins.
        self.command('pause 0')
        self.output('direct', True)
        self.output('standby', False)
