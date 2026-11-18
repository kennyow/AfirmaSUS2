import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.storage import FileSystemStorage
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve

from cloudpilot import videos
from cloudpilot.portal_preview import PortalPreviewMiddleware
from core.views.midias import adicionar_midia, remover_midia


class VideoEditingTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.originals = [{'titulo': title, 'url': 'https://youtu.be/dOvOjLi99WE', 'descricao': ''}
                          for title in ('Primeiro', 'Segundo')]
        self.source = root / 'videos.json'
        self.source.write_text(json.dumps(self.originals), encoding='utf-8')
        settings = override_settings(PORTAL_PREVIEW=True, DATA_DIR=root)
        settings.enable()
        self.addCleanup(settings.disable)
        storage = patch.object(videos, 'default_storage', FileSystemStorage(location=root / 'r2'))
        storage.start()
        self.addCleanup(storage.stop)

    def request(self, tipo='adicionar', identity=None, authenticated=True, data=None):
        path = '/plataforma/midias/' + tipo + '/video/' + (f'{identity}/' if identity else '')
        request = RequestFactory().post(path, data or {'titulo': 'Novo', 'link': 'https://youtu.be/dOvOjLi99WE'})
        request.user = SimpleNamespace(is_authenticated=authenticated, is_superuser=False)
        request.session = {}
        request._messages = FallbackStorage(request)
        request.resolver_match = resolve(path)
        return request

    def test_member_can_add_and_remove_with_durable_results(self):
        guard = PortalPreviewMiddleware(lambda request: None)
        request = self.request()
        self.assertIsNone(guard.process_view(request, adicionar_midia, (), {'tipo': 'video'}))
        self.assertEqual(adicionar_midia(request, 'video').status_code, 302)
        self.assertEqual([v['titulo'] for v in videos.catalog()], ['Primeiro', 'Segundo', 'Novo'])
        original_id = videos.catalog()[0]['removal_id']
        second_id = videos.catalog()[1]['removal_id']
        new_id = videos.catalog()[2]['removal_id']
        for identity in (original_id, new_id):
            request = self.request('remover', identity)
            self.assertIsNone(guard.process_view(request, remover_midia, (), {'tipo': 'video', 'index': int(identity)}))
            self.assertEqual(remover_midia(request, 'video', int(identity)).status_code, 302)
        self.assertEqual([v['removal_id'] for v in videos.catalog()], [second_id])
        self.assertFalse(videos.remove(original_id))
        self.assertEqual(json.loads(self.source.read_text(encoding='utf-8')), self.originals)

    def test_public_cannot_add_or_remove(self):
        for tipo in ('adicionar', 'remover'):
            identity = videos.catalog()[0]['removal_id']
            request = self.request(tipo, identity if tipo == 'remover' else None, authenticated=False)
            guard = PortalPreviewMiddleware(lambda request: None)
            self.assertEqual(guard.process_view(request, None, (), {'tipo': 'video'}).status_code, 302)
            response = adicionar_midia(request, 'video') if tipo == 'adicionar' else remover_midia(request, 'video', int(identity))
            self.assertEqual(response.status_code, 302)
        self.assertEqual(len(videos.catalog()), 2)

    def test_invalid_data_is_not_saved(self):
        for title, link in (('', 'https://youtu.be/dOvOjLi99WE'), ('x' * 201, 'https://youtu.be/dOvOjLi99WE'),
                            ('Teste', 'javascript:alert(1)'), ('Teste', 'https://example.com/watch?v=dOvOjLi99WE'),
                            ('Teste', 'https://www.youtube.com/')):
            adicionar_midia(self.request(data={'titulo': title, 'link': link}), 'video')
        self.assertEqual(len(videos.catalog()), 2)

    def test_save_failure_returns_feedback_without_false_success(self):
        with patch.object(videos, 'add', side_effect=OSError('unavailable')):
            with self.assertLogs('core.views.midias', level='ERROR'):
                request = self.request()
                self.assertEqual(adicionar_midia(request, 'video').status_code, 302)
        self.assertEqual(len(videos.catalog()), 2)
        self.assertTrue(any('Não foi possível' in str(message) for message in request._messages))

    def test_forms_are_enabled_only_for_logged_in_members(self):
        template = get_template('core/linha_tempo_midias.html')
        context = {'portal_preview': True, 'videos': videos.catalog()}
        html = template.render({**context, 'user': SimpleNamespace(is_authenticated=True)})
        self.assertIn('class="modal-content rounded-4" data-pilot-edit', html)
        self.assertIn('style="display:inline;" data-pilot-edit', html)
        self.assertIn(f"/video/{videos.catalog()[0]['removal_id']}/", html)
        public = template.render({**context, 'user': SimpleNamespace(is_authenticated=False)})
        self.assertNotIn('id="modalVideo"', public)
        self.assertNotIn('/midias/remover/video/', public)
