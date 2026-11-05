"""Stage only application sources for Wrangler; never scan a build environment."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

subprocess.run([sys.executable, '-m', 'unittest', 'cloudpilot.test_worker_hashers'], check=True)

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / 'src'
STAGE.mkdir(exist_ok=True)

environment = dict(os.environ)
environment['DJANGO_SETTINGS_MODULE'] = 'setup.static_settings'
subprocess.run(
    [sys.executable, str(ROOT / 'manage.py'), 'collectstatic', '--noinput', '--verbosity=0'],
    cwd=ROOT, env=environment, check=True,
)

for name in ('core', 'setup', 'cloudpilot'):
    shutil.copytree(
        ROOT / name, STAGE / name, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'test_*.py', 'tests.py', 'static'),
    )
shutil.copyfile(ROOT / 'worker.py', STAGE / 'worker.py')
assert (STAGE / 'cloudpilot' / 'templates' / 'cloudpilot' / 'catalogo.html').is_file()
assert (STAGE / 'setup' / 'cloudflare_settings.py').is_file()
print('Aplicacao preparada em src; ambientes, bancos e JSON de conteudo ficam fora do pacote.')

