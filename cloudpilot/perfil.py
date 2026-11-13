import logging
from pathlib import Path
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db import connection
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import IMAGE_FORMATS, UploadPublicoForm


@login_required
@require_http_methods(['GET', 'POST'])
def perfil(request):
    if request.method == 'POST':
        form = UploadPublicoForm({'titulo': 'Foto de perfil'}, request.FILES)
        if form.is_valid() and Path(form.cleaned_data['arquivo'].name).suffix.lower() in IMAGE_FORMATS:
            photo = form.cleaned_data['arquivo']
            extension = Path(photo.name).suffix.lower()
            key = None
            try:
                key = default_storage.save(f'avatares/{uuid4().hex}{extension}', photo)
                # Use one statement so concurrent first uploads do not race on insertion.
                with connection.cursor() as cursor:
                    cursor.execute(
                        'INSERT INTO cloudpilot_fotoperfil (usuario_id, arquivo) VALUES (%s, %s) '
                        'ON CONFLICT(usuario_id) DO UPDATE SET arquivo = excluded.arquivo',
                        [request.user.pk, key],
                    )
            except Exception:
                logging.getLogger(__name__).exception('Falha ao salvar foto de perfil.')
                if key:
                    try:
                        default_storage.delete(key)
                    except Exception:
                        logging.getLogger(__name__).exception('Falha ao limpar foto de perfil.')
                messages.error(request, 'Não foi possível salvar a foto.')
            else:
                messages.success(request, 'Foto de perfil atualizada.')
            return redirect('perfil_usuario')
        messages.error(request, 'Envie uma imagem JPG, PNG ou WebP de até 5 MB.')
    return render(request, 'cloudpilot/perfil.html')
