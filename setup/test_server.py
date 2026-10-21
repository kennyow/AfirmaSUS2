"""Teste HTTP do servidor real, apenas na interface local e sem gravar dados."""
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler


class ProductionServerTests(unittest.TestCase):
    def test_login_estatico_e_host_invalido(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        environment = os.environ.copy()
        environment.update({
            'DJANGO_DEBUG': 'false',
            'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
            'DJANGO_ALLOWED_HOSTS': '127.0.0.1',
            'HOST': '127.0.0.1',
            'PORT': str(port),
        })
        process = subprocess.Popen(
            [sys.executable, 'serve.py'],
            cwd=Path(__file__).resolve().parent.parent,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        opener = build_opener(ProxyHandler({}))
        base_url = f'http://127.0.0.1:{port}'
        try:
            deadline = time.monotonic() + 20
            while True:
                try:
                    with opener.open(base_url + '/login/', timeout=1) as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn(b'csrfmiddlewaretoken', response.read())
                    break
                except (URLError, TimeoutError):
                    if process.poll() is not None or time.monotonic() >= deadline:
                        self.fail('O servidor não respondeu dentro do prazo.')
                    time.sleep(0.1)
            with opener.open(base_url + '/static/logo_roxo.png', timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), 'image/png')
                self.assertTrue(response.read())
            with self.assertRaises(HTTPError) as error:
                opener.open(Request(base_url + '/login/', headers={'Host': 'unknown.example'}), timeout=3)
            self.assertEqual(error.exception.code, 400)
            error.exception.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
