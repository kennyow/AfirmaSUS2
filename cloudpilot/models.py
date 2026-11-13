from pathlib import PurePosixPath
from uuid import uuid4

from django.conf import settings
from django.db import models


def upload_path(instance, filename):
    extension = PurePosixPath(filename).suffix.lower()
    return f'publicos/{uuid4().hex}{extension}'


class ArquivoPublico(models.Model):
    titulo = models.CharField(max_length=200)
    arquivo = models.FileField(upload_to=upload_path, max_length=200)
    nome_original = models.CharField(max_length=255)
    tamanho = models.PositiveIntegerField()
    tipo = models.CharField(max_length=100)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enviado_em', '-pk']
        verbose_name = 'arquivo público'
        verbose_name_plural = 'arquivos públicos'

    @property
    def imagem(self):
        return self.tipo in {'image/jpeg', 'image/png', 'image/webp'}

    def __str__(self):
        return self.titulo


class FotoPerfil(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.CASCADE, related_name="foto_perfil")
    arquivo = models.CharField(max_length=200)

    @property
    def url(self):
        from django.core.files.storage import default_storage
        return default_storage.url(self.arquivo)
