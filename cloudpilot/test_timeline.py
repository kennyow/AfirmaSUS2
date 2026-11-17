import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.storage import FileSystemStorage
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve
from unittest.mock import patch

from cloudpilot import timeline
from cloudpilot.portal_preview import PortalPreviewMiddleware
from core.views.midias import adicionar_midia, remover_midia


class DynamicTimelineTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.original = {'title': {'text': {'headline': 'História'}}, 'events': [
            {'start_date': {'year': '2026', 'month': '01', 'day': '01'}, 'text': {'headline': 'Legado'}},
        ]}
        self.source = root / 'linhadotempodinamica.json'
        self.source.write_text(json.dumps(self.original), encoding='utf-8')
        self.settings_override = override_settings(PORTAL_PREVIEW=True, DATA_DIR=root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.storage_patch = patch.object(timeline, 'default_storage', FileSystemStorage(location=root / 'r2'))
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def request(self, path, data=None, authenticated=True):
        request = RequestFactory().post(path, data or {})
        request.user = SimpleNamespace(is_authenticated=authenticated, is_superuser=False)
        request.session = {}
        request._messages = FallbackStorage(request)
        request.resolver_match = resolve(path)
        return request

    def test_member_can_publish_and_public_cannot(self):
        path = '/plataforma/midias/adicionar/timeline_dinamica/'
        data = {'year': '2026', 'month': '11', 'day': '17', 'titulo': 'Novo evento', 'group': 'Reunião'}
        request = self.request(path, data)
        guard = PortalPreviewMiddleware(lambda request: None)
        self.assertIsNone(guard.process_view(request, adicionar_midia, (), {'tipo': 'timeline_dinamica'}))
        self.assertEqual(adicionar_midia(request, 'timeline_dinamica').status_code, 302)
        self.assertEqual([e['text']['headline'] for e in timeline.document()['events']], ['Legado', 'Novo evento'])
        self.assertEqual(json.loads(self.source.read_text(encoding='utf-8')), self.original)
        anonymous = self.request(path, data, False)
        self.assertEqual(guard.process_view(anonymous, adicionar_midia, (), {'tipo': 'timeline_dinamica'}).status_code, 302)
        self.assertEqual(adicionar_midia(anonymous, 'timeline_dinamica').status_code, 302)
        self.assertEqual(len(timeline.document()['events']), 2)
        unrelated = self.request('/plataforma/midias/adicionar/video/')
        self.assertEqual(guard.process_view(unrelated, adicionar_midia, (), {'tipo': 'video'}).status_code, 403)

    def test_invalid_date_does_not_publish(self):
        request = self.request('/plataforma/midias/adicionar/timeline_dinamica/',
                               {'year': '2026', 'month': '2', 'day': '30', 'titulo': 'Inválido', 'group': 'Evento'})
        adicionar_midia(request, 'timeline_dinamica')
        self.assertEqual(len(timeline.document()['events']), 1)

    def test_stable_removal_preserves_other_records_and_source(self):
        original_id = timeline.document()['events'][0]['removal_id']
        timeline.add({'text': {'headline': 'Primeiro'}})
        timeline.add({'text': {'headline': 'Segundo'}})
        request = self.request(f'/plataforma/midias/remover/timeline_dinamica/{original_id}/')
        remover_midia(request, 'timeline_dinamica', int(original_id))
        self.assertEqual({e['text']['headline'] for e in timeline.document()['events']}, {'Primeiro', 'Segundo'})
        self.assertFalse(timeline.remove(original_id))
        self.assertEqual(json.loads(self.source.read_text(encoding='utf-8')), self.original)
        new_id = timeline.document()['events'][0]['removal_id']
        self.assertTrue(timeline.remove(new_id))
        self.assertEqual(len(timeline.document()['events']), 1)

    def test_template_marks_only_authorized_forms_editable(self):
        from django.template.loader import get_template
        template = get_template('core/linha_tempo_midias.html')
        html = template.render({'user': SimpleNamespace(is_authenticated=True), 'portal_preview': True,
                                'eventos_timeline_dinamica': timeline.document()['events']})
        self.assertIn('method="POST" data-pilot-edit', html)
        self.assertIn('id="formRemoverEventoDinamico" data-pilot-edit', html)
        self.assertIn(f"/timeline_dinamica/{timeline.document()['events'][0]['removal_id']}/", html)
        public = template.render({'user': SimpleNamespace(is_authenticated=False), 'portal_preview': True,
                                  'eventos_timeline_dinamica': timeline.document()['events']})
        self.assertNotIn('id="dinamica-year"', public)
