import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.files.storage import default_storage
from django.db.models import Sum
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms import UploadPublicoForm
from .models import ArquivoPublico

logger = logging.getLogger(__name__)


@require_GET
def catalogo(request):
    total = ArquivoPublico.objects.aggregate(total=Sum('tamanho'))['total'] or 0
    return render(request, 'cloudpilot/catalogo.html', {
        'arquivos': ArquivoPublico.objects.all()[:100],
        'form': UploadPublicoForm(),
        'total_bytes': total,
    })


@login_required
@permission_required('cloudpilot.add_arquivopublico', raise_exception=True)
@require_POST
def enviar(request):
    form = UploadPublicoForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, 'cloudpilot/catalogo.html', {
            'arquivos': ArquivoPublico.objects.all()[:100],
            'form': form,
            'total_bytes': ArquivoPublico.objects.aggregate(total=Sum('tamanho'))['total'] or 0,
        }, status=400)
    uploaded = form.cleaned_data['arquivo']
    registro = ArquivoPublico(
        titulo=form.cleaned_data['titulo'], nome_original=uploaded.name,
        tamanho=uploaded.size, tipo=uploaded.content_type, enviado_por=request.user,
    )
    saved_name = None
    try:
        # Store first, then publish the database record. D1 has no rollback.
        registro.arquivo.save(uploaded.name, uploaded, save=False)
        saved_name = registro.arquivo.name
        registro.save(force_insert=True)
    except Exception:
        logger.exception('Falha ao registrar upload público.')
        if saved_name:
            try:
                default_storage.delete(saved_name)
            except Exception:
                logger.exception('Upload órfão requer reconciliação do armazenamento.')
        messages.error(request, 'Não foi possível salvar o arquivo. Tente novamente.')
        return redirect('pilot:catalogo')
    messages.success(request, 'Arquivo enviado e publicado com sucesso.')
    return redirect('pilot:catalogo')


@require_GET
def baixar(request, pk):
    registro = get_object_or_404(ArquivoPublico, pk=pk)
    if not default_storage.exists(registro.arquivo.name):
        raise Http404('Arquivo indisponível.')
    response = FileResponse(
        registro.arquivo.open('rb'), as_attachment=True,
        filename=registro.nome_original, content_type=registro.tipo,
    )
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "sandbox; default-src 'none'"
    return response


@require_GET
def health(request):
    # Exercises the configured database, but does not disclose configuration.
    ArquivoPublico.objects.exists()
    return JsonResponse({'status': 'ok', 'modo': 'piloto'})
