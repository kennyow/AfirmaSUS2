# core/views/__init__.py

from .utils import converter_link_drive
from .auth_views import fazer_login, fazer_logout, cadastrar_usuario
from .midias import midias, adicionar_midia, remover_midia
from .main_views import home, mapa_territorio
from .management_views import (
    cadastrar_local,
    cadastrar_atividade,
    deletar_local,
    pagina_escala,
    cadastrar_escala,
)