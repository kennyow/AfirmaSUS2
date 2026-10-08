from django.urls import path
from . import views
from core.views import main_views

urlpatterns = [
    # Navegação Principal
    path('', views.home, name='home'),
    path('mapa/', views.mapa_territorio, name='pagina_mapa'),
    path('escala/', views.pagina_escala, name='pagina_escala'),

    # Autenticação e Usuários
    path('login/', views.fazer_login, name='login'),
    path('logout/', views.fazer_logout, name='logout'),
    path('cadastrar/', views.cadastrar_usuario, name='cadastrar_usuario'),

    # Gestão de Conteúdo
    path('local/novo/', main_views.cadastrar_local, name='cadastrar_local'),
    path('local/<int:local_id>/editar/', main_views.editar_local, name='editar_local'),
    path('local/deletar/<int:local_id>/', main_views.deletar_local, name='deletar_local'),
    path('atividade/nova/', views.cadastrar_atividade, name='cadastrar_atividade'),
    path('escala/nova/', views.cadastrar_escala, name='cadastrar_escala'),
    path('escala/deletar/<int:escala_id>/', views.deletar_escala, name='deletar_escala'),
    path('escala/notas/adicionar/', views.adicionar_nota_calendario, name='adicionar_nota_calendario'),
    path('escala/notas/<str:note_id>/deletar/', views.deletar_nota_calendario, name='deletar_nota_calendario'),
    path('escala/notas/<str:note_id>/editar/', views.editar_nota_calendario, name='editar_nota_calendario'),

    # Mídias e Formações
    path('formacoes/', views.formacoes, name='formacoes'),
    path('midias/', views.midias, name='midias'),
    path('midias/adicionar/<str:tipo>/', views.adicionar_midia, name='adicionar_midia'),
    path('midias/remover/<str:tipo>/<int:index>/', views.remover_midia, name='remover_midia'),

    # Levantamento Estatístico
    path('levantamento-estatistico/', main_views.levantamento_estatistico, name='levantamento_estatistico'),
    path('levantamento-estatistico/atualizar/', main_views.atualizar_indicadores, name='atualizar_indicadores'),

    path('minha-nova-aba/', main_views.nova_aba_view, name='nome_da_sua_aba'),
]