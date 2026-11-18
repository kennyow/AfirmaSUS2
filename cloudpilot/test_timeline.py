import json
from io import BytesIO
import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
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
        self.view_storage_patch = patch('core.views.midias.default_storage', timeline.default_storage)
        self.view_storage_patch.start()
        self.addCleanup(self.view_storage_patch.stop)

    def request(self, path, data=None, authenticated=True):
        request = RequestFactory().post(path, data or {})
        request.user = SimpleNamespace(is_authenticated=authenticated, is_superuser=False)
        request.session = {}
        request._messages = FallbackStorage(request)
        request.resolver_match = resolve(path)
        return request

    def test_member_can_publish_and_public_cannot(self):
        path = '/plataforma/midias/adicionar/timeline_dinamica/'
        data = {'data_evento': '2026-11-17', 'titulo': 'Novo evento', 'group': 'Reuniões'}
        request = self.request(path, data)
        guard = PortalPreviewMiddleware(lambda request: None)
        self.assertIsNone(guard.process_view(request, adicionar_midia, (), {'tipo': 'timeline_dinamica'}))
        self.assertEqual(adicionar_midia(request, 'timeline_dinamica').status_code, 302)
        self.assertEqual([e['text']['headline'] for e in timeline.document()['events']], ['Legado', 'Novo evento'])
        self.assertEqual(json.loads(self.source.read_text(encoding='utf-8')), self.original)
        self.assertEqual(timeline.document()['events'][-1]['start_date'], {'year': '2026', 'month': '11', 'day': '17'})
        anonymous = self.request(path, data, False)
        self.assertEqual(guard.process_view(anonymous, adicionar_midia, (), {'tipo': 'timeline_dinamica'}).status_code, 302)
        self.assertEqual(adicionar_midia(anonymous, 'timeline_dinamica').status_code, 302)
        self.assertEqual(len(timeline.document()['events']), 2)
        unrelated = self.request('/plataforma/midias/adicionar/slide/')
        self.assertEqual(guard.process_view(unrelated, adicionar_midia, (), {'tipo': 'slide'}).status_code, 403)

    def test_invalid_date_does_not_publish(self):
        request = self.request('/plataforma/midias/adicionar/timeline_dinamica/',
                               {'data_evento': '2026-02-30', 'titulo': 'Inválido', 'group': 'Eventos'})
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
        self.assertIn('enctype="multipart/form-data" data-pilot-edit', html)
        self.assertIn('<select id="dinamica-group"', html)
        self.assertIn('id="dinamica-data" type="date"', html)
        self.assertNotIn('id="dinamica-year"', html)
        self.assertNotIn('name="media_url"', html)
        self.assertIn('id="formRemoverEventoDinamico" data-pilot-edit', html)
        self.assertIn(f"/timeline_dinamica/{timeline.document()['events'][0]['removal_id']}/", html)
        public = template.render({'user': SimpleNamespace(is_authenticated=False), 'portal_preview': True,
                                  'eventos_timeline_dinamica': timeline.document()['events']})
        self.assertNotIn('id="dinamica-data"', public)

    def image(self):
        buffer = BytesIO()
        Image.new('RGB', (4, 4)).save(buffer, format='PNG')
        return SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')

    def publish(self, **extra):
        data = {'data_evento': '2026-11-17', 'titulo': 'Imagem', 'group': 'Eventos'}
        data.update(extra)
        return adicionar_midia(self.request('/plataforma/midias/adicionar/timeline_dinamica/', data), 'timeline_dinamica')

    def test_single_image_is_saved_with_public_url(self):
        self.publish(arquivo=self.image())
        event = timeline.document()['events'][-1]
        self.assertTrue(event['media']['url'].endswith('.png'))
        self.assertIn('/timeline-dinamica/imagens/', event['media']['url'])
        self.assertEqual(len(timeline.names('timeline-dinamica/imagens')), 1)

    @override_settings(DATA_UPLOAD_MAX_NUMBER_FILES=2)
    def test_rejects_invalid_group_multiple_files_and_fake_image(self):
        for data in ({'group': 'Livre'}, {'arquivo': [self.image(), self.image()]},
                     {'arquivo': SimpleUploadedFile('foto.png', b'fake', content_type='image/png')},
                     {'arquivo': SimpleUploadedFile('texto.pdf', b'%PDF-1.7\n%%EOF', content_type='application/pdf')}):
            with self.subTest(data=list(data)):
                self.publish(**data)
                self.assertEqual(len(timeline.document()['events']), 1)
        self.assertEqual(timeline.names('timeline-dinamica/imagens'), [])

    def test_failed_event_save_cleans_uploaded_image(self):
        with patch.object(timeline, 'add', side_effect=OSError('storage unavailable')):
            with self.assertLogs('core.views.midias', level='ERROR'):
                self.publish(arquivo=self.image())
        self.assertEqual(timeline.names('timeline-dinamica/imagens'), [])
        self.assertEqual(len(timeline.document()['events']), 1)
