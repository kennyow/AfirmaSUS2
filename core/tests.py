import json
import os
import tempfile
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import EscalaTrabalho
from core.views.utils import ordenar_atividades_timeline


midias_views = import_module('core.views.midias')
main_views = import_module('core.views.main_views')
management_views = import_module('core.views.management_views')


class ResumoCalendarioHomeTests(TestCase):
    def test_resumo_exibe_seis_datas_mais_recentes_e_escapa_descricao(self):
        notas = [
            {'id': str(dia), 'title': f'Atividade {dia}', 'start': f'2026-10-{dia:02}',
             'description': '<script>alert(1)</script>'}
            for dia in [2, 7, 1, 5, 3, 6, 4]
        ]
        with patch.object(main_views, '_carregar_notas_calendario', return_value=notas):
            resposta = self.client.get(reverse('home'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([nota['id'] for nota in resposta.context['atividades_calendario']],
                         ['7', '6', '5', '4', '3', '2'])
        self.assertContains(resposta, '07/10/2026')
        self.assertContains(resposta, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(resposta, '<script>alert(1)</script>')

    def test_resumo_sem_notas_mantem_pagina_disponivel(self):
        with patch.object(main_views, '_carregar_notas_calendario', return_value=[]):
            resposta = self.client.get(reverse('home'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Nenhuma atividade cadastrada no calendário.')


class LinhaDoTempoMidiasTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.timeline_path = os.path.join(self.temp_dir.name, 'timeline.json')
        self.dynamic_timeline_path = os.path.join(self.temp_dir.name, 'linhadotempodinamica.json')
        with open(self.timeline_path, 'w', encoding='utf-8') as arquivo:
            json.dump([], arquivo)
        with open(self.dynamic_timeline_path, 'w', encoding='utf-8') as arquivo:
            json.dump({'title': {'text': {'headline': 'Linha do tempo'}}, 'events': []}, arquivo)
        patcher = patch.object(midias_views, 'TIMELINE_PATH', self.timeline_path)
        patcher.start()
        self.addCleanup(patcher.stop)
        dynamic_patcher = patch.object(
            midias_views, 'DYNAMIC_TIMELINE_PATH', self.dynamic_timeline_path
        )
        dynamic_patcher.start()
        self.addCleanup(dynamic_patcher.stop)
        usuario = get_user_model().objects.create_user(username='editor', password='senha-segura')
        self.client.force_login(usuario)

    def test_adiciona_atividade_com_varias_fotos_no_formato_do_json(self):
        resposta = self.client.post(
            reverse('adicionar_midia', args=['timeline']),
            {
                'data': 'Outubro / 2026',
                'titulo': 'Ação comunitária',
                'categoria': 'Saúde',
                'cor_borda': '#17A2B8',
                'descricao': 'Atividade no território.',
                'fotos': [
                    'https://example.com/foto-1.jpg',
                    'https://example.com/foto-2.jpg',
                    '',
                ],
            },
        )

        self.assertRedirects(resposta, reverse('midias'))
        with open(self.timeline_path, encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        self.assertEqual(dados, [{
            'data': 'Outubro / 2026',
            'titulo': 'Ação comunitária',
            'categoria': 'Saúde',
            'cor_borda': '#17A2B8',
            'descricao': 'Atividade no território.',
            'fotos': [
                'https://example.com/foto-1.jpg',
                'https://example.com/foto-2.jpg',
            ],
        }])

    def test_remove_atividade_da_linha_do_tempo(self):
        with open(self.timeline_path, 'w', encoding='utf-8') as arquivo:
            json.dump([{'titulo': 'Atividade'}], arquivo)

        resposta = self.client.post(
            reverse('remover_midia', args=['timeline', 0])
        )

        self.assertRedirects(resposta, reverse('midias'))
        with open(self.timeline_path, encoding='utf-8') as arquivo:
            self.assertEqual(json.load(arquivo), [])

    def test_remove_atividade_pelo_indice_da_lista_ordenada(self):
        with open(self.timeline_path, 'w', encoding='utf-8') as arquivo:
            json.dump([
                {'data': 'Maio / 2026', 'titulo': 'Atividade antiga'},
                {'data': 'Outubro 2026', 'titulo': 'Evento Canônico'},
            ], arquivo)

        resposta = self.client.post(
            reverse('remover_midia', args=['timeline', 0])
        )

        self.assertRedirects(resposta, reverse('midias'))
        with open(self.timeline_path, encoding='utf-8') as arquivo:
            atividades = json.load(arquivo)
        self.assertEqual([atividade['titulo'] for atividade in atividades], ['Atividade antiga'])

    def test_midias_mostra_atividades_sem_exibir_imagens(self):
        with open(self.timeline_path, 'w', encoding='utf-8') as arquivo:
            json.dump([{
                'data': 'Outubro / 2026',
                'titulo': 'Ação comunitária',
                'categoria': 'Saúde',
                'descricao': 'Atividade no território.',
                'fotos': ['https://example.com/foto-privada.jpg'],
            }], arquivo)

        resposta = self.client.get(reverse('midias'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Linha do Tempo de Atividades')
        self.assertContains(resposta, 'Ação comunitária')
        self.assertNotContains(resposta, 'foto-privada.jpg')

    def test_ordena_atividades_da_mais_recente_para_a_mais_antiga(self):
        atividades = [
            {'data': 'Setembro / 2026', 'titulo': 'Setembro 1'},
            {'data': 'Março / 2026', 'titulo': 'Março 1'},
            {'data': 'Agosto/ 2026', 'titulo': 'Agosto'},
            {'data': 'Maio / 2026', 'titulo': 'Maio 1'},
            {'data': 'Dezembro / 2025', 'titulo': 'Dezembro 2025'},
            {'data': 'Dezembro - Hoje / 2026', 'titulo': 'Dezembro 2026'},
            {'data': 'Junho / 2026', 'titulo': 'Junho'},
            {'data': 'Outubro 2026', 'titulo': 'Outubro'},
            {'data': 'Setembro / 2026', 'titulo': 'Setembro 2'},
            {'data': 'Maio / 2026', 'titulo': 'Maio 2'},
            {'data': 'data não informada', 'titulo': 'Sem data'},
        ]

        ordenadas = ordenar_atividades_timeline(atividades)

        self.assertEqual(
            [atividade['titulo'] for atividade in ordenadas],
            [
                'Dezembro 2026',
                'Outubro',
                'Setembro 1',
                'Setembro 2',
                'Agosto',
                'Junho',
                'Maio 1',
                'Maio 2',
                'Março 1',
                'Dezembro 2025',
                'Sem data',
            ],
        )

    def test_home_exibe_atividades_em_ordem_cronologica_decrescente(self):
        atividades = [
            {'data': 'Maio / 2026', 'titulo': 'Atividade antiga', 'fotos': []},
            {'data': 'Outubro 2026', 'titulo': 'Atividade recente', 'fotos': []},
        ]
        with open(self.timeline_path, 'w', encoding='utf-8') as arquivo:
            json.dump(atividades, arquivo)
        base_dir_patcher = patch.object(
            main_views.settings, 'DATA_DIR', Path(self.temp_dir.name)
        )
        base_dir_patcher.start()
        self.addCleanup(base_dir_patcher.stop)

        resposta = self.client.get(reverse('home'))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            [atividade['titulo'] for atividade in resposta.context['atividades_timeline']],
            ['Atividade recente', 'Atividade antiga'],
        )

    def test_formacoes_continua_em_pagina_separada(self):
        resposta = self.client.get(reverse('formacoes'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Formações &amp; Materiais')
        self.assertNotContains(resposta, 'Linha do Tempo de Atividades')

    def test_adiciona_evento_dinamico_preservando_metadados_do_arquivo(self):
        resposta = self.client.post(
            reverse('adicionar_midia', args=['timeline_dinamica']),
            {
                'year': '2026',
                'month': '2',
                'day': '9',
                'titulo': 'Reunião comunitária',
                'descricao': 'Planejamento de atividades.',
                'group': 'Eventos',
                'media_url': 'https://example.com/foto.jpg',
                'media_caption': 'Encontro no território',
            },
        )

        self.assertRedirects(resposta, reverse('midias'))
        with open(self.dynamic_timeline_path, encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        self.assertEqual(dados['title'], {'text': {'headline': 'Linha do tempo'}})
        self.assertEqual(dados['events'], [{
            'start_date': {'year': '2026', 'month': '02', 'day': '09'},
            'text': {
                'headline': 'Reunião comunitária',
                'text': 'Planejamento de atividades.',
            },
            'group': 'Eventos',
            'media': {
                'url': 'https://example.com/foto.jpg',
                'caption': 'Encontro no território',
            },
        }])

    def test_remove_evento_dinamico_preserva_titulo_e_outros_eventos(self):
        with open(self.dynamic_timeline_path, 'w', encoding='utf-8') as arquivo:
            json.dump({
                'title': {'text': {'headline': 'Linha do tempo'}},
                'events': [
                    {'text': {'headline': 'Remover'}},
                    {'text': {'headline': 'Manter'}},
                ],
            }, arquivo)

        resposta = self.client.post(
            reverse('remover_midia', args=['timeline_dinamica', 0])
        )

        self.assertRedirects(resposta, reverse('midias'))
        with open(self.dynamic_timeline_path, encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        self.assertEqual(dados['title'], {'text': {'headline': 'Linha do tempo'}})
        self.assertEqual(dados['events'], [{'text': {'headline': 'Manter'}}])


class EquipeInformacoesTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        data_dir = Path(self.temp_dir.name)
        (data_dir / 'integrantes.json').write_text(json.dumps([{
            'nome': 'Integrante de teste',
            'curso': 'Enfermagem',
            'situacao': 'Bolsista',
            'foto': 'https://drive.google.com/file/d/foto_teste/view',
        }]), encoding='utf-8')
        patcher = patch.object(main_views.settings, 'DATA_DIR', data_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_pagina_exibe_integrantes_e_secao_informacoes(self):
        resposta = self.client.get(reverse('equipe_informacoes'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Equipe e Informações')
        self.assertContains(resposta, 'Integrante de teste')
        self.assertContains(resposta, 'Enfermagem')
        self.assertContains(resposta, 'Bolsista')
        self.assertContains(resposta, 'Informações')
        self.assertContains(
            resposta,
            'https://lh3.googleusercontent.com/d/foto_teste',
        )

    def test_pagina_exibe_plataformas_com_links_e_logos(self):
        resposta = self.client.get(reverse('equipe_informacoes'))

        self.assertEqual(resposta.status_code, 200)
        plataformas_esperadas = {
            'Ushahidi': (
                'https://kennyow.ushahidi.io/map',
                'https://lh3.googleusercontent.com/d/1Y7DiHORMbXRFZfM-v3jTHC07aSl6sYse',
                'Mapeamento colaborativo.',
            ),
            'Partimap': (
                'https://www.partimap.eu/en/p/AfirmaSUSJP/0?force=1',
                'https://lh3.googleusercontent.com/d/1UJOoYTfH2HXFPEzPurd_gCE3qmqirWgp',
                'Cartografia comunitária.',
            ),
            'ChronoFlo': (
                'https://www.chronoflotimeline.com/timeline/shared/32199/AfirmaSUS/',
                'https://lh3.googleusercontent.com/d/1z3b8OyQeX2PMXoCLO3g-_pFtsNdhUi0G',
                'Linha do tempo interativa.',
            ),
            'Instagram': (
                'https://www.instagram.com/afirmasusjp/',
                'https://lh3.googleusercontent.com/d/1P6sTla2_5gbSwTpraremHHL9uGRAQ7Vp',
                'Perfil oficial do projeto.',
            ),
        }

        for nome, (url, logo_url, descricao) in plataformas_esperadas.items():
            with self.subTest(plataforma=nome):
                self.assertContains(resposta, nome)
                self.assertContains(resposta, url)
                self.assertContains(resposta, logo_url)
                self.assertContains(resposta, descricao)

        self.assertContains(resposta, 'rel="noopener noreferrer"')
        self.assertContains(resposta, 'target="_blank"')

    def test_nova_aba_aparece_na_navegacao_como_ativa(self):
        resposta = self.client.get(reverse('equipe_informacoes'))

        self.assertContains(
            resposta,
            'class="subnav-link active"',
            html=False,
        )
        self.assertContains(resposta, '👥 Equipe e Informações')


class EscalaTrabalhoTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.calendario_notas_path = Path(self.temp_dir.name) / 'calendario_notas.json'
        notas_patcher = patch.object(
            management_views, 'CALENDARIO_NOTAS_PATH', self.calendario_notas_path
        )
        notas_patcher.start()
        self.addCleanup(notas_patcher.stop)
        usuario = get_user_model().objects.create_user(username='editor', password='senha-segura')
        self.client.force_login(usuario)
        self.escala = EscalaTrabalho.objects.create(
            dia_semana='Segunda-feira',
            turno='Manhã',
            horario_inicio='08:00',
            horario_fim='12:00',
        )

    def test_exclui_horario_da_escala(self):
        resposta = self.client.post(
            reverse('deletar_escala', args=[self.escala.pk])
        )

        self.assertRedirects(resposta, reverse('pagina_escala'))
        self.assertFalse(EscalaTrabalho.objects.filter(pk=self.escala.pk).exists())

    def test_exclusao_da_escala_nao_aceita_get(self):
        resposta = self.client.get(
            reverse('deletar_escala', args=[self.escala.pk])
        )

        self.assertEqual(resposta.status_code, 405)

    def test_grade_identifica_cada_turno_com_uma_cor(self):
        for turno in ('Tarde', 'Noite', 'Integral'):
            EscalaTrabalho.objects.create(
                dia_semana='Segunda-feira',
                turno=turno,
            )

        resposta = self.client.get(reverse('pagina_escala'))

        self.assertContains(resposta, 'class="badge bg-warning text-dark me-1">Manhã</span>')
        self.assertContains(resposta, 'class="badge bg-primary me-1">Tarde</span>')
        self.assertContains(resposta, 'class="badge bg-dark me-1">Noite</span>')
        self.assertContains(resposta, 'class="badge bg-success me-1">Integral</span>')

    def test_calendario_carrega_eventos_do_arquivo_json(self):
        eventos = [{
            'id': 'evento-importado-calendario-001',
            'title': 'Atividade de teste',
            'start': '2026-10-12',
            'end': '2026-10-12',
            'backgroundColor': '#4C2059',
            'description': 'Detalhes do evento.',
        }]
        self.calendario_notas_path.write_text(json.dumps(eventos), encoding='utf-8')
        resposta = self.client.get(reverse('pagina_escala'))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['calendario_eventos'][0]['title'], 'Atividade de teste')
        self.assertEqual(
            resposta.context['calendario_eventos'][0]['extendedProps']['description'],
            'Detalhes do evento.',
        )
        self.assertTrue(resposta.context['calendario_eventos'][0]['extendedProps']['isNote'])
        self.assertNotIn('end', resposta.context['calendario_eventos'][0])
        self.assertContains(resposta, 'activities-calendar')

    def test_adiciona_nota_e_exibe_no_calendario(self):
        resposta = self.client.post(
            reverse('adicionar_nota_calendario'),
            {
                'date': '2026-10-12',
                'title': 'Lembrete importante',
                'description': 'Levar os materiais.',
            },
        )

        self.assertRedirects(resposta, reverse('pagina_escala'))
        notas = json.loads(self.calendario_notas_path.read_text(encoding='utf-8'))
        self.assertEqual(len(notas), 1)
        self.assertEqual(notas[0]['title'], 'Lembrete importante')

        resposta = self.client.get(reverse('pagina_escala'))
        nota_calendario = next(
            evento for evento in resposta.context['calendario_eventos']
            if evento.get('id') == notas[0]['id']
        )
        self.assertTrue(nota_calendario['extendedProps']['isNote'])
        self.assertEqual(nota_calendario['backgroundColor'], '#381246')

    def test_exclui_evento_importado_do_calendario(self):
        self.calendario_notas_path.write_text(json.dumps([{
            'id': 'evento-importado-calendario-001',
            'title': 'Remover',
            'start': '2026-10-12',
            'description': '',
        }]), encoding='utf-8')

        resposta = self.client.post(
            reverse('deletar_nota_calendario', args=['evento-importado-calendario-001'])
        )

        self.assertRedirects(resposta, reverse('pagina_escala'))
        self.assertEqual(
            json.loads(self.calendario_notas_path.read_text(encoding='utf-8')),
            [],
        )

    def test_nao_permite_criar_nota_com_data_invalida(self):
        resposta = self.client.post(
            reverse('adicionar_nota_calendario'),
            {'date': 'data-invalida', 'title': 'Teste', 'description': ''},
        )

        self.assertRedirects(resposta, reverse('pagina_escala'))
        self.assertFalse(self.calendario_notas_path.exists())

    def test_edita_evento_importado_mantendo_metadados_e_identificador(self):
        evento_original = {
            'id': 'evento-importado-calendario-001',
            'title': 'Evento antes da edição',
            'start': '2026-10-12',
            'end': '2026-10-12',
            'backgroundColor': '#FF8C00',
            'borderColor': '#FF8C00',
            'textColor': '#ffffff',
            'description': 'Descrição antiga.',
        }
        self.calendario_notas_path.write_text(
            json.dumps([evento_original]), encoding='utf-8'
        )

        resposta = self.client.post(
            reverse('editar_nota_calendario', args=[evento_original['id']]),
            {
                'date': '2026-10-14',
                'title': 'Evento atualizado',
                'description': 'Nova descrição.',
            },
        )

        self.assertRedirects(resposta, reverse('pagina_escala'))
        evento_editado = json.loads(
            self.calendario_notas_path.read_text(encoding='utf-8')
        )[0]
        self.assertEqual(evento_editado['id'], evento_original['id'])
        self.assertEqual(evento_editado['title'], 'Evento atualizado')
        self.assertEqual(evento_editado['start'], '2026-10-14')
        self.assertEqual(evento_editado['end'], '2026-10-14')
        self.assertEqual(evento_editado['description'], 'Nova descrição.')
        self.assertEqual(evento_editado['backgroundColor'], '#FF8C00')
