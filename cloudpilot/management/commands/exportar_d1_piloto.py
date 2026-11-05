import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Exporta somente banco de piloto vazio, com esquema e permissões, para bootstrap no D1.'

    def add_arguments(self, parser):
        parser.add_argument('destino')

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        if db['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('Execute no banco SQLite isolado do piloto.')
        path = Path(db['NAME']).resolve()
        if path.name != 'pilot.sqlite3' or not path.is_file():
            raise CommandError('Banco isolado pilot.sqlite3 não encontrado. Execute migrate primeiro.')
        allowed_data = {'django_migrations', 'django_content_type', 'auth_permission'}
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as connection:
            tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                if table in allowed_data or table.startswith('sqlite_'):
                    continue
                quoted = table.replace('"', '""')
                if connection.execute(f'SELECT 1 FROM "{quoted}" LIMIT 1').fetchone():
                    raise CommandError('O banco já contém dados de uso. A exportação inicial foi recusada.')
            lines = [line for line in connection.iterdump()
                     if line not in {'BEGIN TRANSACTION;', 'COMMIT;'}
                     and not line.startswith('PRAGMA')
                     and 'sqlite_sequence' not in line]
        output = Path(options['destino'])
        if output.exists():
            raise CommandError('O destino já existe; escolha um novo arquivo.')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS('SQL inicial criado sem contas, sessões ou arquivos. Ainda não aplicado ao D1.'))
