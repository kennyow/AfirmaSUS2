# core/forms.py

import os
import json
from datetime import date, time
from django import forms
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import AtaReuniao, Local, Atividade, EscalaTrabalho, UsuarioAutorizado


# ==========================================
# FORMULÁRIO DE LOCAIS DO MAPA
# ==========================================
class LocalForm(forms.ModelForm):
    CATEGORIAS_CHOICES = [
        ('Saúde', '🟢 Saúde (Verde / Hospital)'),
        ('Esporte e Lazer', '🟠 Esporte e Lazer (Laranja / Running)'),
        ('Educação', '🟣 Educação (Roxo / Graduate)'),
        ('Religião', '🔵 Religião (Azul / Praying)'),
        ('Cultura', '🟡 Cultura (Amarelo / Landmark)'),
        ('Comércio', '🔴 Comércio (Vermelho / Shopping)'),
        ('Administrativo', '🩷 Administrativo (Rosa / Briefcase)'),
    ]

    categoria = forms.ChoiceField(
        choices=CATEGORIAS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Local
        fields = ['nome', 'distrito', 'categoria', 'lat', 'lon', 'status', 'foto', 'descricao']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: UBS São Rafael'}),
            'distrito': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Distrito I'}),
            'lat': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'Ex: -7.13567'}),
            'lon': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'Ex: -34.85519'}),
            'status': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Ativo / Crítico'}),
            'foto': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Link da foto (Google Drive ou URL)'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição completa do local...'}),
        }

    def clean_lat(self):
        lat = self.cleaned_data.get('lat')
        if lat is not None and abs(lat) > 90:
            # Tenta corrigir entrada sem ponto decimal
            str_lat = str(lat).replace('.', '').replace('-', '')
            val = float(f"-{str_lat[:1]}.{str_lat[1:]}") if lat < 0 else float(f"{str_lat[:1]}.{str_lat[1:]}")
            return val
        return lat

    def clean_lon(self):
        lon = self.cleaned_data.get('lon')
        if lon is not None and abs(lon) > 180:
            # Tenta corrigir entrada sem ponto decimal (ex: -348575 -> -34.8575)
            str_lon = str(lon).replace('.', '').replace('-', '')
            val = float(f"-{str_lon[:2]}.{str_lon[2:]}") if lon < 0 else float(f"{str_lon[:2]}.{str_lon[2:]}")
            return val
        return lon

    def save(self, commit=True):
        local = super().save(commit=False)
        
        # Mapeamento automático de Cor e Ícone por Categoria
        MAPA_ATRIBUTOS = {
            'Saúde': {'cor': 'green', 'icone': 'heart-pulse'},
            'Esporte e Lazer': {'cor': 'orange', 'icone': 'person-running'},
            'Educação': {'cor': 'purple', 'icone': 'user-graduate'},
            'Religião': {'cor': 'blue', 'icone': 'person-praying'},
            'Cultura': {'cor': 'beige', 'icone': 'landmark'},
            'Comércio': {'cor': 'red', 'icone': 'cart-shopping'},
            'Administrativo': {'cor': 'pink', 'icone': 'briefcase'},
        }

        attr = MAPA_ATRIBUTOS.get(local.categoria, {'cor': 'purple', 'icone': 'location-dot'})
        local.cor = attr['cor']
        local.icone = attr['icone']

        if commit:
            local.save()

            # Persistência síncrona no arquivo territorio_dados.json
            caminho_json = os.path.join(settings.DATA_DIR, 'territorio_dados.json')
            try:
                dados_existentes = []
                if os.path.exists(caminho_json):
                    with open(caminho_json, 'r', encoding='utf-8') as f:
                        dados_existentes = json.load(f)

                novo_item = {
                    "id": local.id,
                    "nome": local.nome,
                    "distrito": local.distrito or "Distrito I",
                    "categoria": local.categoria,
                    "lat": float(local.lat),
                    "lon": float(local.lon),
                    "foto": local.foto or "",
                    "descricao": local.descricao or "",
                    "status": local.status or "Ativo",
                    "cor": local.cor,
                    "icone": local.icone
                }

                # Atualiza ou insere no JSON
                dados_existentes = [item for item in dados_existentes if item.get('id') != local.id]
                dados_existentes.append(novo_item)

                with open(caminho_json, 'w', encoding='utf-8') as f:
                    json.dump(dados_existentes, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"Erro ao salvar em territorio_dados.json: {e}")

        return local


# ==========================================
# FORMULÁRIO DE ATIVIDADES / EVENTOS
# ==========================================
class AtividadeForm(forms.ModelForm):
    class Meta:
        model = Atividade
        fields = ['titulo', 'data', 'descricao', 'local', 'imagem']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título da Atividade/Evento'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'local': forms.Select(attrs={'class': 'form-select'}),
            'imagem': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


