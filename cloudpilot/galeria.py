import hashlib
import json
from uuid import uuid4
from functools import lru_cache
from pathlib import Path

from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST, require_safe

from .forms import IMAGE_FORMATS, UploadPublicoForm


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


def album_keys(index, entry, uploaded):
    prefix = f'albuns/{index}'
    hidden = set(files_at(f'{prefix}/removidas'))
    originals = (
        uploaded.get(key, key) for key in entry['keys']
        if key.startswith('legado/') or key in uploaded
    )
    added = (
        f'{prefix}/fotos/{name}' for name in sorted(files_at(f'{prefix}/fotos'))
        if Path(name).suffix.lower() in IMAGE_FORMATS
    )
    return [key for key in (*originals, *added) if photo_id(key) not in hidden]


def photo_id(key):
    return hashlib.sha256(key.encode()).hexdigest()


def album_cards():
    uploaded = available_uploads()
    cards = []
    for index, album in enumerate(albums(), start=1):
        photos = album_keys(index, album, uploaded)
        cards.append({
            'index': index,
            'title': album['title'],
            'cover': default_storage.url(photos[0]) if photos else None,
            'available': len(photos),
            'total': len(album['keys']),
        })
    return cards


@require_safe
def galeria(request):
    return render(request, 'cloudpilot/galeria.html', {'albums': album_cards()})


def get_album(index):
    catalog = albums()
    if not 1 <= index <= len(catalog):
        raise Http404
    return catalog[index - 1]


@xframe_options_sameorigin
@require_safe
def album(request, index):
    entry = get_album(index)
    keys = album_keys(index, entry, available_uploads())
    page = Paginator(keys, 1).get_page(request.GET.get('foto'))
    key = page.object_list[0] if keys else None
    return render(request, 'cloudpilot/album.html', {
        'album': entry,
        'index': index,
        'embedded': request.GET.get('interno') == '1',
        'page': page,
        'photo': default_storage.url(key) if key else None,
        'photo_id': photo_id(key) if key else '',
    })


@login_required
@require_POST
def change_album(request, index):
    entry = get_album(index)
    if request.POST.get('action') == 'remover':
        keys = album_keys(index, entry, available_uploads())
        target = request.POST.get('photo_id')
        if not any(photo_id(key) == target for key in keys):
            raise Http404
        marker = f'albuns/{index}/removidas/{target}'
        if not default_storage.exists(marker):
            default_storage.save(marker, ContentFile(b'1'))
    else:
        form = UploadPublicoForm({'titulo': 'Foto do álbum'}, request.FILES)
        if not form.is_valid():
            messages.error(request, 'Envie uma imagem JPG, PNG ou WebP válida de até 5 MB.')
        else:
            file = form.cleaned_data['arquivo']
            extension = Path(file.name).suffix.lower()
            if extension in IMAGE_FORMATS:
                default_storage.save(f'albuns/{index}/fotos/{uuid4().hex}{extension}', file)
            else:
                messages.error(request, 'Selecione uma imagem JPG, PNG ou WebP.')
    url = reverse('pilot:album', args=[index])
    return redirect(f'{url}?interno=1' if request.POST.get('interno') == '1' else url)
