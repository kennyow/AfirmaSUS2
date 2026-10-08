# core/forms.py

import os
import json
from django import forms
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Local, Atividade, EscalaTrabalho, UsuarioAutorizado


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

            # Persistência síncrona no arquivo dados_locais.json
            caminho_json = os.path.join(settings.BASE_DIR, 'dados_locais.json')
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
                print(f"Erro ao salvar em dados_locais.json: {e}")

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