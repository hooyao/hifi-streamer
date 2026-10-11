#!/usr/bin/env python3
"""Bounded daily release observation; downloads metadata, never changes a player."""
import datetime
import json
import logging
import logging.handlers
import urllib.request
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.config import atomic_json
from hifi.maintenance import validate_candidate

config = Path.home()/'.config/hifi-streamer'
state = config/'state'
state.mkdir(parents=True,exist_ok=True)
logger = logging.getLogger('update-check')
logger.setLevel(logging.INFO)
logger.addHandler(logging.handlers.RotatingFileHandler(state/'updates.log',maxBytes=262144,backupCount=1))
channels = config/'update-channels.json'
if channels.exists():
    urls = json.loads(channels.read_text())
    result = {}
    for component,url in urls.items():
        if component not in ('soloist','web') or not url.startswith('https://'):
            raise ValueError('invalid release channel')
        try:
            with urllib.request.urlopen(url,timeout=15) as response:
                raw = response.read(16385)
            if len(raw)>16384:
                raise ValueError('release metadata too large')
            candidate = json.loads(raw)
            if candidate.get('component') != component:
                raise ValueError('release component differs')
            validate_candidate(candidate)
            current_path = config/f'{component}-release.json'
            current = json.loads(current_path.read_text()) if current_path.exists() else {}
            result[component] = {'available':candidate.get('image') != current.get('image'),'candidate':candidate}
        except Exception as error:
            result[component] = {'error':type(error).__name__}
            logger.warning('%s metadata check failed: %s',component,type(error).__name__)
    atomic_json(state/'updates.json',result)
