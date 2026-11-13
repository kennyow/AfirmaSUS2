from django.urls import include, path
from core.views.midias import publicar_formacao
from core.urls import urlpatterns as original_patterns

# Keep named routes for template compatibility; middleware blocks every mutation,
# including legacy views that used GET for deletion. Authentication stays shared.
urlpatterns = [path('formacoes/publicar/', publicar_formacao, name='publicar_formacao'), path('', include([
    route for route in original_patterns
    if route.name not in {'login', 'logout', 'cadastrar_usuario'}
]))]
