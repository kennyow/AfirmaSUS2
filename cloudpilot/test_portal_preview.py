import json
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import AtaReuniao, EscalaTrabalho, Integrante, Local, NotaCalendario
from core.views.atas import _conteudo_vazio
from .test_pilot import png


class PortalPreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('preview-admin', password='test-only-password')
        cls.member = User.objects.create_user('preview-member', password='test-only-password')

    def test_all_original_sections_render_for_admin(self):
        self.client.force_login(self.admin)
        names = ('home', 'pagina_mapa', 'pagina_escala', 'equipe_informacoes',
                 'atas', 'fila_atas', 'lembretes_atas', 'formacoes', 'midias',
                 'levantamento_estatistico')
        for name in names:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Prévia para revisão')
                self.assertNotContains(response, 'drive.google.com')
                self.assertNotContains(response, 'googleusercontent.com')

    def test_public_sections_and_private_minutes(self):
        for name in ('home', 'pagina_mapa', 'pagina_escala', 'equipe_informacoes',
                     'formacoes', 'midias', 'levantamento_estatistico'):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertEqual(reverse('home'), '/')
        self.assertEqual(self.client.get(reverse('atas')).status_code, 302)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get('/plataforma/').status_code, 200)
        self.assertEqual(self.client.get(reverse('atas')).status_code, 403)

    def test_post_and_legacy_get_deletion_are_blocked(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse('adicionar_midia', args=['formacao']), {'titulo': 'Não publicar'}).status_code, 405)
        self.assertEqual(self.client.post(reverse('home')).status_code, 405)

    def test_admin_can_confirm_and_delete_only_unlinked_locations(self):
        local = Local.objects.create(nome='Local de teste', lat=-7, lon=-34)
        delete = reverse('deletar_local', args=[local.pk])
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(delete).status_code, 403)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(delete), 'Sim, excluir')
        self.assertTrue(Local.objects.filter(pk=local.pk).exists())
        shift = EscalaTrabalho.objects.create(local=local)
        self.assertRedirects(self.client.post(delete), reverse('editar_local', args=[local.pk]))
        self.assertTrue(EscalaTrabalho.objects.filter(pk=shift.pk, local=local).exists())
        shift.delete()
        self.assertRedirects(self.client.post(delete), reverse('pagina_mapa'))
        self.assertFalse(Local.objects.filter(pk=local.pk).exists())

    def test_original_registration_is_not_exposed(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/plataforma/cadastrar/').status_code, 404)

    def test_admin_can_save_and_edit_map_location(self):
        self.client.force_login(self.admin)
        data = {'nome': 'Local de teste', 'categoria': 'Saúde', 'lat': '-7.13', 'lon': '-34.85'}
        self.assertRedirects(self.client.post(reverse('cadastrar_local'), data), reverse('pagina_mapa'))
        local = Local.objects.get()
        edit = reverse('editar_local', args=[local.pk])
        self.assertRedirects(self.client.post(edit, {**data, 'nome': 'Local revisado'}), reverse('pagina_mapa'))
        local.refresh_from_db()
        self.assertEqual(local.nome, 'Local revisado')
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(edit, data).status_code, 403)

    @patch('core.forms.default_storage')
    def test_uploaded_photo_replaces_link_on_map(self, storage):
        self.client.force_login(self.admin)
        local = Local.objects.create(nome='Local de teste', lat=-7, lon=-34)
        storage.url.return_value = 'https://media.example.test/locais/foto.png'
        response = self.client.post(reverse('editar_local', args=[local.pk]), {
            'nome': local.nome, 'categoria': 'Saúde', 'lat': '-7', 'lon': '-34',
            'foto': 'https://example.test/anterior.jpg', 'foto_upload': png(),
        })
        self.assertRedirects(response, reverse('pagina_mapa'))
        local.refresh_from_db()
        self.assertEqual(local.foto, storage.url.return_value)
        key, uploaded = storage.save.call_args.args
        self.assertRegex(key, r'^locais/[0-9a-f]{32}\.png$')
        self.assertEqual(uploaded.content_type, 'image/png')

    def test_admin_can_create_and_link_schedule_to_location(self):
        integrante = Integrante.objects.create(nome='Integrante de teste')
        local = Local.objects.create(nome='Local de teste', lat=-7, lon=-34)
        data = {'integrante': integrante.pk, 'dia_semana': 'Segunda-feira', 'turno': 'Manhã',
                'horario_inicio': '08:00', 'horario_fim': '12:00'}
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(reverse('cadastrar_escala'), data), reverse('pagina_escala'))
        escala = EscalaTrabalho.objects.get()
        self.assertIsNone(escala.local_id)
        edit = reverse('editar_escala', args=[escala.pk])
        self.assertRedirects(self.client.post(edit, {**data, 'local': local.pk}), reverse('pagina_escala'))
        escala.refresh_from_db()
        self.assertEqual(escala.local_id, local.pk)
        self.assertEqual(EscalaTrabalho.objects.count(), 1)
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(edit, data).status_code, 403)

    def test_library_and_shared_login_stay_available(self):
        self.assertEqual(reverse('login'), '/login/')
        self.assertEqual(reverse('logout'), '/logout/')
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/health/').status_code, 200)

    def test_admin_can_create_and_edit_minutes_in_preview(self):
        self.client.force_login(self.admin)
        data = {'titulo': 'Ata piloto', 'data': '2026-11-06', 'conteudo': json.dumps(_conteudo_vazio())}
        self.assertEqual(self.client.post(reverse('nova_ata'), data).status_code, 302)
        ata = AtaReuniao.objects.get()
        edit = reverse('editar_ata', args=[ata.pk])
        response = self.client.post(edit, {**data, 'titulo': 'Ata revisada'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json(), {'ok': True, 'url': edit})
        ata.refresh_from_db()
        self.assertEqual(ata.titulo, 'Ata revisada')
        self.assertEqual(ata.criada_por, self.admin)
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(edit, data).status_code, 403)

    def test_admin_can_queue_and_export_minutes_in_preview(self):
        self.client.force_login(self.admin)
        ata = AtaReuniao.objects.create(
            titulo='Ata piloto', data='2026-11-06', conteudo=_conteudo_vazio(),
            criada_por=self.admin, atualizada_por=self.admin,
        )
        fila = reverse('alterar_fila_ata', args=[ata.pk])
        exportar = reverse('exportar_atas')
        data = {'atas': [str(ata.pk)], 'formatos': ['pdf', 'docx', 'xlsx'], 'modo': 'juntos'}
        self.assertEqual(self.client.get(fila).status_code, 405)
        self.assertEqual(self.client.post(fila).status_code, 302)
        self.assertContains(self.client.get(reverse('fila_atas')), 'Ata piloto')
        response = self.client.post(exportar, data)
        self.assertEqual(response.status_code, 200)
        with ZipFile(BytesIO(response.content)) as archive:
            self.assertEqual(set(archive.namelist()), {'Atas_Reuniao.pdf', 'Atas_Reuniao.docx', 'Atas_Reuniao.xlsx'})
        ata.refresh_from_db()
        self.assertIsNotNone(ata.exportada_em)
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(exportar, data).status_code, 403)

    def test_only_admin_can_complete_a_minutes_reminder(self):
        content = _conteudo_vazio()
        content['acoes'] = [{'id': 'acao-1', 'lembrete': {'data': '2026-11-06'}}]
        ata = AtaReuniao.objects.create(
            titulo='Ata com lembrete', data='2026-11-06', conteudo=content,
            criada_por=self.admin, atualizada_por=self.admin,
        )
        concluir = reverse('concluir_acao_ata', args=[ata.pk, 'acao-1'])
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(concluir).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(concluir).status_code, 405)
        response = self.client.post(concluir, follow=True)
        self.assertContains(response, 'Ata com lembrete')
        ata.refresh_from_db()
        self.assertEqual(ata.conteudo['acoes'][0]['status'], 'Concluída')

    @override_settings(CALENDARIO_NO_BANCO=True)
    def test_admin_can_add_and_edit_persistent_calendar_note(self):
        self.client.force_login(self.admin)
        data = {'title': 'Reunião de teste', 'date': '2026-11-06', 'description': 'Descrição'}
        self.assertRedirects(self.client.post(reverse('adicionar_nota_calendario'), data), reverse('pagina_escala'))
        nota = NotaCalendario.objects.get()
        edit = reverse('editar_nota_calendario', args=[nota.pk])
        self.assertRedirects(self.client.post(edit, {**data, 'title': 'Reunião atualizada'}), reverse('pagina_escala'))
        response = self.client.get(reverse('pagina_escala'))
        self.assertEqual(response.context['calendario_eventos'][0]['title'], 'Reunião atualizada')
        self.assertEqual(NotaCalendario.objects.count(), 1)
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(edit, data).status_code, 403)
