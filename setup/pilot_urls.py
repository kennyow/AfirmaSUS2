from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from core.views.main_views import home

from cloudpilot.materiais import abrir_material, adicionar_material, remover_material

urlpatterns = [
    path('materiais/adicionar/', adicionar_material, name='adicionar_material'),
    path('materiais/<str:key>/remover/', remover_material, name='remover_material'),
    path('materiais/<str:key>/visualizar/', abrir_material, name='visualizar_material'),
    path('materiais/<str:key>/baixar/', abrir_material, {'download': True}, name='baixar_material'),
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(template_name='cloudpilot/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('plataforma/', include('setup.portal_preview_urls')),
    path('', include('cloudpilot.urls')),
    path('', home, name='home'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
