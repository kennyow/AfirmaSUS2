import pandas as pd
import re
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Perfil

class Command(BaseCommand):
    help = 'Importa usuários e perfis a partir de uma planilha Excel (.xlsx)'

    def add_arguments(self, parser):
        parser.add_argument('caminho_excel', type=str, help='Caminho completo do arquivo Excel')

    def handle(self, *args, **kwargs):
        caminho = kwargs['caminho_excel']
        self.stdout.write(self.style.WARNING(f"Lendo arquivo: {caminho}"))

        try:
            df = pd.read_excel(caminho)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao abrir o arquivo: {e}"))
            return

        criados = 0
        ignorados = 0

        for index, row in df.iterrows():
            nome = str(row.get('Nome', '')).strip()
            email = str(row.get('Email', '')).strip().lower()
            cpf_raw = str(row.get('CPF', ''))
            
            # Limpa o CPF deixando apenas os dígitos numéricos
            cpf_limpo = re.sub(r'\D', '', cpf_raw)

            if not email or not cpf_limpo or email == 'nan':
                self.stdout.write(self.style.ERROR(f"Linha {index+2}: Email ou CPF inválido/vazio. Ignorando..."))
                ignorados += 1
                continue

            # Verifica se o usuário já existe no Django
            if User.objects.filter(username=email).exists():
                self.stdout.write(self.style.WARNING(f"Usuário {email} já existe. Ignorando..."))
                ignorados += 1
                continue

            # Separa primeiro nome e sobrenome
            partes_nome = nome.split(' ', 1)
            first_name = partes_nome[0]
            last_name = partes_nome[1] if len(partes_nome) > 1 else ''

            # Cria o usuário com E-mail no username e CPF limpo como Senha
            user = User.objects.create_user(
                username=email,
                email=email,
                password=cpf_limpo,
                first_name=first_name,
                last_name=last_name
            )

            # Trata data de nascimento (se existir)
            data_nasc = row.get('Data de Nascimento')
            if pd.isna(data_nasc):
                data_nasc = None

            # Cria o perfil associado ao usuário
            Perfil.objects.create(
                user=user,
                cpf=cpf_limpo,
                data_nascimento=data_nasc
            )

            criados += 1
            self.stdout.write(self.style.SUCCESS(f"✅ Usuário criado: {nome} ({email})"))

        self.stdout.write(self.style.SUCCESS(f"\nConcluído! {criados} usuários criados e {ignorados} ignorados/existentes."))