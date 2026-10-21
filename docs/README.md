# Hospedagem do AfirmaSUS2

Aplicação publicada em https://kennyow.pythonanywhere.com/.
Login e navegação foram confirmados pelo usuário. O teste de gravação após
Reload e a configuração de backup externo ainda estão pendentes.

Os guias nesta pasta registram o trabalho feito no workspace, onde este
repositório fica dentro da pasta `AfirmaSUS2/afirmasus_django`. Neles, os
comandos partem da pasta pai `AfirmaSUS2`, salvo indicação em contrário.
Em um clone apenas deste repositório, `manage.py`, `requirements.txt` e
`serve.py` ficam diretamente na raiz; ajuste os caminhos dos comandos.

Na conta PythonAnywhere:

- Código: `/home/kennyow/AfirmaSUS2/afirmasus_django`.
- Virtualenv: `/home/kennyow/.virtualenvs/afirmasus` (Python 3.13).
- Dados: `/home/kennyow/afirmasus-dados`.
- Configuração privada: `/home/kennyow/.afirmasus-config.json`.
- O WSGI do painel carrega o JSON privado no ambiente antes de iniciar Django.
- `/static/` aponta para `staticfiles` no código.
- `/media/` aponta para `media` no diretório de dados.

A chave privada, ambientes virtuais, arquivos coletados e pacotes de envio
não fazem parte desta documentação nem do commit de implantação.
