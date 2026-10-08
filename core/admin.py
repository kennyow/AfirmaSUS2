from django.contrib import admin
from .models import Local, Atividade, Integrante, EscalaTrabalho, UsuarioAutorizado

@admin.register(UsuarioAutorizado)
class UsuarioAutorizadoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'cpf', 'ativo')
    search_fields = ('nome', 'email', 'cpf')
    list_filter = ('ativo',)

admin.site.register(Local)
admin.site.register(Atividade)
admin.site.register(Integrante)
admin.site.register(EscalaTrabalho)