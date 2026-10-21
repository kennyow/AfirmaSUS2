# Ambiente local do AfirmaSUS2

Execute os comandos abaixo no PowerShell, na pasta `AfirmaSUS2`.
O ambiente exclusivo está em `.venv`; não é necessário ativá-lo.

## Instalar as versões registradas

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.in` lista as dependências diretas. `requirements.txt` registra
as versões resolvidas após uma instalação bem-sucedida.

## Verificar a aplicação

```powershell
.\.venv\Scripts\python.exe afirmasus_django/manage.py check
.\.venv\Scripts\python.exe afirmasus_django/manage.py test core
```

Os testes Django usam um banco de testes separado. Não execute importações de
dados ou migrações no banco existente sem preparar um backup.

## Iniciar para desenvolvimento

Depois da validação local e da conferência das migrações:

```powershell
.\.venv\Scripts\python.exe afirmasus_django/manage.py runserver
```

Acesse `http://127.0.0.1:8000/`. Encerre com `Ctrl+C`.
Esse servidor é destinado ao desenvolvimento local.

## Chave secreta e ambiente

Em desenvolvimento, `DJANGO_DEBUG` é `true` por padrão e há uma chave local
exclusiva para desenvolvimento. A chave antiga foi removida do código.
Sessões assinadas com a chave antiga podem exigir novo login.

Na hospedagem, configure `DJANGO_DEBUG=false` e `DJANGO_SECRET_KEY` no painel
de variáveis de ambiente do provedor. Gere uma chave aleatória com pelo menos
50 caracteres; não reutilize a chave local nem publique a chave em arquivos
versionados. A aplicação recusa iniciar sem uma chave adequada com DEBUG falso.

Para configurar apenas a sessão atual do PowerShell, sem mostrar a chave:

```powershell
$env:DJANGO_SECRET_KEY = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

Arquivos `.env` não são carregados automaticamente. Use as variáveis do
processo ou o painel da hospedagem. Domínio, HTTPS e demais configurações
de produção serão tratados nas próximas pendências.

## Domínios permitidos e CSRF

`DJANGO_ALLOWED_HOSTS` recebe hosts separados por vírgula, sem protocolo,
porta ou caminho. Em desenvolvimento, o padrão é `localhost,127.0.0.1,[::1]`.
Em produção, a lista é obrigatória e `*` não é aceito.

Exemplo ilustrativo para a hospedagem, a substituir pelo domínio real:

```text
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
```

`DJANGO_SECRET_KEY` também deve estar configurada conforme a seção anterior.
Origens CSRF incluem protocolo e, quando não padrão, porta. Essa lista é
opcional: requisições de formulário na mesma origem já são verificadas pelo
Django. Declare apenas origens extras que realmente precisem enviar formulários.
Ela não libera CORS nem substitui a validação do token CSRF.

Estas variáveis preparam a aplicação; a conexão DNS e o certificado HTTPS
serão configurados depois da escolha da hospedagem e do domínio.

Para executar também os testes isolados das configurações, a partir de AfirmaSUS2:

```powershell
Push-Location afirmasus_django
..\.venv\Scripts\python.exe -m unittest setup.test_settings -v
Pop-Location
```

## Arquivos estáticos em produção

WhiteNoise entrega os arquivos estáticos pela própria aplicação Django.
Com `DJANGO_DEBUG=false`, a coleta gera arquivos com nomes versionados,
compressão quando vantajosa e cache para os arquivos versionados.

Na implantação, após instalar `requirements.txt` e configurar as variáveis
de produção, execute a partir de `AfirmaSUS2`:

```powershell
.\.venv\Scripts\python.exe afirmasus_django/manage.py collectstatic --noinput
```

No Linux, use o Python do ambiente da hospedagem com o mesmo `manage.py`.
A saída fica em `afirmasus_django/staticfiles/`, ignorada pelo Git, e precisa
ser gerada a cada implantação e estar disponível quando a aplicação iniciar.
Edite os arquivos originais em `static/` ou `core/static/`, nunca essa saída.

O teste `test_estaticos_coletados_e_servidos_em_producao` coleta os arquivos
em uma pasta temporária e verifica respostas HTTP para logo, CSS, JavaScript
e estilos do administrador com DEBUG falso.

Uploads em `media/` serão tratados na etapa de armazenamento persistente.
Bibliotecas carregadas por CDN nos templates continuam dependendo desses serviços.

## Servidor de produção

O projeto usa Waitress, servidor WSGI compatível com Windows e Linux.
Depois de definir as variáveis de produção e executar `collectstatic`,
inicie a partir de `AfirmaSUS2`:

```powershell
$env:DJANGO_DEBUG = 'false'
$env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1'
$env:HOST = '127.0.0.1'
$env:PORT = '8080'
.\.venv\Scripts\python.exe afirmasus_django/serve.py
```

Defina também `DJANGO_SECRET_KEY` conforme a seção de chave secreta.
Acesse `http://127.0.0.1:8080/login/` e encerre com `Ctrl+C`.
`serve.py` assume DEBUG falso quando a variável está ausente e recusa DEBUG true.

