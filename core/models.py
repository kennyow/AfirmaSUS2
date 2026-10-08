from django.db import models
from django.contrib.auth.models import User

# ---------------------------------------------------------
# 1. MODELO DE LOCAIS (MAPA INTERATIVO)
# ---------------------------------------------------------
class Local(models.Model):
    nome = models.CharField(max_length=150)
    distrito = models.CharField(max_length=100, blank=True, null=True)
    categoria = models.CharField(max_length=100, default='Saúde')
    lat = models.FloatField()
    lon = models.FloatField()
    status = models.CharField(max_length=50, blank=True, null=True)
    cor = models.CharField(max_length=30, default='purple')
    icone = models.CharField(max_length=30, default='hospital')
    foto = models.CharField(max_length=500, blank=True, null=True)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome


# ---------------------------------------------------------
# 2. MODELO DE ATIVIDADES E EVENTOS (CALENDÁRIO / LINHA DO TEMPO)
# ---------------------------------------------------------
class Atividade(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="Título do Evento")
    data = models.DateField(verbose_name="Data da Atividade")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    local = models.ForeignKey(Local, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Local Relacionado")
    
    # Campo para upload direto de imagem pelo usuário
    imagem = models.ImageField(upload_to='eventos/', blank=True, null=True, verbose_name="Foto/Evidência do Evento")

    def __str__(self):
        return f"{self.titulo} - {self.data}"


# ---------------------------------------------------------
# 3. MODELO DE INTEGRANTES DO PROJETO
# ---------------------------------------------------------
class Integrante(models.Model):
    nome = models.CharField(max_length=150)
    curso = models.CharField(max_length=100, blank=True, null=True)
    situacao = models.CharField(max_length=50, blank=True, null=True)
    foto = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.nome

    @property
    def foto_url_direta(self):
        """Extrai o ID do Google Drive e redireciona para o CDN de imagens lh3.googleusercontent.com"""
        if not self.foto:
            return ''

        if 'drive.google.com' in self.foto or 'googleusercontent.com' in self.foto:
            file_id = None
            if '/d/' in self.foto:
                file_id = self.foto.split('/d/')[1].split('/')[0]
            elif 'id=' in self.foto:
                file_id = self.foto.split('id=')[1].split('&')[0]
            
            if file_id:
                # Servidor estático direto de mídia da Google (sem bloqueios CORS/hotlink)
                return f"https://lh3.googleusercontent.com/d/{file_id}"
                
        return self.foto


# ---------------------------------------------------------
# 4. MODELO DE ESCALA DE TRABALHO
# ---------------------------------------------------------

class EscalaTrabalho(models.Model):
    DIAS_SEMANA = [
        ('Segunda-feira', 'Segunda-feira'),
        ('Terça-feira', 'Terça-feira'),
        ('Quarta-feira', 'Quarta-feira'),
        ('Quinta-feira', 'Quinta-feira'),
        ('Sexta-feira', 'Sexta-feira'),
        ('Sábado', 'Sábado'),
        ('Domingo', 'Domingo'),
    ]

    TURNOS = [
        ('Manhã', 'Manhã'),
        ('Tarde', 'Tarde'),
        ('Noite', 'Noite'),
        ('Integral', 'Integral'),
    ]

    integrante = models.ForeignKey(
        Integrante, 
        on_delete=models.CASCADE, 
        related_name='escalas', 
        verbose_name="Integrante",
        null=True, 
        blank=True
    )
    local = models.ForeignKey(
        Local, 
        on_delete=models.CASCADE, 
        related_name='escalas', 
        verbose_name="Local de Atuação",
        null=True, 
        blank=True
    )
    dia_semana = models.CharField(
        max_length=20, 
        choices=DIAS_SEMANA, 
        default='Segunda-feira',
        verbose_name="Dia da Semana",
        null=True, 
        blank=True
    )
    turno = models.CharField(max_length=20, choices=TURNOS, default='Manhã', verbose_name="Turno")
    horario_inicio = models.TimeField(null=True, blank=True, verbose_name="Horário de Início")
    horario_fim = models.TimeField(null=True, blank=True, verbose_name="Horário de Término")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Escala de Trabalho"
        verbose_name_plural = "Escalas de Trabalho"
        ordering = ['dia_semana', 'horario_inicio']

    def __str__(self):
        nome_integrante = self.integrante.nome if self.integrante else "Sem Integrante"
        nome_local = self.local.nome if self.local else "Sem Local"
        return f"{nome_integrante} - {nome_local} ({self.dia_semana})"


class UsuarioAutorizado(models.Model):
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF (Apenas números ou formatado)")
    email = models.EmailField(unique=True, verbose_name="E-mail Autorizado")
    nome = models.CharField(max_length=150, verbose_name="Nome Completo")
    ativo = models.BooleanField(default=True, verbose_name="Autorização Ativa")

    class Meta:
        verbose_name = "Usuário Autorizado"
        verbose_name_plural = "Usuários Autorizados (White-list)"

    def __str__(self):
        return f"{self.nome} ({self.cpf})"



class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    data_nascimento = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento")
    avatar = models.ImageField(upload_to='avatares/', null=True, blank=True, verbose_name="Foto de Perfil / Avatar")

    def __str__(self):
        return f"Perfil de {self.user.get_full_name() or self.user.username}"

    @property
    def avatar_url(self):
        """Retorna a URL da foto de perfil ou um avatar com a inicial do nome"""
        if self.avatar:
            return self.avatar.url
        return None