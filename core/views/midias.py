import json
import os
import re
from datetime import date
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .utils import converter_link_drive

# Caminhos para os arquivos JSON na raiz do projeto
FORMACOES_PATH = os.path.join(settings.BASE_DIR, 'formacoes.json')
APRESENTACOES_PATH = os.path.join(settings.BASE_DIR, 'apresentacoes.json')
VIDEOS_PATH = os.path.join(settings.BASE_DIR, 'videos.json')
TIMELINE_PATH = os.path.join(settings.BASE_DIR, 'timeline.json')
DYNAMIC_TIMELINE_PATH = os.path.join(settings.BASE_DIR, 'linhadotempodinamica.json')

def ler_json(caminho):
    if not os.path.exists(caminho):
        return []
    with open(caminho, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def salvar_json(caminho, dados):
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def ler_linha_tempo_dinamica():
    if not os.path.exists(DYNAMIC_TIMELINE_PATH):
        return {'title': {}, 'events': []}
    with open(DYNAMIC_TIMELINE_PATH, 'r', encoding='utf-8') as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, dict) or not isinstance(dados.get('events'), list):
        raise ValueError('linhadotempodinamica.json deve conter um objeto com uma lista "events".')
    dados.setdefault('title', {})
    return dados

def extrair_youtube_id(url):
    if not url:
        return ""
    # Trata URLs normais, curtas, embed, e com parâmetros extras (&t=...)
    match = re.search(r'(?:v=|\/live\/|\/embed\/|youtu\.be\/|\/v\/)([\w-]{11})', url)
    return match.group(1) if match else ""

def formacoes(request):
    formacoes_raw = ler_json(FORMACOES_PATH)
    apresentacoes_raw = ler_json(APRESENTACOES_PATH)
    videos_raw = ler_json(VIDEOS_PATH)

    # 1. Formações
    formacoes = []
    for item in formacoes_raw:
        item_copy = item.copy()
        raw_foto = item_copy.get('foto') or item_copy.get('imagem') or item_copy.get('link') or ''
        item_copy['foto_url'] = converter_link_drive(raw_foto)
        formacoes.append(item_copy)

    # 2. Slides / Apresentações
    apresentacoes = []
    for item in apresentacoes_raw:
        item_copy = item.copy()
        raw_foto = item_copy.get('foto') or item_copy.get('imagem') or item_copy.get('thumb') or item_copy.get('cover') or ''
        raw_link = item_copy.get('link') or item_copy.get('link_directo') or item_copy.get('embed_url') or ''
        
        # Converte a URL da foto (se for Google Drive/web)
        foto_convertida = converter_link_drive(raw_foto) if raw_foto else ""
        
        # Tenta pegar foto do campo ou do link do slide
        if not foto_convertida and raw_link:
            foto_convertida = converter_link_drive(raw_link)

        item_copy['foto_url'] = foto_convertida if ('lh3.googleusercontent' in foto_convertida or foto_convertida.startswith('http')) else ''
        item_copy['link_url'] = raw_link
        apresentacoes.append(item_copy)

    # 3. Vídeos da Comunidade
    videos = []
    for item in videos_raw:
        item_copy = item.copy()
        raw_url = item_copy.get('url') or item_copy.get('link') or ''
        y_id = extrair_youtube_id(raw_url)
        
        item_copy['video_id'] = y_id
        item_copy['embed_url'] = f"https://www.youtube-nocookie.com/embed/{y_id}" if y_id else raw_url
        videos.append(item_copy)

    context = {
        'formacoes': formacoes,
        'apresentacoes': apresentacoes,
        'videos': videos,
    }
    return render(request, 'core/midias.html', context)

def midias(request):
    atividades = ler_json(TIMELINE_PATH)
    linha_tempo_dinamica = ler_linha_tempo_dinamica()
    return render(request, 'core/linha_tempo_midias.html', {
        'atividades_timeline': atividades,
        'eventos_timeline_dinamica': linha_tempo_dinamica['events'],
    })

