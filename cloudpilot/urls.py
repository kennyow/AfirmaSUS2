from django.urls import path

from . import views
from .galeria import galeria

app_name = 'pilot'
urlpatterns = [
    path('', views.catalogo, name='catalogo'),
    path('arquivos/enviar/', views.enviar, name='enviar'),
    path('arquivos/<int:pk>/baixar/', views.baixar, name='baixar'),
    path('midias/galeria/', galeria, name='galeria'),
    path('health/', views.health, name='health'),
]
