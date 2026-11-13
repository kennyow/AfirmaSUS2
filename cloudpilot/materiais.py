from pathlib import PurePosixPath
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_safe

WORD_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


from .forms import UploadPublicoForm


MATERIALS_PREFIX = 'materiais/Materiais'


def materiais():
    try:
        _, files = default_storage.listdir(MATERIALS_PREFIX)
    except FileNotFoundError:
        return []
    items = []
    for name in files:
        path = PurePosixPath(name)
        if path.suffix.lower() in {'.pdf', '.docx'}:
            title = path.stem
            if title.startswith('envio-') and '--' in title:
                title = title.split('--', 1)[1]
            items.append({'key': name, 'title': title})
    return sorted(items, key=lambda item: item['title'].casefold())


@login_required
@require_POST
def adicionar_material(request):
    form = UploadPublicoForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, 'Informe o título e envie um PDF ou Word válido de até 10 MB.')
        return redirect('formacoes')
    file = form.cleaned_data['arquivo']
    extension = PurePosixPath(file.name).suffix.lower()
    if extension not in {'.pdf', '.docx'}:
        messages.error(request, 'Envie um PDF ou documento Word (.docx).')
        return redirect('formacoes')
    title = form.cleaned_data['titulo'].replace('/', '-').replace(chr(92), '-')
    default_storage.save(f'{MATERIALS_PREFIX}/envio-{uuid4().hex}--{title}{extension}', file, max_length=255)
    messages.success(request, 'Material adicionado.')
    return redirect('formacoes')


def material_path(key):
    item = next((item for item in materiais() if item['key'] == key), None)
    if item is None:
        raise Http404('Material indisponível.')
    return item, f'{MATERIALS_PREFIX}/{key}'


@login_required
@require_POST
def remover_material(request, key):
    _, path = material_path(key)
    default_storage.delete(path)
    messages.success(request, 'Material removido.')
    return redirect('formacoes')


@require_safe
def abrir_material(request, key, download=False):
    item, path = material_path(key)
    is_pdf = key.lower().endswith('.pdf')
    if not is_pdf and not download:
        try:
            with default_storage.open(path, 'rb') as file, ZipFile(file) as document:
                entry = document.getinfo('word/document.xml')
                if entry.file_size > 4 * 1024 * 1024:
                    raise Http404('Prévia indisponível. Baixe o original.')
                content = ElementTree.fromstring(document.read(entry))
        except (BadZipFile, KeyError, ElementTree.ParseError) as error:
            raise Http404('Prévia indisponível. Baixe o original.') from error
        paragraphs = [
            ''.join(t.text or '' for t in p.iter(WORD_NS + 't'))
            for p in content.iter(WORD_NS + 'p')
        ]
        return render(request, 'cloudpilot/material.html', {'item': item, 'paragraphs': paragraphs})

    extension = '.pdf' if is_pdf else '.docx'
    mime = 'application/pdf' if is_pdf else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    response = FileResponse(default_storage.open(path, 'rb'), as_attachment=download,
                            filename=item['title'] + extension, content_type=mime)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "sandbox; default-src 'none'" if download else "object-src 'none'; script-src 'none'"
    return response
