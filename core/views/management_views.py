import json
import logging
import os
import tempfile
import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from ..models import Local, Atividade, EscalaTrabalho
from ..forms import LocalForm, AtividadeForm, EscalaForm

logger = logging.getLogger(__name__)
CALENDARIO_NOTAS_PATH = settings.BASE_DIR / 'calendario_notas.json'


def _carregar_notas_calendario():
    try:
        with CALENDARIO_NOTAS_PATH.open(encoding='utf-8') as arquivo:
            notas = json.load(arquivo)
    except FileNotFoundError:
        return []

    if not isinstance(notas, list) or not all(isinstance(nota, dict) for nota in notas):
        raise ValueError("O arquivo de notas deve conter uma lista de objetos JSON.")
    for nota in notas:
        if not all(isinstance(nota.get(campo), str) and nota[campo] for campo in ('id', 'title', 'start')):
            raise ValueError("Cada nota deve conter id, título e data válidos.")
        date.fromisoformat(nota['start'])
    return notas


def _salvar_notas_calendario(notas):
    CALENDARIO_NOTAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    caminho_temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=CALENDARIO_NOTAS_PATH.parent,
            delete=False,
        ) as arquivo:
            caminho_temporario = Path(arquivo.name)
            json.dump(notas, arquivo, ensure_ascii=False, indent=2)
            arquivo.write('\n')
        os.replace(caminho_temporario, CALENDARIO_NOTAS_PATH)
    finally:
        if caminho_temporario and caminho_temporario.exists():
            caminho_temporario.unlink()

@login_required
def cadastrar_local(request):
    if request.method == 'POST':
        form = LocalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Novo local cadastrado com sucesso no mapa!")
            return redirect('pagina_mapa')
    else:
        form = LocalForm()

    return render(request, 'core/form_local.html', {'form': form})

@login_required
def cadastrar_atividade(request):
    if request.method == 'POST':
        form = AtividadeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Atividade cadastrada com sucesso!")
            return redirect('pagina_escala')
    else:
        form = AtividadeForm()

    return render(request, 'core/form_atividade.html', {'form': form})

@login_required
def deletar_local(request, local_id):
    local = get_object_or_404(Local, pk=local_id)
    local.delete()
    messages.warning(request, "Local removido com sucesso do mapa.")
    return redirect('pagina_mapa')

def pagina_escala(request):
    escalas = EscalaTrabalho.objects.select_related('integrante', 'local').all()
    dias = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    escalas_por_dia = {dia: escalas.filter(dia_semana=dia) for dia in dias}

    calendario_eventos = []
    calendario_erro = None
    try:
        for evento in _carregar_notas_calendario():
            evento_formatado = evento.copy()
            evento_formatado['extendedProps'] = {
                'description': evento.get('description', ''),
                'isNote': True,
            }
            if evento_formatado.get('end') == evento_formatado.get('start'):
                evento_formatado.pop('end')
            calendario_eventos.append(evento_formatado)
    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Não foi possível carregar o calendário de atividades em %s.", CALENDARIO_NOTAS_PATH)
        calendario_erro = "Não foi possível carregar o calendário. Verifique o arquivo calendario_notas.json."

    context = {
        'escalas_por_dia': escalas_por_dia,
        'calendario_eventos': calendario_eventos,
        'calendario_erro': calendario_erro,
    }
    return render(request, 'core/escala.html', context)

@login_required
def cadastrar_escala(request):
    if request.method == 'POST':
        form = EscalaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Nova escala cadastrada com sucesso!")
            return redirect('pagina_escala')
    else:
        form = EscalaForm()

    return render(request, 'core/form_escala.html', {'form': form})


@login_required
@require_POST
def deletar_escala(request, escala_id):
    escala = get_object_or_404(EscalaTrabalho, pk=escala_id)
    escala.delete()
    messages.warning(request, "Horário removido da escala com sucesso.")
    return redirect('pagina_escala')


@login_required
@require_POST
def adicionar_nota_calendario(request):
    titulo = request.POST.get('title', '').strip()
    descricao = request.POST.get('description', '').strip()
    data_nota = request.POST.get('date', '').strip()

    try:
        date.fromisoformat(data_nota)
    except ValueError:
        messages.error(request, "Selecione uma data válida para a nota.")
        return redirect('pagina_escala')

    if not titulo or len(titulo) > 200:
        messages.error(request, "Informe um título para a nota com até 200 caracteres.")
        return redirect('pagina_escala')

    try:
        notas = _carregar_notas_calendario()
        notas.append({
            'id': f'nota-{uuid.uuid4()}',
            'title': titulo,
            'start': data_nota,
            'description': descricao,
        })
        _salvar_notas_calendario(notas)
    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Não foi possível salvar a nota do calendário.")
        messages.error(request, "Não foi possível salvar a nota. Tente novamente.")
        return redirect('pagina_escala')

    messages.success(request, "Nota adicionada ao calendário.")
    return redirect('pagina_escala')


@login_required
@require_POST
def deletar_nota_calendario(request, note_id):
    try:
        notas = _carregar_notas_calendario()
        notas_filtradas = [
            nota for nota in notas
            if nota.get('id') != note_id
        ]
        if len(notas_filtradas) == len(notas):
            messages.error(request, "O evento não foi encontrado.")
            return redirect('pagina_escala')
        _salvar_notas_calendario(notas_filtradas)
    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Não foi possível excluir a nota %s do calendário.", note_id)
        messages.error(request, "Não foi possível excluir a nota. Tente novamente.")
        return redirect('pagina_escala')

    messages.success(request, "Evento removido do calendário.")
    return redirect('pagina_escala')


@login_required
@require_POST
def editar_nota_calendario(request, note_id):
    titulo = request.POST.get('title', '').strip()
    descricao = request.POST.get('description', '').strip()
    data_nota = request.POST.get('date', '').strip()

    try:
        date.fromisoformat(data_nota)
    except ValueError:
        messages.error(request, "Selecione uma data válida para o evento.")
        return redirect('pagina_escala')

    if not titulo or len(titulo) > 200:
        messages.error(request, "Informe um título com até 200 caracteres.")
        return redirect('pagina_escala')

    try:
        eventos = _carregar_notas_calendario()
        evento = next((item for item in eventos if item['id'] == note_id), None)
        if evento is None:
            messages.error(request, "O evento não foi encontrado.")
            return redirect('pagina_escala')
        evento.update({
            'title': titulo,
            'start': data_nota,
            'description': descricao,
        })
        if 'end' in evento:
            evento['end'] = data_nota
        _salvar_notas_calendario(eventos)
    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Não foi possível editar o evento %s do calendário.", note_id)
        messages.error(request, "Não foi possível salvar as alterações. Tente novamente.")
        return redirect('pagina_escala')

    messages.success(request, "Evento atualizado no calendário.")
    return redirect('pagina_escala')