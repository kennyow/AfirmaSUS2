# AfirmaSUS2 — caminho até o domínio

## Etapa 1: diagnóstico

Inspeção realizada em 20/10/2026. O projeto já é uma aplicação web Django.
A raiz da aplicação é `afirmasus_django/`, onde está `manage.py`.
O projeto `AfirmaSUS/` é separado e não foi alterado.

Recursos encontrados: página inicial, mapa, equipe, escalas, atas, mídias,
indicadores, autenticação e administração.

### Resultado da verificação

- Há banco SQLite em `afirmasus_django/db.sqlite3`.
- Há conteúdo em JSON, com gravações feitas pelas views e formulários.
- Há arquivos estáticos e configuração de uploads em `media/`.
- Não foi encontrado manifesto de dependências dentro de AfirmaSUS2.
- O Python do `venv` compartilhado não tem Django instalado. Não foi possível
  executar os checks ou testes da aplicação.
- A versão de Django citada no cabeçalho de settings.py não confirma a versão
  realmente usada. A versão deverá ser definida e validada no ambiente dedicado.

### Pendências antes da publicação

- Criar ambiente Python dedicado e registrar dependências: Django, pandas,
  folium, plotly e o mecanismo de leitura de Excel utilizado na importação.
- Executar `manage.py check` e os testes existentes.
- Carregar a chave secreta de produção pelo ambiente e usar uma chave nova.
- Desativar DEBUG em produção e configurar ALLOWED_HOSTS e origens CSRF.
- Definir STATIC_ROOT, coletar estáticos e configurar sua entrega.
- Configurar servidor WSGI/ASGI de produção, HTTPS e entrega de uploads.
- Definir armazenamento persistente e backup para banco, JSON e uploads.
  Um serviço com disco temporário perderia alterações feitas nesses arquivos.
- Verificar permissões das operações de edição e testar login em produção.

## Próximas etapas, uma por vez

### Atualização: pesquisa de hospedagem

- Comparação de Render e PythonAnywhere registrada em `ESCOLHA_HOSPEDAGEM.md`.
- A seleção aguarda orçamento e informação sobre domínio já registrado.
- Nenhum serviço foi contratado ou criado. A configuração de implantação
  será preparada para o provedor selecionado.

### Atualização: caminhos persistentes e cópia dos dados preparados

- `DJANGO_DATA_DIR` controla os caminhos do SQLite, JSON e uploads.
  Sem configuração, os dados locais continuam nos caminhos anteriores.
- Atualizadas views, formulário e importação de JSON para usar o diretório.
- Criado `manage.py copiar_dados DESTINO_ABSOLUTO`, que copia para uma pasta
  nova, verifica a integridade SQLite e preserva JSON e uploads.
- Documentados migração inicial, backup e restauração em `AMBIENTE_LOCAL.md`.
- Teste com dados temporários verificou cópia, recusa de sobrescrita e
  reabertura por outro processo. Corrigido fechamento das conexões no Windows.
- Validação: os 43 testes passaram (32 de core e 11 de configuração,
  estáticos, servidor e persistência; o teste corrigido foi repetido isoladamente).
- Os dados reais não foram migrados. Ainda será necessário montar o volume,
  transferir os dados, configurar backup externo e servir uploads na hospedagem.
- Próxima pendência: escolher a hospedagem compatível com Python/Django e
  disco persistente, considerando orçamento e domínio disponível.

### Atualização: servidor de aplicação preparado

- Instalado Waitress 3.0.2 e registrado em requirements.txt.
- Criado `afirmasus_django/serve.py`, com DEBUG falso por padrão e recusa
  explícita de DEBUG true; host e porta configuráveis por HOST e PORT.
- Configurado um processo com uma thread para evitar concorrência interna
  nas gravações JSON. A implantação deverá manter uma única instância.
- Teste HTTP real em localhost confirmou login com status 200, logo PNG
  com status 200 e rejeição de Host desconhecido com status 400.
- Servidor temporário encerrado após o teste; nenhum formulário foi enviado.
- Passaram 42 testes (32 de core e dez de configuração/estáticos/servidor).
  Django sem problemas de sistema e pip sem dependências quebradas.
- Instruções em `AMBIENTE_LOCAL.md`. Não houve publicação nesta etapa.
- Próxima pendência: preparar armazenamento persistente para SQLite, JSON
  e uploads, antes de escolher e configurar a hospedagem.

Referência do servidor: https://docs.pylonsproject.org/projects/waitress/en/stable/runner.html

### Atualização: coleta e entrega de arquivos estáticos

- Configurado STATIC_ROOT em `afirmasus_django/staticfiles/`, ignorado no Git.
- Instalado WhiteNoise 6.12.0 e registrado em requirements.txt.
- Em produção, configurado armazenamento com manifesto, nomes versionados
  e compressão; uploads continuam usando seu armazenamento próprio.
