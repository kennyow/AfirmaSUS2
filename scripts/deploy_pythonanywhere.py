"""Publish GitHub code, static assets and JSON; preserve SQLite and uploads."""
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
from uuid import uuid4

import requests


ROOT = Path(__file__).resolve().parent.parent
REMOTE = '/home/kennyow/AfirmaSUS2/afirmasus_django'
API = 'https://www.pythonanywhere.com/api/v0/user/kennyow'
DOMAIN = 'kennyow.pythonanywhere.com'
DATA_REMOTE = '/home/kennyow/afirmasus-dados'


def data_file(name):
    path = PurePosixPath(name)
    return (len(path.parts) == 1 and not name.startswith('.')
            and path.suffix.lower() == '.json' and path.name == name)


def destination(name):
    return (DATA_REMOTE if data_file(name) else REMOTE) + '/' + name


def validate_json(name, content):
    try:
        json.loads(content.decode('utf-8-sig'),
                   parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, UnicodeError) as error:
        raise RuntimeError(f'JSON inválido: {name}. Nenhum arquivo foi publicado.') from error


def publish_data(client, name, content, original, backup_directory, before_write=lambda: None):
    path = destination(name)
    if client.read(path) != original:
        raise RuntimeError(f'O site alterou {name} durante a publicação; tente novamente.')
    if original is not None:
        backup_path = backup_directory + '/' + name
        client.write(backup_path, original)
        if client.read(backup_path) != original:
            raise RuntimeError(f'Não foi possível verificar o backup de {name}.')
    if client.read(path) != original:
        raise RuntimeError(f'O site alterou {name} durante o backup; tente novamente.')
    before_write()
    client.write(path, content)
    if client.read(path) != content:
        raise RuntimeError(f'Não foi possível verificar o JSON publicado: {name}.')


def same_migration(local, remote):
    """Compare Python syntax without executing code or ignoring operations."""
    if remote is None:
        return False
    try:
        return ast.dump(ast.parse(local), include_attributes=False) == ast.dump(
            ast.parse(remote), include_attributes=False)
    except (SyntaxError, ValueError):
        return False


def error_annotation(message):
    return '::error::' + message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def requirement_lines(content):
    """Ignore file formatting, preserving dependency specifications exactly."""
    return sorted(line.strip() for line in content.decode('utf-8-sig').splitlines()
                  if line.strip() and not line.lstrip().startswith('#'))


def validate_requirements(local, remote):
    path = REMOTE + '/requirements.txt'
    if remote is None:
        raise RuntimeError(
            f'Arquivo ausente no servidor: {path}. '
            'Siga docs/ATUALIZACAO_AUTOMATICA.md, seção Sincronização inicial. '
            'Nenhum arquivo foi publicado.'
        )
    if requirement_lines(local) != requirement_lines(remote):
        raise RuntimeError(
            f'O arquivo {path} difere do GitHub. '
            'Siga docs/ATUALIZACAO_AUTOMATICA.md, seção Sincronização inicial, '
            'para instalar e sincronizar as dependências. Nenhum arquivo foi publicado.'
        )


def code_file(name):
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and '..' not in path.parts
        and not any(part.startswith('.') or part == '__pycache__' for part in path.parts)
        and path.parts[0] in {'core', 'setup', 'static'}
        and path.suffix.lower() in {'.py', '.html', '.css', '.js', '.svg', '.png',
                                    '.jpg', '.jpeg', '.gif', '.ico', '.webp',
                                    '.woff', '.woff2', '.ttf', '.map'}
    )


class Client:
    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers['Authorization'] = f'Token {token}'
        self.last_request = 0

    def call(self, method, endpoint, **kwargs):
        # API limit: 40 requests/minute. Leave a margin and honor 429 retries.
        for attempt in range(4):
            time.sleep(max(0, 1.6 - (time.monotonic() - self.last_request)))
            response = self.session.request(method, API + endpoint, timeout=90, **kwargs)
            self.last_request = time.monotonic()
            if response.status_code != 429:
                if response.status_code != 404:
                    response.raise_for_status()
                return response
            time.sleep(60)
        raise RuntimeError('Limite da API persistiu. Execute o workflow novamente.')

    def read(self, path):
        response = self.call('GET', '/files/path' + path)
        return None if response.status_code == 404 else response.content

    def write(self, path, content):
        response = self.call('POST', '/files/path' + path,
                             files={'content': ('upload', content)})
        response.raise_for_status()


