import json
from datetime import date, datetime, time
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..ata_exports import build_export_files
from ..forms import AtaReuniaoForm, AtaReuniaoFormExportacao
from ..models import AtaReuniao, Integrante


def _conteudo_vazio():
    return {
        'participantes': {'presentes': [], 'ausentes': []},
        'assuntos': {'itens': [], 'observacoes': ''},
        'decisoes': {'itens': [], 'justificativas': ''},
        'acoes': [],
        'pendencias': {'itens': [], 'proximos_passos': ''},
        'encerramento': {'horario_termino': '', 'proxima_reuniao': ''},
        'anotacoes': '',
        'horario_automatico': True,
    }


def _agrupar_por_data(atas):
    grupos = {}
    for ata in atas:
        conteudo = ata.conteudo
        preenchido = [
            ata.data,
            ata.horario,
            ata.local,
            ata.coordenador,
            ata.responsavel,
            ata.titulo,
            bool(conteudo['participantes']['presentes']),
            any(item['titulo'] or item['discussao'] for item in conteudo['assuntos']['itens']),
            any(conteudo['decisoes']['itens']),
            any(acao['tarefa'] for acao in conteudo['acoes']),
            conteudo['encerramento']['horario_termino'],
        ]
        ata.progresso = round(sum(bool(valor) for valor in preenchido) / len(preenchido) * 100)
        grupos.setdefault(ata.data, []).append(ata)
    return [
        {'data': dia, 'atas': lista}
        for dia, lista in sorted(grupos.items(), reverse=True)
    ]


def _filtrar_atas(atas, consulta):
    termos = consulta.casefold().split()
    if not termos:
        return atas
    filtradas = []
    for ata in atas:
        conteudo = json.dumps(ata.conteudo, ensure_ascii=False).casefold()
        texto = ' '.join((
            ata.titulo,
            ata.local,
            ata.coordenador,
            ata.responsavel,
            conteudo,
        )).casefold()
        if all(termo in texto for termo in termos):
            filtradas.append(ata)
    return filtradas


@login_required
def lista_atas(request):
    consulta = request.GET.get('q', '').strip()
    atas = list(AtaReuniao.objects.all())
    atas = _filtrar_atas(atas, consulta)
    return render(request, 'core/atas_lista.html', {
        'grupos': _agrupar_por_data(atas),
        'consulta': consulta,
        'total_atas': len(atas),
        'pagina_atas': 'lista',
    })


@login_required
def nova_ata(request):
    if request.method == 'POST':
        form = AtaReuniaoForm(request.POST)
        if form.is_valid():
            ata = form.save(commit=False)
            ata.criada_por = request.user
            ata.atualizada_por = request.user
            ata.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'url': reverse('editar_ata', kwargs={'ata_id': ata.pk}),
                })
            messages.success(request, "Ata criada e salva no sistema.")
            return redirect('editar_ata', ata_id=ata.pk)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'errors': _erros_formulario(form)}, status=400)
    else:
        form = AtaReuniaoForm(initial={
            'data': timezone.localdate(),
            'conteudo': _conteudo_vazio(),
        })
    return render(request, 'core/ata_formulario.html', {
        'form': form,
        'ata': None,
        'conteudo_inicial': _conteudo_vazio(),
        'integrantes_ata': list(
            Integrante.objects.order_by('nome').values_list('nome', flat=True)
        ),
    })


@login_required
def editar_ata(request, ata_id):
    ata = get_object_or_404(AtaReuniao, pk=ata_id)
    if request.method == 'POST':
        form = AtaReuniaoForm(request.POST, instance=ata)
        if form.is_valid():
            atualizada = form.save(commit=False)
            atualizada.atualizada_por = request.user
            atualizada.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'url': reverse('editar_ata', kwargs={'ata_id': ata.pk}),
                })
            messages.success(request, "Ata atualizada.")
            return redirect('editar_ata', ata_id=ata.pk)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'errors': _erros_formulario(form)}, status=400)
    else:
        form = AtaReuniaoForm(instance=ata)
    return render(request, 'core/ata_formulario.html', {
        'form': form,
        'ata': ata,
        'conteudo_inicial': ata.conteudo,
        'integrantes_ata': list(
            Integrante.objects.order_by('nome').values_list('nome', flat=True)
        ),
    })


def _erros_formulario(form):
    return {
        campo: [str(erro) for erro in erros]
        for campo, erros in form.errors.items()
    }


@login_required
@require_POST
def excluir_ata(request, ata_id):
    ata = get_object_or_404(AtaReuniao, pk=ata_id)
    ata.delete()
    messages.success(request, "Ata excluída.")
    return redirect('atas')


