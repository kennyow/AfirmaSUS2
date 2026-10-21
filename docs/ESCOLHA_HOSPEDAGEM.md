# Escolha da hospedagem

Pesquisa em fontes oficiais em 20/10/2026. A escolha depende do orçamento
e de haver um domínio já registrado; essas informações estão pendentes.

## Direção definida com o usuário

Orçamento inicial zero e nenhum domínio registrado. Vamos começar no plano
Beginner gratuito do PythonAnywhere, usando o subdomínio da conta. A criação
da conta e o nome de usuário ainda estão pendentes. Não há recurso publicado.

A documentação atual anuncia um worker, 512 MiB e expiração mensal da web app;
será necessário acompanhar a data de expiração/renovação no painel. Domínio
próprio exigirá rever o plano no futuro. Não haverá contratação nesta fase.

A documentação lista Python até 3.13 na imagem `innit`. A instalação no
servidor deverá usar Python 3.13 e ser validada lá; a suíte local foi executada
em 3.14, o que não comprova a compatibilidade remota por si só.

As dependências locais ocupam cerca de 237,6 MiB, os JSON 0,07 MiB e o banco
0,21 MiB. Isso indica viabilidade inicial, mas não garante caber na conta:
Linux, cache de instalação, arquivos coletados e uploads alteram o consumo.
Não envie `.venv`, caches ou a saída `staticfiles`; instale as dependências
no servidor, sem cache, e confira a quota antes da publicação.

O WSGI será executado pela plataforma; `serve.py` não deverá ser iniciado
como serviço separado no PythonAnywhere. As instruções de implantação serão
ajustadas após conhecer o usuário e os caminhos da conta.

Fontes adicionais:
- https://help.pythonanywhere.com/pages/FreeAccountsFeatures/
- https://help.pythonanywhere.com/pages/PythonVersions/
- https://help.pythonanywhere.com/pages/DiskQuota

## Requisitos do projeto atual

- Python compatível com as dependências registradas; o ambiente local usa 3.14.
- Processo Django WSGI e armazenamento persistente para SQLite, JSON e uploads.
- Uma única instância e execução sem gravações JSON simultâneas.
- HTTPS, domínio próprio, transferência dos dados e backup externo.
- Configuração de entrega HTTP dos uploads ainda pendente.

## Opções verificadas

| Opção | Compatibilidade e condições |
| --- | --- |
| Render, serviço pago com disco | Permite usar `serve.py` e volume persistente. O disco só está disponível em execução, não durante build ou pre-deploy. A configuração de build deverá usar uma pasta temporária existente para DJANGO_DATA_DIR; o processo em execução usará o volume. O plano e o tamanho do disco precisam ser cotados no painel. |
| PythonAnywhere Developer | A página oficial anuncia US$ 10/mês, 5 GB e domínio próprio. Usa o WSGI da plataforma, exigindo adaptar as instruções de inicialização. O plano anuncia três workers; será necessário confirmar a configuração para uma única execução antes de usar as gravações JSON atuais. |
| PythonAnywhere Beginner | Gratuito, 512 MB e subdomínio da plataforma. Sem domínio próprio no plano gratuito. A capacidade para dependências, dados e uploads e as versões Python disponíveis precisam ser verificadas antes de escolhê-lo para demonstração. |

O Render gratuito não atende à persistência local do projeto: não permite
anexar disco persistente e o sistema de arquivos é temporário.

Os valores não incluem registro/renovação de domínio, eventuais impostos,
conversão cambial ou outros serviços. Não houve contratação nem criação
de recursos nesta pesquisa.

## Decisão pendente

1. Definir orçamento mensal e informar se já existe um domínio registrado.
2. Selecionar provedor e conferir o preço final e as versões Python disponíveis.
3. Preparar os arquivos de implantação específicos do provedor escolhido.
4. Implantar em endereço provisório, transferir dados e validar persistência.
5. Configurar domínio, HTTPS e backups.

## Fontes oficiais

- https://render.com/docs/disks
- https://render.com/docs/free
- https://render.com/docs/custom-domains
- https://render.com/pricing
- https://www.pythonanywhere.com/pricing/
- https://help.pythonanywhere.com/pages/CustomDomains/
