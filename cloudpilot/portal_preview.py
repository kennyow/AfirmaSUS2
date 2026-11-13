"""Restrict the pilot portal to administrators and enabled operations."""
import json
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.deprecation import MiddlewareMixin


PUBLIC_PAGES = frozenset({
    'home', 'pagina_mapa', 'pagina_escala', 'equipe_informacoes',
    'formacoes', 'midias', 'levantamento_estatistico',
})
READ_ONLY_PAGES = PUBLIC_PAGES | {'atas', 'fila_atas', 'lembretes_atas'}
EDITABLE_PAGES = frozenset({
    'cadastrar_escala', 'editar_escala', 'cadastrar_local', 'editar_local',
    'nova_ata', 'editar_ata', 'deletar_local',
})
POST_ONLY_PAGES = frozenset({'alterar_fila_ata', 'exportar_atas', 'concluir_acao_ata', 'deletar_escala', 'publicar_formacao'})


class PortalPreviewMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path != '/' and not request.path.startswith('/plataforma/'):
            return None
        if request.method in ('GET', 'HEAD') and request.resolver_match.url_name in PUBLIC_PAGES:
            return None
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not request.user.is_superuser:
            return HttpResponse('Esta prévia está disponível apenas ao administrador.', status=403)
        if request.resolver_match.url_name in EDITABLE_PAGES and request.method in ('GET', 'HEAD', 'POST'):
            return None
        if request.method == 'POST' and request.resolver_match.url_name in POST_ONLY_PAGES:
            return None
        if getattr(settings, 'CALENDARIO_NO_BANCO', False) and request.method == 'POST' and request.resolver_match.url_name in {'adicionar_nota_calendario', 'editar_nota_calendario'}:
            return None
        if request.method not in ('GET', 'HEAD') or request.resolver_match.url_name not in READ_ONLY_PAGES:
            return HttpResponse('Esta operação ainda não está disponível na prévia.', status=405)
        return None


def context(request):
    return {'portal_preview': request.path == '/' or request.path.startswith('/plataforma/')}


def read_document(name, default):
    path = Path(settings.DATA_DIR) / name
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def statistics(request):
    events = read_document('linhadotempodinamica.json', {}).get('events', [])
    metrics = read_document('indicadores.json', {})
    monthly, categories = Counter(), Counter()
    for event in events:
        start = event.get('start_date', {})
        try:
            year, month = int(start.get('year', 2026)), int(start.get('month', 1))
        except (TypeError, ValueError):
            continue
        if not 1 <= month <= 12:
            continue
        monthly[(year, month)] += 1
        categories[str(event.get('group') or 'Outros')] += 1
    dates = sorted(monthly)
    line = {'x': [f'{m:02d}/{y}' for y, m in dates], 'y': [monthly[d] for d in dates]}
    pie = {'labels': sorted(categories), 'values': [categories[c] for c in sorted(categories)]}
    return render(request, 'core/levantamento_estatistico.html', {
        'total_acoes': len(events),
        'participantes_impactados': metrics.get('participantes_impactados', 150),
        'formacoes_oficinas': metrics.get('formacoes_oficinas', 22),
        'grafico_linha_html': render_to_string('cloudpilot/preview_chart.html', {'chart_id': 'preview-monthly', 'data': line, 'kind': 'line'}) if dates else '',
        'grafico_rosca_html': render_to_string('cloudpilot/preview_chart.html', {'chart_id': 'preview-categories', 'data': pie, 'kind': 'pie'}) if categories else '',
    })
