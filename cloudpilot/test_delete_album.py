import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.storage import FileSystemStorage
from django.http import Http404
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase

from cloudpilot import galeria


class DeleteAlbumTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        storage = FileSystemStorage(location=self.root)
        patcher = patch.object(galeria, 'default_storage', storage)
        patcher.start()
        self.addCleanup(patcher.stop)
        catalog = patch.object(galeria, 'albums', return_value=[{'title': 'Legado', 'keys': []}])
        catalog.start()
        self.addCleanup(catalog.stop)
        (self.root / 'albuns-publicados').mkdir()
        (self.root / 'albuns-publicados' / '100').write_text(json.dumps({
            'title': 'Novo', 'keys': [], 'timeline': True,
        }), encoding='utf-8')
        self.photo = self.root / 'albuns' / '100' / 'fotos' / 'foto.png'
        self.photo.parent.mkdir(parents=True)
        self.photo.write_bytes(b'preservar')

    def request(self, method='post', authenticated=True):
        request = getattr(RequestFactory(), method)('/midias/galeria/100/excluir/')
        request.user = SimpleNamespace(is_authenticated=authenticated)
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_delete_hides_album_from_gallery_timeline_and_direct_address(self):
        self.assertEqual(len(galeria.album_cards()), 2)
        self.assertEqual(len(galeria.timeline_albums()), 1)
        self.assertEqual(galeria.delete_album(self.request(), 100).status_code, 302)
        self.assertEqual([x['title'] for x in galeria.album_cards()], ['Legado'])
        self.assertEqual(galeria.timeline_albums(), [])
        with self.assertRaises(Http404):
            galeria.get_album(100)
        self.assertEqual(self.photo.read_bytes(), b'preservar')

    def test_imported_album_can_also_be_removed(self):
        galeria.delete_album(self.request(), 1)
        self.assertEqual([x['title'] for x in galeria.album_cards()], ['Novo'])

    def test_public_and_get_cannot_delete(self):
        self.assertEqual(galeria.delete_album(self.request(authenticated=False), 100).status_code, 302)
        self.assertEqual(galeria.delete_album(self.request(method='get'), 100).status_code, 405)
        self.assertEqual(len(galeria.album_cards()), 2)

    def test_control_only_shown_to_members(self):
        template = get_template('core/linha_tempo_midias.html')
        context = {'portal_preview': True, 'gallery_albums': galeria.album_cards()}
        member = template.render({**context, 'user': SimpleNamespace(is_authenticated=True)})
        public = template.render({**context, 'user': SimpleNamespace(is_authenticated=False)})
        self.assertIn('id="delete-album-modal"', member)
        self.assertIn('/midias/galeria/100/excluir/', member)
        self.assertNotIn('id="delete-album-modal"', public)
