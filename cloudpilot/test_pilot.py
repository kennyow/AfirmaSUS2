import io
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import Client, TestCase, override_settings
from PIL import Image

from .models import ArquivoPublico


def png(name='registro.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (16, 16), '#481859').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='text/html')


class UploadFlowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        temporary_root = settings.BASE_DIR / '.test-tmp'
        temporary_root.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(dir=temporary_root)
        cls.storage_settings = override_settings(
            MEDIA_ROOT=cls.directory.name,
            STORAGES={
                'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
            },
        )
        cls.storage_settings.enable()

    @classmethod
    def tearDownClass(cls):
        cls.storage_settings.disable()
        cls.directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(username='equipe-teste', password='test-only-secret')
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label='cloudpilot', codename='add_arquivopublico',
        ))

    def upload(self, file=None):
        return self.client.post('/arquivos/enviar/', {'titulo': 'Registro do projeto', 'arquivo': file or png()})

    def test_visitor_can_browse_but_not_upload(self):
        self.assertEqual(self.client.get('/arquivos/').status_code, 200)
        self.assertEqual(self.upload().status_code, 302)
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_login_and_upload_image_then_public_download(self):
        response = self.client.post('/login/', {'username': self.user.username, 'password': 'test-only-secret'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.upload().status_code, 302)
        item = ArquivoPublico.objects.get()
        self.assertEqual(item.enviado_por_id, self.user.pk)
        self.assertEqual(item.tipo, 'image/png')
        self.assertTrue(item.arquivo.name.startswith('publicos/'))
        self.assertNotIn('registro', item.arquivo.name)
        self.assertTrue(default_storage.exists(item.arquivo.name))
        self.client.logout()
        page = self.client.get('/arquivos/')
        self.assertContains(page, 'Registro do projeto')
        self.assertContains(page, item.arquivo.url)
        download = self.client.get(f'/arquivos/{item.pk}/baixar/')
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment;', download['Content-Disposition'])
        self.assertEqual(b''.join(download.streaming_content)[:8], b'\x89PNG\r\n\x1a\n')

    def test_account_without_upload_permission_is_rejected(self):
        ordinary = User.objects.create_user(username='consulta-teste')
        self.client.force_login(ordinary)
        self.assertEqual(self.upload().status_code, 403)
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_inactive_account_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post('/login/', {'username': self.user.username, 'password': 'test-only-secret'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_upload_requires_csrf(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user)
        self.assertEqual(browser.post('/arquivos/enviar/', {'titulo': 'Teste', 'arquivo': png()}).status_code, 403)
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_fake_image_rejected(self):
        self.client.force_login(self.user)
        file = SimpleUploadedFile('imagem.png', b'<script>alert(1)</script>', content_type='image/png')
        self.assertEqual(self.upload(file).status_code, 400)
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_extension_must_match_image_content(self):
        self.client.force_login(self.user)
        self.assertEqual(self.upload(png('imagem.jpg')).status_code, 400)
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_image_limit(self):
        self.client.force_login(self.user)
        file = SimpleUploadedFile('grande.png', b'x' * (5 * 1024 * 1024 + 1))
        self.assertEqual(self.upload(file).status_code, 400)
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_svg_is_not_accepted(self):
        self.client.force_login(self.user)
        file = SimpleUploadedFile('vetor.svg', b'<svg></svg>')
        self.assertEqual(self.upload(file).status_code, 400)
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_pdf_upload_and_download(self):
        self.client.force_login(self.user)
        file = SimpleUploadedFile('ata.pdf', b'%PDF-1.4\n%test\n%%EOF', content_type='text/html')
        self.assertEqual(self.upload(file).status_code, 302)
        item = ArquivoPublico.objects.get()
        self.assertEqual(item.tipo, 'application/pdf')
        response = self.client.get(f'/arquivos/{item.pk}/baixar/')
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment;', response['Content-Disposition'])
        response.close()

    def test_bad_office_archive_rejected(self):
        self.client.force_login(self.user)
        self.assertEqual(self.upload(SimpleUploadedFile('ata.docx', b'not-a-zip')).status_code, 400)
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_storage_failure_does_not_publish_record(self):
        self.client.force_login(self.user)
        with patch('django.core.files.storage.FileSystemStorage._save', side_effect=OSError('unavailable')):
            with self.assertLogs('cloudpilot.views', level='ERROR'):
                self.assertEqual(self.upload().status_code, 302)
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_database_failure_cleans_uploaded_object(self):
        self.client.force_login(self.user)
        with patch.object(ArquivoPublico, 'save', side_effect=DatabaseError('unavailable')):
            with patch.object(default_storage, 'delete', wraps=default_storage.delete) as cleanup:
                with self.assertLogs('cloudpilot.views', level='ERROR'):
                    self.assertEqual(self.upload().status_code, 302)
                cleanup.assert_called_once()
                self.assertFalse(default_storage.exists(cleanup.call_args.args[0]))
        self.assertFalse(ArquivoPublico.objects.exists())

    def test_health_and_unknown_download(self):
        self.assertEqual(self.client.get('/health/').json()['status'], 'ok')
        self.assertEqual(self.client.get('/arquivos/99999/baixar/').status_code, 404)

    def test_oversized_request_is_rejected_early(self):
        response = self.client.post('/arquivos/enviar/', data=b'x', content_type='application/octet-stream', CONTENT_LENGTH=str(13 * 1024 * 1024))
        self.assertEqual(response.status_code, 413)