- Coleta real concluída: 130 arquivos copiados, 388 operações de pós-processamento.
- Teste de integração confirmou respostas HTTP 200, tipos de conteúdo e cache
  para logo, CSS, JavaScript e CSS do administrador com DEBUG falso.
- Passaram nove testes de configuração/estáticos e 32 testes de core.
  A verificação do Django não identificou problemas. Na primeira execução,
  WhiteNoise avisou que a pasta de saída ainda não existia; a coleta a criou.
- Comando para repetir a coleta em cada implantação em `AMBIENTE_LOCAL.md`.
- Próxima pendência: preparar o servidor de aplicação de produção.

Referência de configuração: https://whitenoise.readthedocs.io/en/stable/django.html

### Atualização: domínios e origens CSRF por ambiente

- `DJANGO_ALLOWED_HOSTS` define a lista de hosts separados por vírgula.
  Em produção, lista ausente ou curinga `*` impedem a inicialização.
- Em desenvolvimento, os hosts locais são aceitos por padrão.
- `DJANGO_CSRF_TRUSTED_ORIGINS` define origens extras opcionais com protocolo.
- Instruções e exemplos em `AMBIENTE_LOCAL.md`. O domínio real ainda será definido.
- Validação: oito testes de configuração e 32 testes de core passaram;
  nenhuma ocorrência na verificação de sistema do Django.
- Próxima pendência: configurar coleta e entrega dos arquivos estáticos.

### Atualização: chave secreta por ambiente

- Removida a chave antiga do código; `DJANGO_SECRET_KEY` fornece a chave.
- Desenvolvimento mantém uma chave local explícita e DEBUG ligado por padrão.
- Na hospedagem será obrigatório configurar `DJANGO_DEBUG=false` e uma chave
  aleatória própria. Com DEBUG falso, chave ausente, curta ou com prefixo de
  desenvolvimento impede a inicialização.
- Validação: 32 testes de core e quatro testes de configuração passaram.
- Instruções de configuração em `AMBIENTE_LOCAL.md`; nenhum segredo de
  produção foi gerado ou salvo no repositório.
- Próxima pendência: configurar domínios permitidos e origens CSRF por ambiente.

### Atualização: ambiente exclusivo preparado

- Criado `AfirmaSUS2/.venv` com Python 3.14.4.
- Instalado Django 5.2.18 e as dependências diretas listadas em `requirements.in`.
- Registradas as versões instaladas em `requirements.txt`.
- `pip check`: nenhuma dependência quebrada.
- `manage.py check`: nenhum erro; sete avisos W042 sobre o tipo padrão das
  chaves primárias. A correção deve considerar os tipos já usados nas migrações.
- Não foram executadas migrações, importações ou alterações nos dados existentes.
- Testes funcionais ainda pendentes. Próxima pendência: validar a aplicação
  com os testes existentes e tratar os resultados encontrados.
- Instruções de uso em `AMBIENTE_LOCAL.md`.

O diagnóstico inicial acima descreve o estado anterior à preparação do ambiente.

### Atualização: testes e consistência dos modelos validados

- Executados os 32 testes existentes de `core`: todos passaram após as correções.
- Restaurada a cor padrão roxa nas notas do calendário, preservando cores
  explicitamente definidas nos eventos.
- Corrigido o escape do `&` no título HTML de formações.
- Configurado `BigAutoField` no aplicativo, conforme as migrações existentes,
  eliminando os sete avisos W042.
- Verificação de sistema: nenhum problema identificado.
- `makemigrations --check --dry-run`: nenhuma mudança detectada.
- Os testes usaram banco separado em memória; não foram aplicadas migrações
  no banco existente. A aparência no navegador ainda não foi validada.
- Próxima pendência: separar as configurações locais das de produção,
  começando pela chave secreta em variável de ambiente.

1. Diagnóstico estrutural: concluído.
2. Preparação local: ambiente, dependências e testes concluídos; revisão visual pendente.
3. Preparação de produção: configurações por ambiente, estáticos e persistência.
4. Escolha da hospedagem: confirmar orçamento, suporte a Python/Django,
   armazenamento persistente e estratégia de backup antes de contratar.
5. Implantação em endereço provisório e testes de navegação, login e gravação.
6. Conexão do domínio: configurar DNS conforme o provedor escolhido e ativar HTTPS.
7. Verificação final: domínio, certificado, dados preservados após atualização
   e restauração de backup.

O domínio desejado, a existência de um domínio já registrado e o orçamento
ainda precisam ser informados antes da escolha de hospedagem. Essas decisões
não impedem a preparação local.

Nenhuma hospedagem foi criada, nenhum domínio foi contratado e os dados
existentes não foram migrados nesta etapa.

Referência: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
