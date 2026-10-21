"""Verifica as configurações em processos isolados, sem expor chaves."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import textwrap
import unittest


class SecretKeySettingsTests(unittest.TestCase):
    def test_estaticos_coletados_e_servidos_em_producao(self):
        result = self.run_settings('false', secrets.token_urlsafe(64), code=textwrap.dedent('''
            import os
            import tempfile
            os.environ['DJANGO_SETTINGS_MODULE'] = 'setup.settings'
            import django
            django.setup()
            from django.core.management import call_command
            from django.contrib.staticfiles.storage import staticfiles_storage
            from django.test import Client, override_settings
            with tempfile.TemporaryDirectory() as directory:
                with override_settings(STATIC_ROOT=directory):
                    call_command('collectstatic', interactive=False, verbosity=0)
                    client = Client(HTTP_HOST='example.com')
                    for name, mime in (
                        ('logo_roxo.png', 'image/png'),
                        ('core/atas.css', 'text/css'),
                        ('core/atas.js', 'text/javascript'),
                        ('admin/css/base.css', 'text/css'),
                    ):
                        url = staticfiles_storage.url(name)
                        assert url != '/static/' + name, url
                        response = client.get(url)
                        assert response.status_code == 200, (url, response.status_code)
                        assert response['Content-Type'].split(';')[0] == mime
                        assert 'immutable' in response['Cache-Control']
                        assert b''.join(response.streaming_content)
                        response.close()
        '''))
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_settings(self, debug=None, key=None, hosts='example.com', origins=None, code='import setup.settings'):
        environment = os.environ.copy()
        for name in ('DJANGO_DEBUG', 'DJANGO_SECRET_KEY', 'DJANGO_ALLOWED_HOSTS', 'DJANGO_CSRF_TRUSTED_ORIGINS', 'DJANGO_DATA_DIR'):
            environment.pop(name, None)
        if debug is not None:
            environment['DJANGO_DEBUG'] = debug
        if key is not None:
            environment['DJANGO_SECRET_KEY'] = key
        if hosts is not None:
            environment['DJANGO_ALLOWED_HOSTS'] = hosts
        if origins is not None:
            environment['DJANGO_CSRF_TRUSTED_ORIGINS'] = origins
        return subprocess.run(
            [sys.executable, '-c', code],
            cwd=Path(__file__).resolve().parent.parent,
            env=environment,
            capture_output=True,
            text=True,
        )

    def test_local_sem_chave(self):
        self.assertEqual(self.run_settings().returncode, 0)

    def test_producao_rejeita_chave_ausente_vazia_curta_ou_local(self):
        for key in (None, '', ' ', 'curta', 'django-insecure-' + 'x' * 64):
            with self.subTest(key_type=type(key).__name__):
                result = self.run_settings('false', key)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ImproperlyConfigured', result.stderr)

    def test_producao_aceita_chave_aleatoria(self):
        self.assertEqual(
            self.run_settings('false', secrets.token_urlsafe(64)).returncode, 0
        )

    def test_debug_invalido_e_rejeitado(self):
        self.assertNotEqual(self.run_settings('talvez').returncode, 0)

    def test_dados_persistentes_copia_e_reabertura(self):
        result = self.run_settings(code=textwrap.dedent('''
            import os, tempfile, sqlite3, json
            from contextlib import closing
            from pathlib import Path
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / 'source'
                source.mkdir()
                os.environ['DJANGO_DATA_DIR'] = str(source)
                os.environ['DJANGO_SETTINGS_MODULE'] = 'setup.settings'
                import django
                django.setup()
                from django.conf import settings
                from django.core.management import call_command
                from django.core.management.base import CommandError
                from core.views import management_views, main_views
                from importlib import import_module
                midias = import_module('core.views.midias')
                assert settings.DATABASES['default']['NAME'] == source / 'db.sqlite3'
                assert settings.MEDIA_ROOT == source / 'media'
                assert midias.TIMELINE_PATH == str(source / 'timeline.json')
                assert main_views.INDICADORES_PATH == str(source / 'indicadores.json')
                assert management_views.CALENDARIO_NOTAS_PATH == source / 'calendario_notas.json'
                with closing(sqlite3.connect(source / 'db.sqlite3')) as database:
                    database.execute('CREATE TABLE sample (value TEXT)')
                    database.execute("INSERT INTO sample VALUES ('preservado')")
                    database.commit()
                (source / 'timeline.json').write_text('[{"titulo":"preservado"}]', encoding='utf-8')
                (source / 'media').mkdir()
                (source / 'media' / 'upload.txt').write_text('upload', encoding='utf-8')
                destination = root / 'backup'
                call_command('copiar_dados', str(destination), verbosity=0)
                with closing(sqlite3.connect(destination / 'db.sqlite3')) as database:
                    assert database.execute('SELECT value FROM sample').fetchone()[0] == 'preservado'
                assert json.loads((destination / 'timeline.json').read_text(encoding='utf-8'))[0]['titulo'] == 'preservado'
                assert (destination / 'media' / 'upload.txt').read_text() == 'upload'
                try:
                    call_command('copiar_dados', str(destination), verbosity=0)
                except CommandError:
                    pass
                else:
                    raise AssertionError('Destino existente foi aceito')
                import subprocess, sys
                environment = os.environ.copy()
                environment['DJANGO_DATA_DIR'] = str(destination)
                reopened = subprocess.run([sys.executable, '-c',
                    "from setup.settings import DATABASES; import sqlite3; "
                    "db = sqlite3.connect(DATABASES['default']['NAME']); "
                    "assert db.execute('SELECT value FROM sample').fetchone()[0] == 'preservado'; db.close()"],
                    env=environment, capture_output=True, text=True)
                assert reopened.returncode == 0, reopened.stderr
        '''))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hosts_locais_por_padrao(self):
        result = self.run_settings(hosts=None, code=(
            "from setup.settings import ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS; "
            "assert ALLOWED_HOSTS == ['localhost', '127.0.0.1', '[::1]']; "
            "assert CSRF_TRUSTED_ORIGINS == []"
        ))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_producao_exige_hosts_explicitos(self):
        for hosts in (None, '', ' , ', '*', 'example.com,*'):
            result = self.run_settings('false', secrets.token_urlsafe(64), hosts=hosts)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('DJANGO_ALLOWED_HOSTS', result.stderr)

    def test_listas_removem_espacos_e_itens_vazios(self):
        result = self.run_settings(
            'false', secrets.token_urlsafe(64),
            hosts=' example.com, www.example.com, ',
            origins=' https://example.com, https://www.example.com, ',
            code=(
                "from setup.settings import ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS; "
                "assert ALLOWED_HOSTS == ['example.com', 'www.example.com']; "
                "assert CSRF_TRUSTED_ORIGINS == ['https://example.com', 'https://www.example.com']"
            ),
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_host_desconhecido_e_rejeitado(self):
        result = self.run_settings('false', secrets.token_urlsafe(64), code=(
            "import os; os.environ['DJANGO_SETTINGS_MODULE'] = 'setup.settings'; "
            "from django.test import RequestFactory; "
            "from django.core.exceptions import DisallowedHost; "
            "request = RequestFactory().get('/', HTTP_HOST='example.com'); "
            "assert request.get_host() == 'example.com'; "
            "request = RequestFactory().get('/', HTTP_HOST='unknown.example'); "
            "\ntry: request.get_host()\n"
            "except DisallowedHost: pass\n"
            "else: raise AssertionError('Host desconhecido aceito')"
        ))
        self.assertEqual(result.returncode, 0, result.stderr)
