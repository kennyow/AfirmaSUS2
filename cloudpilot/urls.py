from django.urls import path

from . import views
from .galeria import album, change_album, create_album, galeria

app_name = 'pilot'
urlpatterns = [
    path('arquivos/', views.catalogo, name='catalogo'),
    path('arquivos/enviar/', views.enviar, name='enviar'),
    path('arquivos/<int:pk>/baixar/', views.baixar, name='baixar'),
    path('midias/galeria/', galeria, name='galeria'),
    path('midias/galeria/adicionar/', create_album, name='create_album'),
    path('midias/galeria/<int:index>/', album, name='album'),
    path('midias/galeria/<int:index>/alterar/', change_album, name='change_album'),
    path('health/', views.health, name='health'),
]
