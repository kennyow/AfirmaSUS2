from django.contrib import admin

from .models import ArquivoPublico


@admin.register(ArquivoPublico)
class ArquivoPublicoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'tamanho', 'enviado_por', 'enviado_em')
    readonly_fields = ('titulo', 'arquivo', 'nome_original', 'tipo', 'tamanho', 'enviado_por', 'enviado_em')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Deletion requires a deliberate object + database reconciliation flow.
        return False
