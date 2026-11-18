"""Persist video additions and removals without overwriting the bundled catalog."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def names(prefix):
    try:
        return default_storage.listdir(prefix)[1]
    except FileNotFoundError:
        return []


def catalog():
    path = Path(settings.DATA_DIR) / 'videos.json'
    originals = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    records = []
    for index, item in enumerate(originals):
        identity = json.dumps([index, item], sort_keys=True, ensure_ascii=False)
        records.append({**item, 'removal_id': str(int(hashlib.sha256(identity.encode()).hexdigest()[:32], 16))})
    for name in sorted(names('videos-publicados')):
        if name.endswith('.json'):
            with default_storage.open(f'videos-publicados/{name}', 'rb') as stream:
                item = json.load(stream)
            records.append({**item, 'removal_id': str(int(name[:-5], 16))})
    removed = set(names('videos-removidos'))
    return [item for item in records if item['removal_id'] not in removed]


def add(item):
    default_storage.save(f'videos-publicados/{uuid4().hex}.json',
                         ContentFile(json.dumps(item, ensure_ascii=False).encode()))


def remove(identity):
    if not any(item['removal_id'] == str(identity) for item in catalog()):
        return False
    key = f'videos-removidos/{identity}'
    if not default_storage.exists(key):
        default_storage.save(key, ContentFile(b'1'))
    return True
