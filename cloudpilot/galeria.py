from pathlib import Path

from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_safe

from core.legacy_media import media_keys


@require_safe
def galeria(request):
    try:
        _, uploaded = default_storage.listdir('galeria')
    except FileNotFoundError:
        uploaded = []

    keys = sorted(set(media_keys().values())) + [
        f'galeria/{name}' for name in sorted(uploaded)
        if Path(name).suffix.lower() in {'.jpg', '.jpeg', '.png'}
    ]
    page = Paginator(keys, 36).get_page(request.GET.get('pagina'))
    photos = [default_storage.url(key) for key in page]
    return render(request, 'cloudpilot/galeria.html', {'photos': photos, 'page': page})