Na hospedagem Linux, o comando, com diretório de trabalho `AfirmaSUS2`, será:

```text
python afirmasus_django/serve.py
```

Configure `HOST=0.0.0.0` apenas quando o provedor exigir escuta em todas as
interfaces do contêiner. `PORT` aceita a porta fornecida pelo provedor.
O padrão local é `127.0.0.1:8080`. Use os hosts reais na hospedagem.

Mantenha uma única instância e uma thread enquanto houver gravações em JSON.
O servidor não faz migrações, coleta de estáticos ou importação automaticamente.
HTTPS, proxy confiável, reinício automático, persistência e entrega de uploads
ainda dependem das próximas etapas e da hospedagem escolhida.

Para repetir o teste HTTP local (requer a coleta dos estáticos):

```powershell
Push-Location afirmasus_django
..\.venv\Scripts\python.exe -m unittest setup.test_server -v
Pop-Location
```

O teste inicia e encerra uma instância local temporária; verifica login,
logo e rejeição de Host desconhecido, sem enviar formulários.

## Armazenamento persistente e cópias

`DJANGO_DATA_DIR` seleciona uma pasta absoluta existente que contém
`db.sqlite3`, os arquivos JSON e `media/`. Sem a variável, os caminhos locais
atuais são preservados. Código e estáticos continuam na pasta da aplicação.
Na hospedagem, configure essa variável com o caminho de um volume persistente;
uma pasta comum em um contêiner temporário não garante persistência.

Para preparar uma cópia inicial ou um backup, pare todas as instâncias do
servidor e outros processos que gravem dados. A partir de `AfirmaSUS2`, use
um destino absoluto novo, fora da pasta de origem:

```powershell
.\.venv\Scripts\python.exe afirmasus_django/manage.py copiar_dados 'C:\caminho\persistente\afirmasus-dados'
```

Substitua o exemplo por um local gravável apropriado. O comando usa a API de
backup SQLite, verifica a integridade da cópia e copia JSON e uploads.
Recusa destinos existentes. Em caso de falha, não use a pasta incompleta.
O servidor deve ficar parado durante toda a cópia para manter banco, JSON
e uploads coerentes entre si.

Depois de conferir a cópia, configure no processo que inicia o servidor:

```powershell
$env:DJANGO_DATA_DIR = 'C:\caminho\persistente\afirmasus-dados'
```

Na hospedagem Linux, um exemplo seria `DJANGO_DATA_DIR=/data/afirmasus`,
desde que `/data` esteja efetivamente montado como volume persistente e os
dados já tenham sido copiados para ele. Não inicie com uma pasta vazia:
isso pode criar um banco novo e deixar o conteúdo JSON ausente.

Para backups futuros, execute `copiar_dados` com DJANGO_DATA_DIR apontando
para os dados em uso e escolha outro destino novo. Guarde também uma cópia
fora do volume/servidor e controle o acesso: ela contém os dados da aplicação.
Agendamento e retenção dos backups ainda serão configurados na hospedagem.

Para restaurar, pare o servidor, extraia ou copie um backup completo para uma
pasta nova, confira seu conteúdo e aponte DJANGO_DATA_DIR para essa pasta.
Reinicie e valide login, calendário e uploads antes de voltar ao uso.
Não sobrescreva os dados ativos; preserve-os para poder reverter.

Mantenha uma única instância enquanto o projeto usar SQLite e gravações JSON.
A entrega HTTP dos uploads e a comprovação de persistência entre implantações
serão configuradas e verificadas quando a hospedagem for definida.