@login_required
@require_POST
def alterar_fila_ata(request, ata_id):
    ata = get_object_or_404(AtaReuniao, pk=ata_id)
    ata.na_fila = not ata.na_fila
    ata.na_fila_em = timezone.now() if ata.na_fila else None
    ata.atualizada_por = request.user
    ata.save(update_fields=['na_fila', 'na_fila_em', 'atualizada_por', 'atualizada_em'])
    messages.success(
        request,
        "Ata adicionada à fila de exportação." if ata.na_fila
        else "Ata removida da fila de exportação.",
    )
    return redirect('fila_atas' if request.POST.get('origem') == 'fila' else 'atas')


@login_required
def fila_atas(request):
    atas = list(AtaReuniao.objects.filter(na_fila=True))
    return render(request, 'core/atas_lista.html', {
        'grupos': _agrupar_por_data(atas),
        'total_atas': len(atas),
        'pagina_atas': 'fila',
    })


@login_required
@require_POST
def concluir_acao_ata(request, ata_id, acao_id):
    ata = get_object_or_404(AtaReuniao, pk=ata_id)
    acoes = ata.conteudo.get('acoes', [])
    acao = next((item for item in acoes if item.get('id') == acao_id), None)
    if acao is None:
        messages.error(request, "A ação não foi encontrada.")
        return redirect('lembretes_atas')
    acao['status'] = 'Concluída'
    ata.atualizada_por = request.user
    ata.save(update_fields=['conteudo', 'atualizada_por', 'atualizada_em'])
    messages.success(request, "Ação marcada como concluída.")
    return redirect('lembretes_atas')


@login_required
def lembretes_atas(request):
    agora = timezone.localtime()
    hoje = timezone.localdate()
    grupos = {'atrasados': [], 'hoje': [], 'proximos': [], 'concluidos': []}
    atas = AtaReuniao.objects.all()

    for ata in atas:
        for acao in ata.conteudo.get('acoes', []):
            lembrete = acao.get('lembrete', {})
            if not lembrete.get('data'):
                continue
            dia = date.fromisoformat(lembrete['data'])
            horario = time.fromisoformat(lembrete.get('hora') or '09:00')
            instante = timezone.make_aware(
                datetime.combine(dia, horario),
                timezone.get_current_timezone(),
            )
            item = {
                'ata': ata,
                'acao': acao,
                'instante': instante,
            }
            if acao.get('status') == 'Concluída':
                grupos['concluidos'].append(item)
            elif instante < agora:
                grupos['atrasados'].append(item)
            elif dia == hoje:
                grupos['hoje'].append(item)
            else:
                grupos['proximos'].append(item)

    for itens in grupos.values():
        itens.sort(key=lambda item: item['instante'])
    grupos['concluidos'].reverse()
    total_lembretes = sum(len(grupos[chave]) for chave in ('atrasados', 'hoje'))
    return render(request, 'core/atas_lista.html', {
        'pagina_atas': 'lembretes',
        'grupos_lembretes': grupos,
        'total_lembretes': total_lembretes,
        'tem_lembretes': any(grupos.values()),
    })


@login_required
@require_POST
def exportar_atas(request):
    em_fila = AtaReuniao.objects.filter(na_fila=True)
    form = AtaReuniaoFormExportacao(request.POST, atas=em_fila)
    if not form.is_valid():
        messages.error(request, "Selecione atas e formatos válidos para exportar.")
        return redirect('fila_atas')

    atas = list(em_fila.filter(pk__in=form.cleaned_data['atas']))
    if len(atas) != len(set(form.cleaned_data['atas'])):
        messages.error(request, "Uma ou mais atas selecionadas não estão na fila.")
        return redirect('fila_atas')

    arquivos = build_export_files(
        atas,
        form.cleaned_data['formatos'],
        form.cleaned_data['modo'],
    )
    buffer = BytesIO()
    nomes = set()
    with ZipFile(buffer, 'w', ZIP_DEFLATED) as arquivo_zip:
        for nome, conteudo in arquivos:
            nome_unico = nome
            sufixo = 2
            while nome_unico in nomes:
                separador = nome.rfind('.')
                nome_unico = f'{nome[:separador]}_{sufixo}{nome[separador:]}'
                sufixo += 1
            nomes.add(nome_unico)
            arquivo_zip.writestr(nome_unico, conteudo)

    agora = timezone.now()
    em_fila.filter(pk__in=[ata.pk for ata in atas]).update(exportada_em=agora)
    resposta = HttpResponse(buffer.getvalue(), content_type='application/zip')
    resposta['Content-Disposition'] = 'attachment; filename="atas_afirmasus.zip"'
    return resposta