@login_required
def adicionar_midia(request, tipo):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        link = request.POST.get('link', '')
        foto = request.POST.get('foto', '')
        descricao = request.POST.get('descricao', '')

        if tipo == 'formacao':
            formacoes = ler_json(FORMACOES_PATH)
            formacoes.append({
                'titulo': titulo,
                'foto': foto or link,
                'link': link,
                'descricao': descricao
            })
            salvar_json(FORMACOES_PATH, formacoes)

        elif tipo in ['slide', 'apresentacao']:
            apresentacoes = ler_json(APRESENTACOES_PATH)
            apresentacoes.append({
                'titulo': titulo,
                'foto': foto,
                'link': link,
                'descricao': descricao
            })
            salvar_json(APRESENTACOES_PATH, apresentacoes)

        elif tipo == 'video':
            videos = ler_json(VIDEOS_PATH)
            videos.append({
                'titulo': titulo,
                'url': link,
                'descricao': descricao
            })
            salvar_json(VIDEOS_PATH, videos)

        elif tipo == 'timeline':
            data = request.POST.get('data', '').strip()
            titulo = (titulo or '').strip()
            categoria = request.POST.get('categoria', '').strip()
            cor_borda = request.POST.get('cor_borda', '').strip()
            fotos = [foto.strip() for foto in request.POST.getlist('fotos') if foto.strip()]

            if not all((data, titulo, categoria, cor_borda)):
                messages.error(request, 'Preencha data, título, categoria e cor da atividade.')
                return redirect('midias')

            atividades = ler_json(TIMELINE_PATH)
            atividades.append({
                'data': data,
                'titulo': titulo,
                'categoria': categoria,
                'cor_borda': cor_borda,
                'descricao': descricao.strip(),
                'fotos': fotos,
            })
            salvar_json(TIMELINE_PATH, atividades)
            messages.success(request, 'Atividade adicionada à Linha do Tempo.')

        elif tipo == 'timeline_dinamica':
            try:
                year = int(request.POST.get('year', ''))
                month = int(request.POST.get('month', ''))
                day = int(request.POST.get('day', ''))
            except ValueError:
                messages.error(request, 'Informe uma data válida para o evento.')
                return redirect('midias')

            try:
                date(year, month, day)
            except ValueError:
                messages.error(request, 'A data informada não é válida.')
                return redirect('midias')

            headline = (titulo or '').strip()
            group = request.POST.get('group', '').strip()
            media_url = request.POST.get('media_url', '').strip()
            media_caption = request.POST.get('media_caption', '').strip()
            if not headline or not group:
                messages.error(request, 'Preencha o título e o grupo do evento.')
                return redirect('midias')

            evento = {
                'start_date': {
                    'year': str(year),
                    'month': f'{month:02d}',
                    'day': f'{day:02d}',
                },
                'text': {
                    'headline': headline,
                    'text': descricao.strip(),
                },
                'group': group,
            }
            if media_url or media_caption:
                evento['media'] = {}
                if media_url:
                    evento['media']['url'] = media_url
                if media_caption:
                    evento['media']['caption'] = media_caption

            linha_tempo = ler_linha_tempo_dinamica()
            linha_tempo['events'].append(evento)
            salvar_json(DYNAMIC_TIMELINE_PATH, linha_tempo)
            messages.success(request, 'Evento adicionado à Linha do Tempo Dinâmica.')

    return redirect(
        'midias' if tipo in ['timeline', 'timeline_dinamica'] else 'formacoes'
    )

@login_required
def remover_midia(request, tipo, index):
    if request.method == 'POST':
        try:
            idx = int(index)
        except ValueError:
            return redirect(
                'midias' if tipo in ['timeline', 'timeline_dinamica'] else 'formacoes'
            )

        if tipo == 'formacao':
            formacoes = ler_json(FORMACOES_PATH)
            if 0 <= idx < len(formacoes):
                formacoes.pop(idx)
                salvar_json(FORMACOES_PATH, formacoes)

        elif tipo in ['slide', 'apresentacao']:
            apresentacoes = ler_json(APRESENTACOES_PATH)
            if 0 <= idx < len(apresentacoes):
                apresentacoes.pop(idx)
                salvar_json(APRESENTACOES_PATH, apresentacoes)

        elif tipo == 'video':
            videos = ler_json(VIDEOS_PATH)
            if 0 <= idx < len(videos):
                videos.pop(idx)
                salvar_json(VIDEOS_PATH, videos)

        elif tipo == 'timeline':
            atividades = ler_json(TIMELINE_PATH)
            if 0 <= idx < len(atividades):
                atividades.pop(idx)
                salvar_json(TIMELINE_PATH, atividades)

        elif tipo == 'timeline_dinamica':
            linha_tempo = ler_linha_tempo_dinamica()
            eventos = linha_tempo['events']
            if 0 <= idx < len(eventos):
                eventos.pop(idx)
                salvar_json(DYNAMIC_TIMELINE_PATH, linha_tempo)

    return redirect(
        'midias' if tipo in ['timeline', 'timeline_dinamica'] else 'formacoes'
    )