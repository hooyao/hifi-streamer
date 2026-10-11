import argparse
import logging
import logging.handlers
import os
import threading
from pathlib import Path
from .api import UnixServer, handler
from .runtime import Runtime

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
parser.add_argument('--config', type=Path, default=Path.home() / '.config/hifi-streamer')
args = parser.parse_args()
runtime = Runtime(args.repo, args.config)
log_dir = args.config / 'state'
log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
logger = logging.getLogger('hifi')
logger.setLevel(logging.INFO)
rotation = logging.handlers.RotatingFileHandler(log_dir / 'agent.log', maxBytes=1048576, backupCount=2)
rotation.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger.addHandler(rotation)
socket_dir = Path(os.environ['XDG_RUNTIME_DIR']) / 'hifi-streamer'
socket_dir.mkdir(mode=0o700, exist_ok=True)
path = socket_dir / 'agent.sock'
path.unlink(missing_ok=True)
with UnixServer(str(path), handler(runtime)) as server:
    os.chmod(path, 0o600)
    threading.Thread(target=runtime.loop, daemon=True).start()
    server.serve_forever()
