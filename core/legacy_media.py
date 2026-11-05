import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

GOOGLE_MEDIA = re.compile(r'https?://(?:drive\.google\.com|docs\.google\.com|drive\.usercontent\.google\.com|(?:[\w-]+\.)?googleusercontent\.com)[^\s<>"\']*')


@lru_cache(maxsize=1)
def media_keys():
    return json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))


def replace_legacy_media(text, media_url, placeholder):
    def replace(match):
        parsed = urlsplit(match[0])
        if parsed.hostname == 'lh3.googleusercontent.com' and parsed.path.startswith(('/gps-cs-s/', '/grass-cs/')):
            return match[0]
        path_id = re.search(r'/d/([\w-]+)', parsed.path)
        file_id = path_id[1] if path_id else parse_qs(parsed.query).get('id', [''])[0]
        key = media_keys().get(file_id)
        return f'{media_url.rstrip("/")}/{key}' if key else placeholder

    return GOOGLE_MEDIA.sub(replace, text)
