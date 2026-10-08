import json
import os
from django.core.management.base import BaseCommand
from core.models import Local, Integrante, Atividade

class Command(BaseCommand):
    help = 'Importa os dados dos arquivos JSON antigos para o banco de dados do Django'

    def handle(self, *args, **options):
        # ---------------------------------------------------------
        # 1. IMPORTAÇÃO DOS LOCAIS (dados_locais.json)
        # ---------------------------------------------------------
        caminho_locais = 'dados_locais.json'
        if os.path.exists(caminho_locais):
            with open(caminho_locais, 'r', encoding='utf-8') as f:
                dados_locais = json.load(f)
                
            qtd_locais = 0
            for item in dados_locais:
                # get_or_create evita duplicar o registro no banco se já existir
                local, created = Local.objects.get_or_create(
                    nome=item.get('nome'),
                    defaults={
                        'distrito': item.get('distrito', ''),
                        'categoria': item.get('categoria', 'Saúde'),
                        'lat': float(item.get('lat', 0.0)),
                        'lon': float(item.get('lon', 0.0)),
                        'status': item.get('status', ''),
                        'cor': item.get('cor', 'purple'),
                        'icone': item.get('icone', 'hospital'),
                        'foto': item.get('foto', ''),
                        'descricao': item.get('descricao', ''),
                    }
                )
                if created:
                    qtd_locais += 1
            self.stdout.write(self.style.SUCCESS(f' Successfully imported {qtd_locais} novos locais!'))
        else:
            self.stdout.write(self.style.WARNING(f' Arquivo {caminho_locais} não encontrado na raiz.'))

        # ---------------------------------------------------------
        # 2. IMPORTAÇÃO DOS INTEGRANTES (integrantes.json)
        # ---------------------------------------------------------
        caminho_integrantes = 'integrantes.json'
        if os.path.exists(caminho_integrantes):
            with open(caminho_integrantes, 'r', encoding='utf-8') as f:
                dados_integrantes = json.load(f)
                
            qtd_integrantes = 0
            for item in dados_integrantes:
                integrante, created = Integrante.objects.get_or_create(
                    nome=item.get('nome'),
                    defaults={
                        'curso': item.get('curso', ''),
                        'situacao': item.get('situacao', ''),
                        'foto': item.get('foto', ''),
                    }
                )
                if created:
                    qtd_integrantes += 1
            self.stdout.write(self.style.SUCCESS(f' Successfully imported {qtd_integrantes} novos integrantes!'))
        else:
            self.stdout.write(self.style.WARNING(f' Arquivo {caminho_integrantes} não encontrado na raiz.'))