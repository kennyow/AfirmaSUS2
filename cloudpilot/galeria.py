import hashlib
import json
from uuid import uuid4
from functools import lru_cache
from pathlib import Path

from django import forms
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


def album_keys(index, entry, uploaded, has_changes=True):
    prefix = f'albuns/{index}'
    hidden = set(files_at(f'{prefix}/removidas')) if has_changes else set()
    originals = (
        uploaded.get(key, key) for key in entry['keys']
        if key.startswith('legado/') or key in uploaded
    )
    added = (
        f'{prefix}/fotos/{name}' for name in sorted(files_at(f'{prefix}/fotos') if has_changes else [])
        if Path(name).suffix.lower() in IMAGE_FORMATS
    )
    return [key for key in (*entry.get('links', []), *originals, *added) if photo_id(key) not in hidden]


def image_url(key):
    return key if key.startswith(('https://', 'http://')) else default_storage.url(key)


def photo_id(key):
    return hashlib.sha256(key.encode()).hexdigest()


def published_albums():
    for name in sorted(files_at('albuns-publicados'), reverse=True):
        if name.isdecimal():
            yield int(name), get_album(int(name))


def timeline_albums():
    entries = []
    for index, entry in published_albums():
        if entry['timeline']:
            photos = album_keys(index, entry, {})
            entries.append({**entry, 'titulo': entry['title'],
                            'fotos': [image_url(key) for key in photos]})
    return entries


@login_required
@require_POST
def create_album(request):
    title = request.POST.get('titulo', '').strip()
    date = request.POST.get('data', '').strip()
    category = request.POST.get('categoria', '').strip()
    color = request.POST.get('cor_borda', '#17A2B8')
    timeline = request.POST.get('timeline') == '1'
    if not title or len(title) > 200 or (timeline and not (date and category)):
        messages.error(request, 'Informe o título e, para a Linha do Tempo, a data e a categoria.')
        return redirect('midias')
    if len(color) != 7 or color[0] != '#' or any(c not in '0123456789abcdefABCDEF' for c in color[1:]):
        messages.error(request, 'Escolha uma cor válida.')
        return redirect('midias')

    links = []
    validate_url = forms.URLField(max_length=500)
    try:
        for value in request.POST.getlist('fotos'):
            if value.strip():
                link = validate_url.clean(value)
                if not link.startswith(('https://', 'http://')):
                    raise forms.ValidationError('Use um link HTTP ou HTTPS.')
                links.append(link)
    except forms.ValidationError:
        messages.error(request, 'Informe links válidos para as fotos.')
        return redirect('midias')

    files = request.FILES.getlist('arquivos')
    for file in files:
        form = UploadPublicoForm({'titulo': title}, {'arquivo': file})
        if Path(file.name).suffix.lower() not in IMAGE_FORMATS or not form.is_valid():
            messages.error(request, 'Envie fotos JPG, PNG ou WebP de até 5 MB cada.')
            return redirect('midias')

    # Keep existing numeric album addresses and use a separate namespace for new ones.
    index = uuid4().int
    keys = []
    try:
        for position, file in enumerate(files):
            extension = Path(file.name).suffix.lower()
            keys.append(default_storage.save(f'albuns/{index}/fotos/{position:04d}-{uuid4().hex}{extension}', file))
        entry = {'title': title, 'data': date, 'categoria': category, 'cor_borda': color,
                 'descricao': request.POST.get('descricao', '').strip(), 'timeline': timeline,
                 'keys': [], 'links': links}
        default_storage.save(f'albuns-publicados/{index}', ContentFile(json.dumps(entry).encode()))
    except Exception:
        for key in keys:
            try:
                default_storage.delete(key)
            except Exception:
                pass
        messages.error(request, 'Não foi possível salvar o álbum. Tente novamente.')
    else:
        messages.success(request, 'Álbum adicionado.')
    return redirect('midias')


def album_cards():
    uploaded = available_uploads()
    try:
        changed_albums, _ = default_storage.listdir('albuns')
    except FileNotFoundError:
        changed_albums = []
    changed_albums = {str(name).rstrip('/').rsplit('/', 1)[-1] for name in changed_albums}
    cards = []
    catalog = [*published_albums(), *enumerate(albums(), start=1)]
    for index, album in catalog:
        photos = album_keys(index, album, uploaded, 'timeline' in album or str(index) in changed_albums)
        cards.append({
            'index': index,
            'title': album['title'],
            'cover': image_url(photos[0]) if photos else None,
            'available': len(photos),
            'total': len(album['keys']),
        })
    return cards


@require_safe
def galeria(request):
    return render(request, 'cloudpilot/galeria.html', {'albums': album_cards()})


def get_album(index):
    catalog = albums()
    if 1 <= index <= len(catalog):
        return catalog[index - 1]
    try:
        with default_storage.open(f'albuns-publicados/{index}', 'rb') as document:
            return json.load(document)
    except FileNotFoundError as error:
        raise Http404 from error


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
        'thumbnails': [{'url': image_url(item), 'id': photo_id(item)} for item in keys],
        'photo': image_url(key) if key else None,
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
