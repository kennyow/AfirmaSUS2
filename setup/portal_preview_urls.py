from django.urls import include, path
from core.views.midias import excluir_formacao, publicar_formacao
from core.urls import urlpatterns as original_patterns

# Keep named routes for template compatibility; middleware blocks every mutation,
# including legacy views that used GET for deletion. Authentication stays shared.
from django.urls import register_converter


class FormationId:
    regex = r'-?[0-9]+'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return str(value)


register_converter(FormationId, 'formation_id')

urlpatterns = [
    path('formacoes/publicar/', publicar_formacao, name='publicar_formacao'),
    path('formacoes/<formation_id:pk>/editar/', publicar_formacao, name='editar_formacao'),
    path('formacoes/<formation_id:pk>/excluir/', excluir_formacao, name='excluir_formacao'),
    path('', include([
    route for route in original_patterns
    if route.name not in {'login', 'logout', 'cadastrar_usuario'}
]))]
