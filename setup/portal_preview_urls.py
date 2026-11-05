from django.urls import include, path
from core.urls import urlpatterns as original_patterns

# Keep named routes for template compatibility; middleware blocks every mutation,
# including legacy views that used GET for deletion. Authentication stays shared.
urlpatterns = [path('', include([
    route for route in original_patterns
    if route.name not in {'login', 'logout', 'cadastrar_usuario'}
]))]
