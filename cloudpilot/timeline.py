"""Merge bundled TimelineJS events with durable, independently stored R2 records."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

PREFIX = 'timeline-dinamica'


def names(prefix):
    try:
        return default_storage.listdir(prefix)[1]
    except FileNotFoundError:
        return []


def document():
    path = Path(settings.DATA_DIR) / 'linhadotempodinamica.json'
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'title': {}, 'events': []}
    if not isinstance(data, dict) or not isinstance(data.get('events'), list):
        raise ValueError('Formato inválido da Linha do Tempo Dinâmica.')
    data.setdefault('title', {})
    if not getattr(settings, 'PORTAL_PREVIEW', False):
        return data
    events = []
    for index, event in enumerate(data['events']):
        event = event.copy()
        identity = json.dumps([index, event], sort_keys=True, ensure_ascii=False)
        event['removal_id'] = str(int(hashlib.sha256(identity.encode()).hexdigest()[:32], 16))
        events.append(event)
    for name in sorted(names(f'{PREFIX}/eventos')):
        if name.endswith('.json'):
            with default_storage.open(f'{PREFIX}/eventos/{name}', 'rb') as stream:
                event = json.load(stream)
            event['removal_id'] = str(int(name[:-5], 16))
            events.append(event)
    removed = set(names(f'{PREFIX}/removidos'))
    data['events'] = [event for event in events if event['removal_id'] not in removed]
    return data


def add(event):
    key = f'{PREFIX}/eventos/{uuid4().hex}.json'
    default_storage.save(key, ContentFile(json.dumps(event, ensure_ascii=False).encode()))


def remove(identity):
    if not any(event['removal_id'] == str(identity) for event in document()['events']):
        return False
    key = f'{PREFIX}/removidos/{identity}'
    if not default_storage.exists(key):
        default_storage.save(key, ContentFile(b'1'))
    return True
