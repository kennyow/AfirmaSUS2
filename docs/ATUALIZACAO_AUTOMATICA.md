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

## Sincronização inicial

Se o log indicar que requirements.txt está ausente ou diferente, isso não
comprova que os pacotes estão faltando: a checagem compara a lista de requisitos,
não consegue consultar os pacotes instalados pela API de arquivos.
Diferenças de ordem, comentários, linhas vazias, BOM e CRLF são ignoradas.

1. Baixe o requirements.txt atual do repositório no GitHub (ou use o arquivo local
   deste repositório) e envie pela aba Files para `/home/kennyow/requirements-github.txt`.
   Use esse nome temporário para só atualizar a lista oficial após instalar com sucesso.
2. Abra Consoles → Bash no PythonAnywhere e execute:

```bash
/home/kennyow/.virtualenvs/afirmasus/bin/python -m pip install -r /home/kennyow/requirements-github.txt && /home/kennyow/.virtualenvs/afirmasus/bin/python -m pip check && cp /home/kennyow/requirements-github.txt /home/kennyow/AfirmaSUS2/afirmasus_django/requirements.txt
```

3. Só prossiga se terminar sem erros. No GitHub, execute **Run workflow** em
   **Publicar no PythonAnywhere** na branch main para usar o workflow corrigido.
   Reexecutar uma execução antiga usa o código antigo.

Essa etapa não altera banco, JSON, uploads nem executa migrações. Uma falha no pip
pode deixar uma atualização parcial dos pacotes; copie o erro antes de continuar.
Após instalar, a publicação automática fará o Reload. A API de arquivos não
permite executar pip no servidor; por isso esta etapa exige a console do usuário.

## O que é publicado

Código Python de `core` e `setup`, templates, estáticos originais, `manage.py`,
`serve.py` e arquivos gerados por `collectstatic`. Somente fontes rastreadas
pelo Git são consideradas. A coleta ocorre no runner, com uma chave temporária
de build que não é enviada como configuração ao servidor.

Os JSON rastreados pelo Git na raiz do repositório são publicados em
`/home/kennyow/afirmasus-dados`, incluindo `linhadotempodinamica.json`,
`timeline.json` e os demais arquivos de conteúdo. O GitHub é a fonte desses dados:
em cada publicação seus arquivos substituem as versões do site. Alterações feitas
pelo site não voltam automaticamente ao GitHub e podem ser substituídas no próximo push.

Edite os arquivos em `AfirmaSUS2/afirmasus_django`, faça commit e push para main.
A pasta vizinha `AfirmaSUS` não pertence a este repositório e não é publicada.
Salvar no VS Code sem commit/push também não publica.

Antes do envio, todos os JSON são validados. Cada JSON substituído ganha uma cópia
verificada em `/home/kennyow/afirmasus-deploy-backups/<execução>/<arquivo>.json`.
O caminho aparece no log; os backups não ficam em pasta pública. O conteúdo
publicado também é relido para confirmar o envio. Os backups ocupam espaço e
devem ser arquivados/removidos periodicamente após conferir o site.

SQLite, uploads, ambientes virtuais e configuração privada não são enviados.
Dados armazenados no SQLite e mudanças de esquema precisam de procedimentos
próprios; o deploy não substitui banco nem executa migrações automaticamente.

## Limites e recuperação

- Mudanças em dependências interrompem a publicação até instalar e sincronizar
  `requirements.txt` manualmente no servidor.
- Migrações novas/alteradas interrompem a publicação antes do primeiro upload.
  Faça backup e aplique a atualização do banco em uma manutenção planejada.
- Remoção/renomeação de JSON não bloqueia a publicação: os arquivos antigos ficam
  preservados no servidor e deixam de integrar o manifesto; o código usa os nomes
  atuais. O deploy não exclui esses dados antigos automaticamente.
- Remoção/renomeação de fontes após a primeira publicação também exige manutenção
  manual para evitar módulos antigos. O manifesto remoto é
  `.github-deploy-manifest.txt`; só o ajuste após limpar os arquivos correspondentes.
- O envio é arquivo por arquivo, não uma troca atômica. Publique em horário de
  menor uso. Em falha tratada, o script tenta restaurar os arquivos anteriores;
  interrupção forçada do runner ou indisponibilidade da API pode exigir restauração
  manual. Mantenha backup do código e dos dados antes da primeira execução.
- Evite edições pelo site durante a publicação dos JSON. O script detecta mudanças
  entre a leitura inicial e o backup, mas a API não oferece trava de gravação;
  uma edição simultânea ao envio ainda pode ser substituída.
- Reload aceito pela API não comprova que a aplicação iniciou corretamente.
  Confira o site e os logs da aba Web após a publicação.
- Para desativar, remova `PA_DEPLOY_ENABLED` ou mude seu valor para `false`.

API oficial: https://help.pythonanywhere.com/pages/API/
