# core/views/__init__.py

from .utils import converter_link_drive
from .auth_views import fazer_login, fazer_logout, cadastrar_usuario
from .midias import formacoes, midias, adicionar_midia, remover_midia
from .main_views import home, mapa_territorio, equipe_informacoes
from .atas import (
    lista_atas,
    nova_ata,
    editar_ata,
    excluir_ata,
    alterar_fila_ata,
    fila_atas,
    lembretes_atas,
    concluir_acao_ata,
    exportar_atas,
)
from .management_views import (
    cadastrar_local,
    cadastrar_atividade,
    deletar_local,
    pagina_escala,
    cadastrar_escala,
    deletar_escala,
    adicionar_nota_calendario,
    deletar_nota_calendario,
    editar_nota_calendario,
)