"""Read-only visual smoke check. Run against manage.py runserver on port 8012."""
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import resolve
from core.models import Local
from playwright.sync_api import sync_playwright

OUT = ROOT / os.environ.get('COVER_QA_OUTPUT', '.qa-cover')
OUT.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get('COVER_PREVIEW_URL', 'http://127.0.0.1:8012')
paths = ['/', '/mapa/', '/escala/', '/formacoes/', '/midias/', '/levantamento-estatistico/', '/login/', '/cadastrar/']
previews = {}
preview_user = get_user_model()(username='preview', first_name='Equipe')
for path in ['/local/novo/', '/atividade/nova/', '/escala/nova/', '/midias/']:
    request = RequestFactory().get(path)
    request.user = preview_user
    request.resolver_match = resolve(path)
    response = request.resolver_match.func(request, **request.resolver_match.kwargs)
    assert response.status_code == 200, path
    previews[path] = response.content.decode()

local = Local.objects.first()
if local:
    for path in [f'/local/{local.pk}/editar/', f'/local/deletar/{local.pk}/']:
        request = RequestFactory().get(path)
        request.user = preview_user
        request.resolver_match = resolve(path)
        response = request.resolver_match.func(request, **request.resolver_match.kwargs)
        assert response.status_code == 200
        previews[path] = response.content.decode()

results = []
if '--remaining' in sys.argv:
    results = json.loads((OUT / 'results.json').read_text(encoding='utf-8'))
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    page = context.new_page()
    page.set_default_timeout(20000)
    page.set_default_navigation_timeout(60000)
    errors = []
    page.on('pageerror', lambda err: errors.append(str(err)))
    for width in [1440, 390]:
        page.set_viewport_size({'width': width, 'height': 1000 if width == 1440 else 844})
        for path in paths:
            if '--remaining' in sys.argv and width == 1440:
                continue
            errors.clear()
            response = page.goto(BASE + path, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_function('document.fonts.status === "loaded"', timeout=20000)
            page.wait_for_timeout(1200)
            name = path.strip('/').replace('/', '-') or 'home'
            page.screenshot(path=str(OUT / f'{name}-{width}.png'), full_page=True)
            metrics = page.evaluate('''() => ({
                overflow: document.documentElement.scrollWidth > innerWidth + 1,
                font: getComputedStyle(document.body).fontFamily,
                heading: document.querySelector('main h1')?.textContent.trim(),
                header: getComputedStyle(document.querySelector('header')).backgroundColor,
                background: getComputedStyle(document.body).backgroundColor,
                logo: document.querySelector('.brand-logo')?.naturalWidth,
                photo: document.querySelector('.home-hero-photo')?.naturalWidth,
                map: !!document.querySelector('.leaflet-tile-loaded'),
                plots: document.querySelectorAll('.js-plotly-plot .main-svg').length,
                fonts: [...document.fonts].map(f => ({family: f.family, status: f.status})),
            })''')
            results.append({'path': path, 'width': width, 'status': response.status, 'errors': errors.copy(), **metrics})
            print(json.dumps(results[-1], ensure_ascii=True), flush=True)
            (OUT / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            if path == '/mapa/':
                page.locator('#mapa-leaflet').scroll_into_view_if_needed()
                markers = page.locator('.leaflet-marker-icon')
                if markers.count():
                    visible_index = markers.evaluate_all('''els => {
                        const bounds = document.querySelector('#mapa-leaflet').getBoundingClientRect();
                        return els.map((el, index) => ({index, r: el.getBoundingClientRect(), z: Number(el.style.zIndex)}))
                            .filter(({r}) => r.x > bounds.x + 30 && r.y > bounds.y + 30 && r.right < bounds.right - 30 && r.bottom < bounds.bottom - 30)
                            .sort((a,b) => b.z - a.z)[0]?.index;
                    }''')
                    assert visible_index is not None, 'No marker within the map bounds'
                    markers.nth(visible_index).click(force=True)
                    page.locator('#conteudo-detalhes h4').wait_for(state='visible')
                filters = page.locator('.btn-filter-chip')
                if filters.count() > 1:
                    filters.nth(1).click()
                    assert 'categoria=' in page.url
            if width == 390 and path == '/':
                page.locator('.nav-toggle').click()
                page.locator('#afirma-navigation').wait_for(state='visible')
                page.locator('.site-links a[href="/mapa/"]').click()
                assert page.url.endswith('/mapa/')
        for path, html in previews.items():
            url = BASE + path + '?preview-layout=1'
            page.route(url, lambda route: route.fulfill(status=200, content_type='text/html', body=html))
            errors.clear()
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_function('document.fonts.status === "loaded"')
            page.wait_for_timeout(350)
            name = path.strip('/').replace('/', '-')
            page.screenshot(path=str(OUT / f'editor-{name}-{width}.png'), full_page=True)
            overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            results.append({'path': path, 'editor': True, 'width': width, 'overflow': overflow, 'errors': errors.copy()})
            if path == '/midias/':
                before = page.locator('.timeline-foto-item').count()
                page.locator('#adicionar-foto-timeline').click()
                assert page.locator('.timeline-foto-item').count() == before + 1
                page.locator('[data-remove-foto]').last.click()
                assert page.locator('.timeline-foto-item').count() == before
                modal_button = page.locator('[data-bs-target="#modalRemoverAtividade"]')
                if modal_button.count():
                    modal_button.click()
                    page.locator('#modalRemoverAtividade').wait_for(state='visible')
                    page.screenshot(path=str(OUT / f'media-modal-{width}.png'))
            page.unroute(url)
    context.close()
    browser.close()
(OUT / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('Visual smoke checks completed.', flush=True)
assert not any(r['overflow'] for r in results), 'Horizontal overflow detected'
assert not any(r.get('status', 200) != 200 for r in results), 'Route failed'
