import json
from functools import lru_cache
from pathlib import Path

from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe


@lru_cache(maxsize=1)
def albums():
    return json.loads(Path(__file__).with_name('albuns.json').read_text(encoding='utf-8'))


def files_at(prefix):
    try:
        _, names = default_storage.listdir(prefix)
    except FileNotFoundError:
        return []
    return names


def available_uploads():
    paths = {}
    for prefix in [*(f'galeria/lote-{n:02d}' for n in range(1, 6)), 'galeria']:
        paths.update({f'galeria/{name}': f'{prefix}/{name}' for name in files_at(prefix)})
    return paths


def album_photos(album, uploaded):
    return [
        default_storage.url(uploaded.get(key, key))
        for key in album['keys']
        if key.startswith('legado/') or key in uploaded
    ]


def album_cards():
    uploaded = available_uploads()
    cards = []
    for index, album in enumerate(albums(), start=1):
        photos = album_photos(album, uploaded)
        cards.append({
            'index': index,
            'title': album['title'],
            'cover': photos[0] if photos else None,
            'available': len(photos),
            'total': len(album['keys']),
        })
    return cards


@require_safe
def galeria(request):
    return render(request, 'cloudpilot/galeria.html', {'albums': album_cards()})


@require_safe
def album(request, index):
    catalog = albums()
    if not 1 <= index <= len(catalog):
        raise Http404
    entry = catalog[index - 1]
    photos = album_photos(entry, available_uploads())
    page = Paginator(photos, 1).get_page(request.GET.get('foto'))
    return render(request, 'cloudpilot/album.html', {
        'album': entry,
        'page': page,
        'photo': page.object_list[0] if photos else None,
    })
