import os
import json
import folium
import pandas as pd
import plotly.express as px
from django.shortcuts import render, redirect
from django.conf import settings
from ..models import Local, Atividade, Integrante, EscalaTrabalho
from .utils import converter_link_drive


from django.conf import settings
from django.contrib.auth.decorators import login_required

# ---------------------------------------------------------
# 1. ABA APRESENTAÇÃO (HOME)
# ---------------------------------------------------------
def home(request):
    link_foto_apresentacao = "https://drive.google.com/file/d/1sXMf6Y3c5RKxT9Ss5DT6ZwlDh63BOtIj/view?usp=drive_link" 
    link_logo_apresentacao = "https://drive.google.com/file/d/1YD1pFzwf_FLuvoZIP1R0oSrGh8XLghfC/view?usp=drive_link"

    url_foto_apresentacao = converter_link_drive(link_foto_apresentacao)
    url_logo_apresentacao = converter_link_drive(link_logo_apresentacao)

    # Carregamento da Linha do Tempo Geral (JSON TimelineJS)
    caminho_json = os.path.join(settings.BASE_DIR, 'linhadotempodinamica.json')
    timeline_json_str = "{}"

    if os.path.exists(caminho_json):
        try:
            with open(caminho_json, 'r', encoding='utf-8') as f:
                dados_timeline = json.load(f)

            if "title" in dados_timeline and "media" in dados_timeline["title"]:
                if "url" in dados_timeline["title"]["media"]:
                    dados_timeline["title"]["media"]["url"] = converter_link_drive(dados_timeline["title"]["media"]["url"])

            if "events" in dados_timeline:
                for evento in dados_timeline["events"]:
                    if "media" in evento and "url" in evento["media"]:
                        evento["media"]["url"] = converter_link_drive(evento["media"]["url"])

            timeline_json_str = json.dumps(dados_timeline, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao processar linha do tempo geral: {e}")

    # Carregamento da Linha do Tempo de Atividades (JSON local)
    try:
        caminho_timeline_atividades = os.path.join(settings.BASE_DIR, 'timeline.json')
        with open(caminho_timeline_atividades, "r", encoding="utf-8") as f:
            atividades_raw = json.load(f)
            
        atividades_timeline = []
        for ev in atividades_raw:
            lista_fotos = ev.get("fotos", [])
            if not lista_fotos and ev.get("foto"):
                lista_fotos = [ev["foto"]]
                
            ev["fotos"] = [converter_link_drive(f_url) for f_url in lista_fotos]
            atividades_timeline.append(ev)
    except Exception:
        atividades_timeline = []

    contexto = {
        'atividades_timeline': atividades_timeline,
        'url_foto_apresentacao': url_foto_apresentacao,
        'url_logo_apresentacao': url_logo_apresentacao,
        'timeline_json': timeline_json_str,
    }
    return render(request, 'core/home.html', contexto)


# ---------------------------------------------------------
# 2. ABA MAPA DO TERRITÓRIO
# ---------------------------------------------------------
# core/views/main_views.py

import json
from django.shortcuts import render
from ..models import Local, Atividade, EscalaTrabalho


def mapa_territorio(request):
    locais = Local.objects.all()
    atividades = Atividade.objects.select_related('local').all()
    escalas = EscalaTrabalho.objects.select_related('integrante', 'local').all()

    categoria_selecionada = request.GET.get('categoria', 'todos')
    locais_filtrados = locais.filter(categoria=categoria_selecionada) if categoria_selecionada != 'todos' else locais

    # Mapeamento com cores HEX diretas
    MAPA_CATEGORIAS = {
        'Saúde': {'emoji': '🟢', 'cor_btn': '#28a745', 'cor_hex': '#28a745'},
        'Esporte e Lazer': {'emoji': '🟠', 'cor_btn': '#fd7e14', 'cor_hex': '#fd7e14'},
        'Educação': {'emoji': '🟣', 'cor_btn': '#6f42c1', 'cor_hex': '#6f42c1'},
        'Religião': {'emoji': '🔵', 'cor_btn': '#17a2b8', 'cor_hex': '#17a2b8'},
        'Cultura': {'emoji': '🟡', 'cor_btn': '#ffc107', 'cor_hex': '#ffc107'},
        'Comércio': {'emoji': '🔴', 'cor_btn': '#dc3545', 'cor_hex': '#dc3545'},
        'Administrativo': {'emoji': '🩷', 'cor_btn': '#e83e8c', 'cor_hex': '#e83e8c'},
    }

    categorias_bd = sorted(list(set(locais.values_list('categoria', flat=True))))
    lista_categorias = []
    
    for cat in categorias_bd:
        meta = MAPA_CATEGORIAS.get(cat, {'emoji': '📍', 'cor_btn': '#481859', 'cor_hex': '#481859'})
        lista_categorias.append({
            'nome': cat,
            'emoji': meta['emoji'],
            'cor_btn': meta['cor_btn']
        })

    locais_json_list = []
    for loc in locais_filtrados:
        # Garante a validação de coordenadas numéricas
        try:
            lat_val = float(loc.lat)
            lon_val = float(loc.lon)
        except (ValueError, TypeError):
            continue

        escalas_local = [
            {
                'nome': esc.integrante.nome if esc.integrante else 'Integrante',
                'foto': esc.integrante.foto_url_direta if esc.integrante else '',
                'dia': esc.dia_semana,
                'turno': esc.turno,
                'horario': f"{esc.horario_inicio.strftime('%H:%M') if esc.horario_inicio else ''} - {esc.horario_fim.strftime('%H:%M') if esc.horario_fim else ''}"
            } for esc in escalas.filter(local=loc)
        ]

        meta_cat = MAPA_CATEGORIAS.get(loc.categoria, {'cor_hex': '#6f42c1'})

        locais_json_list.append({
            'id': loc.id,
            'nome': loc.nome,
            'distrito': loc.distrito or 'Distrito I',
            'categoria': loc.categoria,
            'status': loc.status or 'Ativo',
            'lat': lat_val,
            'lon': lon_val,
            'cor_hex': meta_cat['cor_hex'],
            'descricao': loc.descricao or 'Sem descrição cadastrada.',
            'foto': loc.foto_url_direta if hasattr(loc, 'foto_url_direta') and loc.foto_url_direta else (loc.foto or ''),
            'escalas': escalas_local,
        })

    contexto = {
        'lista_categorias': lista_categorias,
        'categoria_selecionada': categoria_selecionada,
        'locais_json': json.dumps(locais_json_list, ensure_ascii=False),
    }
    return render(request, 'core/mapa.html', contexto)


# core/views/main_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from ..models import Local
from ..forms import LocalForm

# core/views/main_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from ..models import Local
from ..forms import LocalForm


@login_required
def editar_local(request, local_id):
  local = get_object_or_404(Local, pk=local_id)

  if request.method == 'POST':
    form = LocalForm(request.POST, request.FILES, instance=local)
    if form.is_valid():
      form.save()  # Atualiza o Banco de Dados e o dados_locais.json
      return redirect('pagina_mapa')
  else:
    form = LocalForm(instance=local)

  contexto = {
      'form': form,
      'local': local,
      'titulo': f'Editar Local: {local.nome}',
  }
  return render(request, 'core/form_local.html', contexto)

@login_required
def cadastrar_local(request):
    if request.method == 'POST':
        form = LocalForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('pagina_mapa')
    else:
        form = LocalForm()

    contexto = {
        'form': form,
        'titulo': 'Cadastrar Novo Local',
    }
    return render(request, 'core/form_local.html', contexto)

@login_required
def deletar_local(request, local_id):
    local = get_object_or_404(Local, pk=local_id)
    
    if request.method == 'POST':
        local.delete()
        return redirect('pagina_mapa')
        
    contexto = {
        'local': local,
        'titulo': f'Confirmar exclusão: {local.nome}',
    }
    return render(request, 'core/confirmar_deletar_local.html', contexto)


from django.shortcuts import render

def nova_aba_view(request):
    return render(request, 'core/nova_aba.html')




INDICADORES_PATH = os.path.join(settings.BASE_DIR, 'indicadores.json')

def levantamento_estatistico(request):
    # 1. Carrega os indicadores ajustáveis (mão/manual)
    indicadores_extras = {"participantes_impactados": 150, "formacoes_oficinas": 22}
    if os.path.exists(INDICADORES_PATH):
        try:
            with open(INDICADORES_PATH, 'r', encoding='utf-8') as f:
                indicadores_extras.update(json.load(f))
        except Exception:
            pass

    # 2. Carrega e analisa dinamicamente o arquivo 'linhadotempodinamica.json'
    caminho_json = os.path.join(settings.BASE_DIR, 'linhadotempodinamica.json')
    events = []
    
    if os.path.exists(caminho_json):
        try:
            with open(caminho_json, 'r', encoding='utf-8') as f:
                dados_timeline = json.load(f)
                events = dados_timeline.get("events", [])
        except Exception as e:
            print(f"Erro ao ler linhadotempodinamica.json: {e}")

    total_acoes = len(events)
    
    # Se existirem eventos no JSON, recomputamos métricas e gráficos com Pandas
    grafico_linha_html = ""
    grafico_rosca_html = ""
    
    if events:
        lista_dados = []
        for ev in events:
            # Extrai ano e mês da data do evento
            year = ev.get("start_date", {}).get("year", 2026)
            month = ev.get("start_date", {}).get("month", 1)
            
            # Formata chave do mês (Ex: "01/2026")
            mes_str = f"{int(month):02d}/{year}"
            
            # Categoria / Grupo
            categoria = ev.get("group", "Geral")
            if not categoria or str(categoria).strip() == "":
                categoria = "Outros"

            lista_dados.append({
                "ano": int(year),
                "mes_num": int(month),
                "Mes": mes_str,
                "Categoria": categoria
            })

        df = pd.DataFrame(lista_dados)

        # A. Gráfico 1: Evolução Mensal (Ordenado por Data)
        df_mensal = df.groupby(["ano", "mes_num", "Mes"]).size().reset_index(name="Quantidade")
        df_mensal = df_mensal.sort_values(by=["ano", "mes_num"])

        fig_linha = px.line(
            df_mensal,
            x="Mes",
            y="Quantidade",
            markers=True,
            text="Quantidade",
            labels={"Quantidade": "Nº de Eventos", "Mes": "Mês / Ano"},
            color_discrete_sequence=["#FF8C00"]
        )
        fig_linha.update_traces(textposition="top center", fill='tozeroy')
        fig_linha.update_layout(
            height=360, 
            margin=dict(l=20, r=20, t=30, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Segoe UI, sans-serif")
        )
        grafico_linha_html = fig_linha.to_html(full_html=False, include_plotlyjs=False)

        # B. Gráfico 2: Distribuição por Eixo de Atuação (Categoria/Group)
        df_cat = df.groupby("Categoria").size().reset_index(name="Eventos")
        
        fig_rosca = px.pie(
            df_cat,
            values="Eventos",
            names="Categoria",
            hole=0.45,
            color_discrete_sequence=["#856eaf", "#28A745", "#FF8C00", "#7BDCEB", "#CF68E3", "#DC3545", "#17A2B8"]
        )
        fig_rosca.update_traces(textinfo="percent+value")
        fig_rosca.update_layout(
            height=360, 
            margin=dict(l=10, r=10, t=30, b=10), 
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Segoe UI, sans-serif")
        )
        grafico_rosca_html = fig_rosca.to_html(full_html=False, include_plotlyjs=False)

    contexto = {
        'total_acoes': total_acoes,
        'participantes_impactados': indicadores_extras.get("participantes_impactados", 150),
        'formacoes_oficinas': indicadores_extras.get("formacoes_oficinas", 22),
        'grafico_linha_html': grafico_linha_html,
        'grafico_rosca_html': grafico_rosca_html,
    }
    return render(request, 'core/levantamento_estatistico.html', contexto)

@login_required
def atualizar_indicadores(request):
    """ View para salvar edições dos indicadores manuais no arquivo JSON """
    if request.method == 'POST':
        try:
            part = int(request.POST.get('participantes_impactados', 150))
            form = int(request.POST.get('formacoes_oficinas', 22))
            
            dados = {
                "participantes_impactados": part,
                "formacoes_oficinas": form
            }
            with open(INDICADORES_PATH, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar indicadores: {e}")

    return redirect('levantamento_estatistico')