def main():
    token = os.environ.get('PA_API_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Configure o secret PA_API_TOKEN no GitHub.')
    client = Client(token)
    response = client.call('GET', f'/webapps/{DOMAIN}/')
    response.raise_for_status()
    config = response.json()
    if config.get('virtualenv_path') != '/home/kennyow/.virtualenvs/afirmasus':
        raise RuntimeError('Virtualenv diferente do documentado; confira a aba Web.')
    # Dependency changes need installation on the server before code is published.
    requirements = (ROOT / 'requirements.txt').read_bytes()
    remote_requirements = client.read(REMOTE + '/requirements.txt')
    validate_requirements(requirements, remote_requirements)

    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    names = [name for name in tracked if name and code_file(name)]
    data_names = [name for name in tracked if name and data_file(name)]
    for name in data_names:
        validate_json(name, (ROOT / name).read_bytes())
    names += data_names
    names += ['manage.py', 'serve.py']
    static_root = ROOT / 'staticfiles'
    if not (static_root / 'staticfiles.json').is_file():
        raise RuntimeError('Execute collectstatic com DJANGO_DEBUG=false primeiro.')
    names += [file.relative_to(ROOT).as_posix() for file in static_root.rglob('*') if file.is_file()]
    names = sorted(set(names))
    # Refuse removals: stale Python modules/static originals need a deliberate cleanup.
    manifest_path = REMOTE + '/.github-deploy-manifest.txt'
    previous_manifest = client.read(manifest_path)
    if previous_manifest:
        removed = set(previous_manifest.decode().splitlines()) - set(names)
        # Hashed static files from prior releases may remain for cached pages.
        removed = {name for name in removed if not name.startswith('staticfiles/')}
        if removed:
            raise RuntimeError('Arquivos removidos exigem atualização manual: ' + ', '.join(sorted(removed)))

    # Read all originals before changing anything; retain them for rollback.
    changes = []
    for name in names:
        content = (ROOT / name).read_bytes()
        original = client.read(destination(name))
        if original != content:
            if '/migrations/' in name and not name.endswith('/__init__.py'):
                if same_migration(content, original):
                    continue
                reason = 'ausente no servidor' if original is None else 'com código diferente no servidor'
                raise RuntimeError(
                    f'Migração {reason}: {name}. Nenhum arquivo foi publicado. '
                    'Compare os arquivos antes de alterar a migração inicial; '
                    'não execute migrate nem substitua o arquivo sem conferir o banco.'
                )
            changes.append((name, content, original))
    applied = []
    backup_directory = ('/home/kennyow/afirmasus-deploy-backups/'
                        + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                        + '-' + uuid4().hex[:12])
    try:
        for name, content, original in changes:
            if data_file(name):
                publish_data(client, name, content, original, backup_directory,
                             before_write=lambda: applied.append((name, original)))
            else:
                applied.append((name, original))
                client.write(destination(name), content)
            print('Atualizado:', name, flush=True)
        client.write(manifest_path, ('\n'.join(names) + '\n').encode())
        response = client.call('POST', f'/webapps/{DOMAIN}/reload/')
        response.raise_for_status()
    except Exception:
        print('Falha na publicação; restaurando arquivos anteriores.', flush=True)
        for name, original in reversed(applied):
            if original is not None:
                client.write(destination(name), original)
            else:
                result = client.call('DELETE', '/files/path' + destination(name))
                if result.status_code != 404:
                    result.raise_for_status()
        if previous_manifest is not None:
            client.write(manifest_path, previous_manifest)
        else:
            result = client.call('DELETE', '/files/path' + manifest_path)
            if result.status_code != 404:
                result.raise_for_status()
        raise
    print(f'Publicação enviada e reload aceito: {len(changes)} arquivos atualizados.')
    if any(data_file(name) and original is not None for name, _, original in changes):
        print('Cópias anteriores dos JSON:', backup_directory)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(error_annotation(str(error)), flush=True)
        sys.exit(1)
