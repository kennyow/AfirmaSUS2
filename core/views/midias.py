import json
import os
import re
from django.conf import settings
from django.shortcuts import render, redirect
from .utils import converter_link_drive

# Caminhos para os arquivos JSON na raiz do projeto
FORMACOES_PATH = os.path.join(settings.BASE_DIR, 'formacoes.json')
APRESENTACOES_PATH = os.path.join(settings.BASE_DIR, 'apresentacoes.json')
VIDEOS_PATH = os.path.join(settings.BASE_DIR, 'videos.json')

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

def extrair_youtube_id(url):
    if not url:
        return ""
    # Trata URLs normais, curtas, embed, e com parâmetros extras (&t=...)
    match = re.search(r'(?:v=|\/live\/|\/embed\/|youtu\.be\/|\/v\/)([\w-]{11})', url)
    return match.group(1) if match else ""

def midias(request):
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
        'videos': videos
    }
    return render(request, 'core/midias.html', context)

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

    return redirect('midias')

def remover_midia(request, tipo, index):
    if request.method == 'POST':
        try:
            idx = int(index)
        except ValueError:
            return redirect('midias')

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

    return redirect('midias')