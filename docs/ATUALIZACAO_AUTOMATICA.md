# GitHub → PythonAnywhere

Preparado para `kennyow/AfirmaSUS2`, branch `main`, site
`https://kennyow.pythonanywhere.com/`. Só funciona depois de publicar estes
arquivos no GitHub e configurar o secret e a variável abaixo.

## Ativação

1. PythonAnywhere → Account → API token: gere ou copie o token.
2. GitHub → repositório `kennyow/AfirmaSUS2` → Settings → Secrets and variables
   → Actions → Secrets → New repository secret:
   nome `PA_API_TOKEN`, valor igual ao token. Não coloque esse valor no código,
   em commits ou no chat. O token concede acesso à conta PythonAnywhere.
3. Confira na aba Web do PythonAnywhere:
   - Virtualenv: `/home/kennyow/.virtualenvs/afirmasus` (Python 3.13).
   - Código: `/home/kennyow/AfirmaSUS2/afirmasus_django`.
   - `/static/`: `/home/kennyow/AfirmaSUS2/afirmasus_django/staticfiles`.
   - WSGI carrega `/home/kennyow/.afirmasus-config.json` e define
     `DJANGO_DATA_DIR=/home/kennyow/afirmasus-dados` antes de iniciar Django.
4. Confira que `requirements.txt` do servidor e do GitHub são iguais e que
   as dependências já estão instaladas no virtualenv.
5. Na mesma página Actions do GitHub, aba Variables, crie a repository variable
   `PA_DEPLOY_ENABLED` com valor `true`.
6. Abra Actions → Publicar no PythonAnywhere → Run workflow → main.
   Aguarde o resultado e confira login, navegação e arquivos estáticos no site.

Depois disso, cada push para `main` inicia a publicação. A primeira execução
pode demorar vários minutos: a API limita chamadas e o script respeita esse limite.
O workflow não depende de SSH nem de uma console permanentemente aberta.

## O que é publicado

Código Python de `core` e `setup`, templates, estáticos originais, `manage.py`,
`serve.py` e arquivos gerados por `collectstatic`. Somente fontes rastreadas
pelo Git são consideradas. A coleta ocorre no runner, com uma chave temporária
de build que não é enviada como configuração ao servidor.

SQLite, JSON de dados, uploads, ambientes virtuais e configuração privada não
são enviados. Alterar `linhadotempodinamica.json` localmente, por exemplo,
não altera o conteúdo do site. Dados do site devem ser editados pela aplicação
ou transferidos separadamente, com backup e escolha explícita da fonte correta.

## Limites e recuperação

- Mudanças em dependências interrompem a publicação até instalar e sincronizar
  `requirements.txt` manualmente no servidor.
- Migrações novas/alteradas interrompem a publicação antes do primeiro upload.
  Faça backup e aplique a atualização do banco em uma manutenção planejada.
- Remoção/renomeação de fontes após a primeira publicação também exige manutenção
  manual para evitar módulos antigos. O manifesto remoto é
  `.github-deploy-manifest.txt`; só o ajuste após limpar os arquivos correspondentes.
- O envio é arquivo por arquivo, não uma troca atômica. Publique em horário de
  menor uso. Em falha tratada, o script tenta restaurar os arquivos anteriores;
  interrupção forçada do runner ou indisponibilidade da API pode exigir restauração
  manual. Mantenha backup do código e dos dados antes da primeira execução.
- Reload aceito pela API não comprova que a aplicação iniciou corretamente.
  Confira o site e os logs da aba Web após a publicação.
- Para desativar, remova `PA_DEPLOY_ENABLED` ou mude seu valor para `false`.

API oficial: https://help.pythonanywhere.com/pages/API/
