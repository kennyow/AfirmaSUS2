import json
import re
from datetime import date, timedelta
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import AtaReuniao, Integrante


class AtasTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='editor-atas',
            password='senha-segura',
        )
        self.client.force_login(self.usuario)

    def conteudo_valido(self, **overrides):
        conteudo = {
            'participantes': {'presentes': ['Ana'], 'ausentes': []},
            'assuntos': {
                'itens': [{'id': 'assunto-1', 'titulo': 'Planejamento', 'discussao': 'Organizar as ações.'}],
                'observacoes': '',
            },
            'decisoes': {'itens': ['Realizar novo encontro.'], 'justificativas': ''},
            'acoes': [{
                'id': 'acao-1',
                'tarefa': 'Enviar convite',
                'responsavel': 'Ana',
                'prazo': '',
                'status': 'Pendente',
                'lembrete': {'data': '', 'hora': ''},
            }],
            'pendencias': {'itens': ['Confirmar local'], 'proximos_passos': ''},
            'encerramento': {'horario_termino': '11:00', 'proxima_reuniao': ''},
            'anotacoes': '10:15 — A reunião começou.',
            'horario_automatico': True,
        }
        conteudo.update(overrides)
        return conteudo

    def dados_post(self, **overrides):
        dados = {
            'titulo': 'Planejamento da equipe',
            'data': date.today().isoformat(),
            'horario': '10:00',
            'local': 'UBS Centro',
            'coordenador': 'Ana',
            'responsavel': 'João',
            'conteudo': json.dumps(self.conteudo_valido(), ensure_ascii=False),
        }
        dados.update(overrides)
        return dados

    def criar_ata(self, **overrides):
        return AtaReuniao.objects.create(
            titulo='Planejamento da equipe',
            data=date.today(),
            horario='10:00',
            local='UBS Centro',
            coordenador='Ana',
            responsavel='João',
            conteudo=self.conteudo_valido(),
            criada_por=self.usuario,
            atualizada_por=self.usuario,
            **overrides,
        )

    def test_todas_as_paginas_e_acoes_exigem_login(self):
        self.client.logout()

        for url in (
            reverse('atas'),
            reverse('nova_ata'),
            reverse('fila_atas'),
            reverse('lembretes_atas'),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_cria_ata_e_salva_secoes_estruturadas(self):
        resposta = self.client.post(reverse('nova_ata'), self.dados_post())

        self.assertRedirects(resposta, reverse('editar_ata', args=[1]))
        ata = AtaReuniao.objects.get()
        self.assertEqual(ata.criada_por, self.usuario)
        self.assertEqual(ata.conteudo['participantes']['presentes'], ['Ana'])
        self.assertEqual(ata.conteudo['assuntos']['itens'][0]['titulo'], 'Planejamento')

    def test_salvamento_automatico_retorna_url_de_edicao(self):
        resposta = self.client.post(
            reverse('nova_ata'),
            self.dados_post(),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['ok'])
        ata = AtaReuniao.objects.get()
        self.assertEqual(resposta.json()['url'], reverse('editar_ata', args=[ata.pk]))

    def test_formulario_novo_ata_renderiza_secoes_editaveis(self):
        Integrante.objects.create(nome='Mariana Lima')
        resposta = self.client.get(reverse('nova_ata'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Informações gerais')
        self.assertContains(resposta, 'Assuntos discutidos')
        self.assertContains(resposta, 'Anotações da reunião')
        self.assertContains(resposta, 'id="ata-conteudo-json"')
        self.assertContains(resposta, 'id="ata-integrantes-json"')
        self.assertContains(resposta, 'Mariana Lima')
        self.assertContains(resposta, 'data-people-list="presentes"')
        self.assertContains(resposta, 'data-people-list="ausentes"')

    def test_formulario_edicao_mantem_participante_salvo_que_nao_esta_no_cadastro(self):
        ata = self.criar_ata()

        resposta = self.client.get(reverse('editar_ata', args=[ata.pk]))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Ana')

    def test_rejeita_status_de_acao_invalido(self):
        conteudo = self.conteudo_valido()
        conteudo['acoes'][0]['status'] = 'Desconhecido'

        resposta = self.client.post(
            reverse('nova_ata'),
            self.dados_post(conteudo=json.dumps(conteudo)),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(AtaReuniao.objects.exists())

    def test_usuarios_autenticados_compartilham_e_podem_editar_atas(self):
        ata = self.criar_ata()
        outro_usuario = get_user_model().objects.create_user(
            username='outro-editor',
            password='senha-segura',
        )
        self.client.force_login(outro_usuario)

        resposta = self.client.get(reverse('editar_ata', args=[ata.pk]))

        self.assertEqual(resposta.status_code, 200)
        dados = self.dados_post(titulo='Ata atualizada pela equipe')
        resposta = self.client.post(reverse('editar_ata', args=[ata.pk]), dados)

        self.assertRedirects(resposta, reverse('editar_ata', args=[ata.pk]))
        ata.refresh_from_db()
        self.assertEqual(ata.titulo, 'Ata atualizada pela equipe')
        self.assertEqual(ata.atualizada_por, outro_usuario)

    def test_busca_encontra_conteudo_e_aba_fica_ativa(self):
        self.criar_ata()

        resposta = self.client.get(reverse('atas'), {'q': 'Organizar as ações'})

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Planejamento da equipe')
        self.assertContains(resposta, '📝 Atas')
        self.assertContains(resposta, 'class="subnav-link active"', html=False)

    def test_fila_exporta_pdf_word_e_excel_em_arquivo_zip(self):
        ata = self.criar_ata(na_fila=True)

        resposta = self.client.post(
            reverse('exportar_atas'),
            {
                'atas': [str(ata.pk)],
                'formatos': ['pdf', 'docx', 'xlsx'],
                'modo': 'juntos',
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta['Content-Type'], 'application/zip')
        with ZipFile(BytesIO(resposta.content)) as arquivo_zip:
            self.assertEqual(
                set(arquivo_zip.namelist()),
                {'Atas_Reuniao.pdf', 'Atas_Reuniao.docx', 'Atas_Reuniao.xlsx'},
            )
            pdf = arquivo_zip.read('Atas_Reuniao.pdf')
            self.assertTrue(pdf.startswith(b'%PDF-1.4'))
            xref = int(re.search(rb'startxref\n(\d+)', pdf).group(1))
            self.assertEqual(pdf[xref:xref + 4], b'xref')
            with ZipFile(BytesIO(arquivo_zip.read('Atas_Reuniao.docx'))) as docx:
                self.assertIn('word/document.xml', docx.namelist())
                document = docx.read('word/document.xml')
                ElementTree.fromstring(document)
                self.assertIn('Planejamento da equipe', document.decode())
            with ZipFile(BytesIO(arquivo_zip.read('Atas_Reuniao.xlsx'))) as xlsx:
                self.assertIn('xl/worksheets/sheet1.xml', xlsx.namelist())
                worksheet = xlsx.read('xl/worksheets/sheet1.xml')
                ElementTree.fromstring(worksheet)
                self.assertIn('Enviar convite', worksheet.decode())
        ata.refresh_from_db()
        self.assertIsNotNone(ata.exportada_em)

    def test_fila_nao_exporta_ata_que_nao_esta_marcada(self):
        ata = self.criar_ata()

        resposta = self.client.post(
            reverse('exportar_atas'),
            {'atas': [str(ata.pk)], 'formatos': ['pdf'], 'modo': 'juntos'},
        )

        self.assertRedirects(resposta, reverse('fila_atas'))
        self.assertFalse(AtaReuniao.objects.get(pk=ata.pk).exportada_em)

    def test_lembrete_pode_ser_concluido(self):
        ata = self.criar_ata()
        ata.conteudo['acoes'][0]['lembrete'] = {
            'data': date.today().isoformat(),
            'hora': '09:00',
        }
        ata.save(update_fields=['conteudo'])
        resposta = self.client.post(
            reverse('concluir_acao_ata', args=[ata.pk, 'acao-1'])
        )

        self.assertRedirects(resposta, reverse('lembretes_atas'))
        ata.refresh_from_db()
        self.assertEqual(ata.conteudo['acoes'][0]['status'], 'Concluída')
        self.assertContains(self.client.get(reverse('lembretes_atas')), 'Concluída')

    def test_lembretes_separam_acoes_atrasadas(self):
        ata = self.criar_ata()
        ata.conteudo['acoes'][0]['lembrete'] = {
            'data': (timezone.localdate() - timedelta(days=1)).isoformat(),
            'hora': '09:00',
        }
        ata.save(update_fields=['conteudo'])

        resposta = self.client.get(reverse('lembretes_atas'))

        self.assertContains(resposta, 'Atrasados')
        self.assertContains(resposta, 'Enviar convite')
