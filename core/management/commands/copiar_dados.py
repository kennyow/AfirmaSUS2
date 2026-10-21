"""Copia dados para um destino novo, para migração ou backup com o app parado."""
from pathlib import Path
from contextlib import closing
import shutil
import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Copia SQLite, JSON e uploads para uma pasta nova. Pare o servidor antes de executar.'

    def add_arguments(self, parser):
        parser.add_argument('destino', type=Path)

    def handle(self, *args, **options):
        source = settings.DATA_DIR.resolve()
        destination = options['destino']
        if not destination.is_absolute():
            raise CommandError('O destino deve ser um caminho absoluto.')
        destination = destination.resolve()
        if destination == source or source in destination.parents:
            raise CommandError('O destino deve ficar fora da pasta de dados de origem.')
        if destination.exists():
            raise CommandError('O destino já existe. Use uma pasta nova para evitar sobrescritas.')
        database = source / 'db.sqlite3'
        if not database.is_file():
            raise CommandError('Banco db.sqlite3 não encontrado na origem.')
        destination.mkdir(parents=True)
        try:
            with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as original:
                with closing(sqlite3.connect(destination / 'db.sqlite3')) as copy:
                    original.backup(copy)
                    if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise CommandError('Falha na verificação da cópia SQLite.')
            for path in source.glob('*.json'):
                shutil.copy2(path, destination / path.name)
            if (source / 'media').is_dir():
                shutil.copytree(source / 'media', destination / 'media')
            else:
                (destination / 'media').mkdir()
        except (OSError, sqlite3.Error) as error:
            raise CommandError(
                'Cópia incompleta; não use o destino. Escolha outra pasta ao tentar novamente.'
            ) from error
        self.stdout.write(self.style.SUCCESS('Dados copiados e integridade SQLite verificada.'))
