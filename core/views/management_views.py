import json
import logging

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from ..models import Local, Atividade, EscalaTrabalho
from ..forms import LocalForm, AtividadeForm, EscalaForm

logger = logging.getLogger(__name__)
CALENDARIO_PATH = settings.BASE_DIR.parent.parent / 'AfirmaSUS' / 'calendario.json'

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
        with CALENDARIO_PATH.open(encoding='utf-8') as arquivo:
            eventos_json = json.load(arquivo)
        if not isinstance(eventos_json, list):
            raise ValueError("O conteúdo deve ser uma lista de eventos.")

        for evento in eventos_json:
            if not isinstance(evento, dict):
                raise ValueError("Cada evento deve ser um objeto JSON.")
            evento_formatado = evento.copy()
            evento_formatado['extendedProps'] = {
                'description': evento.get('description', 'Sem descrição disponível.')
            }
            if evento_formatado.get('end') == evento_formatado.get('start'):
                evento_formatado.pop('end')
            calendario_eventos.append(evento_formatado)
    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Não foi possível carregar o calendário de atividades em %s.", CALENDARIO_PATH)
        calendario_erro = "Não foi possível carregar os eventos. Verifique o arquivo calendario.json."

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