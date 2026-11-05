from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Local


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
                self.assertContains(response, 'Somente consulta')
                self.assertNotContains(response, 'drive.google.com')
                self.assertNotContains(response, 'googleusercontent.com')

    def test_preview_is_private_even_when_url_is_known(self):
        self.assertEqual(self.client.get('/plataforma/').status_code, 302)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get('/plataforma/').status_code, 403)

    def test_post_and_legacy_get_deletion_are_blocked(self):
        self.client.force_login(self.admin)
        local = Local.objects.create(nome='Local de teste', lat=-7, lon=-34)
        self.assertEqual(self.client.get(reverse('deletar_local', args=[local.pk])).status_code, 405)
        self.assertTrue(Local.objects.filter(pk=local.pk).exists())
        self.assertEqual(self.client.post(reverse('adicionar_midia', args=['formacao']), {'titulo': 'Não publicar'}).status_code, 405)
        self.assertEqual(self.client.post(reverse('home')).status_code, 405)

    def test_original_registration_is_not_exposed(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/plataforma/cadastrar/').status_code, 404)

    def test_library_and_shared_login_stay_available(self):
        self.assertEqual(reverse('login'), '/login/')
        self.assertEqual(reverse('logout'), '/logout/')
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/health/').status_code, 200)
