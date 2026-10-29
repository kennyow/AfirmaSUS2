from io import StringIO
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from core.models import Perfil, UsuarioAutorizado


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ImportarUsuariosTests(TestCase):
    def setUp(self):
        self.row = {'Nome': 'Integrante Exemplo', 'Email': 'pessoa@example.test',
                    'CPF': '00001234567', 'Data de Nascimento': '2000-01-02'}

    def importar(self, rows=None, **kwargs):
        with patch('core.management.commands.importar_usuarios_excel.pd.read_excel',
                   return_value=pd.DataFrame(rows or [self.row])):
            call_command('importar_usuarios_excel', 'origem.xlsx', stdout=StringIO(), **kwargs)

    def test_cria_conta_perfil_e_autorizacao_sem_privilegios(self):
        self.importar()
        user = get_user_model().objects.get(username=self.row['Email'])
        self.assertTrue(user.check_password(self.row['CPF']))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.perfil.cpf, self.row['CPF'])
        self.assertTrue(UsuarioAutorizado.objects.get(email=user.email).ativo)

    def test_repetir_importacao_preserva_senha_personalizada_e_avatar(self):
        self.importar()
        user = get_user_model().objects.get()
        user.set_password('senha-personalizada')
        user.save()
        original_hash = user.password
        user.perfil.avatar = 'avatares/existente.png'
        user.perfil.save()
        self.importar()
        user.refresh_from_db()
        self.assertEqual(user.password, original_hash)
        self.assertEqual(user.perfil.avatar.name, 'avatares/existente.png')
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(UsuarioAutorizado.objects.count(), 1)

    def test_login_exato_nao_altera_admin_com_mesmo_email(self):
        admin = get_user_model().objects.create_superuser('admin', self.row['Email'], 'senha-admin')
        integrante = get_user_model().objects.create_user(self.row['Email'], self.row['Email'], 'senha-integrante')
        Perfil.objects.create(user=integrante, cpf=self.row['CPF'])
        self.importar()
        admin.refresh_from_db()
        self.assertTrue(admin.check_password('senha-admin'))
        self.assertEqual(admin.first_name, '')
        self.assertTrue(integrante.check_password('senha-integrante'))
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_cpf_formatado_identifica_login_personalizado(self):
        user = get_user_model().objects.create_user('login-personalizado', '', 'senha-atual')
        Perfil.objects.create(user=user, cpf='000.012.345-67')
        self.importar()
        user.refresh_from_db()
        self.assertEqual(user.username, 'login-personalizado')
        self.assertTrue(user.check_password('senha-atual'))
        self.assertEqual(user.perfil.cpf, self.row['CPF'])
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_simulacao_nao_salva_contas_ou_autorizacoes(self):
        self.importar(dry_run=True)
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(Perfil.objects.exists())
        self.assertFalse(UsuarioAutorizado.objects.exists())

    def test_conflito_de_identidade_reverte_toda_importacao(self):
        user = get_user_model().objects.create_user('outra@example.test', '', 'senha-atual')
        Perfil.objects.create(user=user, cpf='11111111111')
        conflito = dict(self.row, Email=user.username, CPF='22222222222')
        with self.assertRaises(CommandError):
            self.importar([self.row, conflito])
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertFalse(UsuarioAutorizado.objects.exists())

    def test_redefinicao_de_senha_exige_opcao_explicita(self):
        self.importar()
        user = get_user_model().objects.get()
        user.set_password('senha-personalizada')
        user.save()
        self.importar(reset_passwords=True)
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.row['CPF']))

    def test_preserva_bloqueios_manuais(self):
        self.importar()
        get_user_model().objects.update(is_active=False)
        UsuarioAutorizado.objects.update(ativo=False)
        self.importar()
        self.assertFalse(get_user_model().objects.get().is_active)
        self.assertFalse(UsuarioAutorizado.objects.get().ativo)

    def test_corrige_zero_inicial_no_cpf_e_na_senha_inicial_antiga(self):
        legado = self.row['CPF'].lstrip('0')
        user = get_user_model().objects.create_user(self.row['Email'], self.row['Email'], legado)
        Perfil.objects.create(user=user, cpf=legado)
        self.importar()
        user.refresh_from_db()
        self.assertEqual(user.perfil.cpf, self.row['CPF'])
        self.assertTrue(user.check_password(self.row['CPF']))
        self.assertFalse(user.check_password(legado))

    def test_corrigir_zero_do_documento_preserva_senha_personalizada(self):
        user = get_user_model().objects.create_user(self.row['Email'], self.row['Email'], 'senha-personalizada')
        Perfil.objects.create(user=user, cpf=self.row['CPF'].lstrip('0'))
        senha_hash = user.password
        self.importar()
        user.refresh_from_db()
        self.assertEqual(user.perfil.cpf, self.row['CPF'])
        self.assertEqual(user.password, senha_hash)