# ==========================================
# FORMULÁRIO DE ESCALAS DE TRABALHO
# ==========================================
class EscalaForm(forms.ModelForm):
    class Meta:
        model = EscalaTrabalho
        fields = ['integrante', 'local', 'dia_semana', 'turno', 'horario_inicio', 'horario_fim', 'observacoes']
        widgets = {
            'integrante': forms.Select(attrs={'class': 'form-select'}),
            'local': forms.Select(attrs={'class': 'form-select'}),
            'dia_semana': forms.Select(attrs={'class': 'form-select'}),
            'turno': forms.Select(attrs={'class': 'form-select'}),
            'horario_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'horario_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Informações adicionais...'}),
        }


# ==========================================
# FORMULÁRIO DE CADASTRO DE USUÁRIO
# ==========================================
class CadastroUsuarioForm(forms.ModelForm):
    cpf = forms.CharField(
        max_length=14, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'})
    )
    password = forms.CharField(
        label="Senha", 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Digite sua senha'})
    )
    password_confirm = forms.CharField(
        label="Confirme a Senha", 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repita a senha'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome de usuário para login'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primeiro Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sobrenome'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'seuemail@exemplo.com'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        cpf_digitado = cleaned_data.get('cpf', '').replace('.', '').replace('-', '').strip()
        email_digitado = cleaned_data.get('email', '').lower().strip()
        senha = cleaned_data.get('password')
        senha_confirm = cleaned_data.get('password_confirm')

        # 1. Validação das senhas
        if senha and senha_confirm and senha != senha_confirm:
            raise ValidationError("As senhas digitadas não coincidem.")

        # 2. Validação da White-list (CPF ou Email)
        autorizado = UsuarioAutorizado.objects.filter(ativo=True).filter(
            models.Q(email__iexact=email_digitado) | models.Q(cpf__icontains=cpf_digitado)
        ).first()

        if not autorizado:
            raise ValidationError(
                "Acesso negado! Este CPF/E-mail não consta na lista de membros autorizados do AfirmaSUS."
            )

        return cleaned_data


class AtaReuniaoForm(forms.ModelForm):
    class Meta:
        model = AtaReuniao
        fields = [
            'titulo',
            'data',
            'horario',
            'local',
            'coordenador',
            'responsavel',
            'conteudo',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex.: Planejamento da campanha de vacinação',
            }),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horario': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'local': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex.: UBS Centro ou Google Meet',
            }),
            'coordenador': forms.TextInput(attrs={'class': 'form-control'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'conteudo': forms.HiddenInput(),
        }

    def clean_conteudo(self):
        conteudo = self.cleaned_data['conteudo']
        if not isinstance(conteudo, dict):
            raise ValidationError("O conteúdo da ata deve ser um objeto válido.")

        participantes = conteudo.get('participantes')
        assuntos = conteudo.get('assuntos')
        decisoes = conteudo.get('decisoes')
        pendencias = conteudo.get('pendencias')
        encerramento = conteudo.get('encerramento')
        acoes = conteudo.get('acoes')

        if not isinstance(participantes, dict) or not isinstance(assuntos, dict):
            raise ValidationError("Revise os participantes e os assuntos da ata.")
        if not isinstance(decisoes, dict) or not isinstance(pendencias, dict):
            raise ValidationError("Revise as decisões e as pendências da ata.")
        if not isinstance(encerramento, dict) or not isinstance(acoes, list):
            raise ValidationError("Revise o encerramento e as ações da ata.")

        def texto(valor, campo, limite=10000):
            if not isinstance(valor, str):
                raise ValidationError(f"O campo {campo} deve ser texto.")
            valor = valor.strip()
            if len(valor) > limite:
                raise ValidationError(f"O campo {campo} excede o limite de {limite} caracteres.")
            return valor

        def lista_textos(valor, campo, limite=100):
            if not isinstance(valor, list) or len(valor) > limite:
                raise ValidationError(f"A lista {campo} é inválida ou excede {limite} itens.")
            return [texto(item, campo, 5000) for item in valor]

        participantes['presentes'] = lista_textos(
            participantes.get('presentes'), 'presentes'
        )
        participantes['ausentes'] = lista_textos(
            participantes.get('ausentes'), 'ausentes'
        )

        itens_assuntos = assuntos.get('itens')
        if not isinstance(itens_assuntos, list) or len(itens_assuntos) > 100:
            raise ValidationError("A lista de assuntos é inválida ou excede 100 itens.")
        assuntos['itens'] = [
            {
                'id': texto(item.get('id', ''), 'identificador do assunto', 64),
                'titulo': texto(item.get('titulo', ''), 'título do assunto', 500),
                'discussao': texto(item.get('discussao', ''), 'discussão', 10000),
            }
            for item in itens_assuntos
            if isinstance(item, dict)
        ]
        if len(assuntos['itens']) != len(itens_assuntos):
            raise ValidationError("Um dos assuntos enviados é inválido.")
        assuntos['observacoes'] = texto(
            assuntos.get('observacoes', ''), 'observações'
        )

        decisoes['itens'] = lista_textos(decisoes.get('itens'), 'decisões')
        decisoes['justificativas'] = texto(
            decisoes.get('justificativas', ''), 'justificativas'
        )

        pendencias['itens'] = lista_textos(pendencias.get('itens'), 'pendências')
        pendencias['proximos_passos'] = texto(
            pendencias.get('proximos_passos', ''), 'próximos passos'
        )

        encerramento['horario_termino'] = texto(
            encerramento.get('horario_termino', ''), 'horário de término', 5
        )
        encerramento['proxima_reuniao'] = texto(
            encerramento.get('proxima_reuniao', ''), 'data da próxima reunião', 10
        )
        if encerramento['horario_termino']:
            try:
                time.fromisoformat(encerramento['horario_termino'])
            except ValueError as erro:
                raise ValidationError("Informe um horário de término válido.") from erro
        if encerramento['proxima_reuniao']:
            try:
                date.fromisoformat(encerramento['proxima_reuniao'])
            except ValueError as erro:
                raise ValidationError("Informe uma data válida para a próxima reunião.") from erro

        acoes_limpas = []
        identificadores = set()
        for acao in acoes:
            if not isinstance(acao, dict):
                raise ValidationError("Uma das ações da ata é inválida.")
            identificador = texto(acao.get('id', ''), 'identificador da ação', 64)
            if not identificador or identificador in identificadores:
                raise ValidationError("Os identificadores das ações devem ser únicos.")
            identificadores.add(identificador)

            status = acao.get('status', 'Pendente')
            if status not in ('Pendente', 'Em andamento', 'Concluída'):
                raise ValidationError("O status de uma ação é inválido.")

            prazo = texto(acao.get('prazo', ''), 'prazo da ação', 10)
            lembrete = acao.get('lembrete')
            if not isinstance(lembrete, dict):
                raise ValidationError("Os dados do lembrete de uma ação são inválidos.")
            lembrete_data = texto(lembrete.get('data', ''), 'data do lembrete', 10)
            lembrete_hora = texto(lembrete.get('hora', ''), 'hora do lembrete', 5)
            for valor, campo, parser in (
                (prazo, 'prazo da ação', 'date'),
                (lembrete_data, 'data do lembrete', 'date'),
                (lembrete_hora, 'hora do lembrete', 'time'),
            ):
                if valor:
                    try:
                        (date if parser == 'date' else time).fromisoformat(valor)
                    except ValueError as erro:
                        raise ValidationError(f"Informe um {campo} válido.") from erro

            acoes_limpas.append({
                'id': identificador,
                'tarefa': texto(acao.get('tarefa', ''), 'tarefa', 5000),
                'responsavel': texto(acao.get('responsavel', ''), 'responsável', 150),
                'prazo': prazo,
                'status': status,
                'lembrete': {'data': lembrete_data, 'hora': lembrete_hora},
            })
        conteudo['acoes'] = acoes_limpas
        conteudo['anotacoes'] = texto(conteudo.get('anotacoes', ''), 'anotações')
        horario_automatico = conteudo.get('horario_automatico', True)
        if not isinstance(horario_automatico, bool):
            raise ValidationError("A preferência de horário automático é inválida.")
        conteudo['horario_automatico'] = horario_automatico
        return conteudo


class AtaReuniaoFormExportacao(forms.Form):
    atas = forms.MultipleChoiceField(required=True)
    formatos = forms.MultipleChoiceField(
        required=True,
        choices=(('pdf', 'PDF'), ('docx', 'Word (.docx)'), ('xlsx', 'Excel (.xlsx)')),
    )
    modo = forms.ChoiceField(
        required=True,
        choices=(('separado', 'Um arquivo por ata'), ('juntos', 'Reunir atas por formato')),
    )

    def __init__(self, *args, atas, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['atas'].choices = [
            (str(ata.pk), ata.titulo.strip() or f'Ata {ata.pk}')
            for ata in atas
        ]

    def clean_atas(self):
        atas = self.cleaned_data['atas']
        if len(atas) > 100:
            raise ValidationError("Exporte no máximo 100 atas por vez.")
        return atas