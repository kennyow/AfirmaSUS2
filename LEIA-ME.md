# AfirmaSUS–JP: piloto de migração para Cloudflare

Preparado em 05/11/2026. Este pacote é uma cópia isolada do código local, com um
piloto novo de login e biblioteca pública. Não é uma migração concluída do site.
O original no OneDrive, o PythonAnywhere, o Drive e o DNS não foram modificados.
Não foram copiados banco de produção, contas, sessões, JSON de conteúdo,
uploads, arquivos de configuração privada nem ambientes virtuais.

## O que já funciona e foi testado

- Login com contas Django e saída por POST.
- Biblioteca pública com os 100 arquivos mais recentes.
- Envio somente por contas ativas com a permissão de adicionar arquivo público.
- Seleção de arquivo no dispositivo, sem formulário de links ou conversor do Drive.
- JPG/PNG/WebP de até 5 MB e 20 milhões de pixels; PDF/DOCX/XLSX de até 10 MB.
- Validação básica do conteúdo e extensão; não é análise antivírus.
- Nome aleatório para o objeto e registro de título, autor, tipo e tamanho no banco.
- Download como anexo. Imagens podem aparecer como prévia pública.
- Se o armazenamento falha, não publica registro; se o banco falha após o upload,
  tenta remover o objeto recém-enviado. Falhas nessa compensação ficam no log
  e exigem reconciliação; não há transação única entre D1 e R2.
- 15 testes locais passaram usando Django 5.2.18 e armazenamento temporário em disco.

O perfil local usa `setup.pilot_settings`, SQLite isolado e pasta `pilot-media`.
São recursos de teste. O perfil Cloudflare usa D1 e o binding R2 `BUCKET`,
sem exigir chaves S3 no código ou no navegador.

## O que ainda não foi validado

A instalação do simulador Workers falhou por indisponibilidade de rede/DNS
neste ambiente. Portanto, o entrypoint, D1, R2, empacotamento de Pillow,
cookies HTTPS e desempenho de login NÃO foram testados no runtime Cloudflare.
`pyproject.toml`, `worker.py`, `setup/cloudflare_settings.py` e `wrangler.jsonc`
são a configuração experimental para essa próxima validação.

A biblioteca é independente das páginas originais. O código original de mapa,
equipe, estatísticas, atas, calendário e mídias foi preservado como referência;
essas páginas ainda precisam ser integradas e testadas no novo ambiente.
Seus usos antigos de Drive e de JSON em disco continuam nesse código inativo.
O piloto não os utiliza. Não apague o Drive ou desative o site existente ainda.

Também faltam: migração dos dados e contas existentes; associação dos arquivos
às páginas atuais; substituição dos links antigos; edição/exclusão de arquivos;
paginação; reconciliação e backup; eventual compressão/remoção de EXIF;
medição e controle do consumo total. Não há trava global de 10 GB neste piloto.

## Testar localmente sem conta Cloudflare

Em uma pasta com Python e as dependências locais do projeto instaladas:

```powershell
python manage.py test cloudpilot.test_pilot --settings=setup.pilot_settings
python manage.py migrate --settings=setup.pilot_settings
python manage.py createsuperuser --settings=setup.pilot_settings
python manage.py preparar_envio --settings=setup.pilot_settings
python manage.py runserver 127.0.0.1:8000 --settings=setup.pilot_settings
```

Abra `http://127.0.0.1:8000/`. O superusuário pode enviar. No painel `/admin/`,
crie as contas de teste e associe as autorizadas ao grupo **Envio de arquivos**.
Não existe cadastro público automático nesse piloto. Senhas são escolhidas
interativamente; não existe senha pronta neste pacote.

Para autorizar contas existentes pelo terminal:

```powershell
python manage.py preparar_envio nome_da_conta --settings=setup.pilot_settings
```

O comando verifica se todas as contas indicadas existem e estão ativas antes de
alterar suas permissões. Usuários comuns continuam sem permissão de upload.

## Preparação para testar Cloudflare

1. Crie sua conta em https://dash.cloudflare.com/ . Nenhuma conta foi criada aqui.
2. Primeiro valide o simulador local em um ambiente que possa baixar pacotes.
   Não é necessário comprar domínio para essa etapa.
3. Instale `uv` pelo instalador oficial e execute nesta pasta `uv sync`.
   Gere/revise `uv.lock` para fixar as dependências resolvidas.
4. Crie uma chave exclusiva de teste local, com pelo menos 50 caracteres, em
   `.dev.vars` (arquivo ignorado pelo Git), no campo `DJANGO_SECRET_KEY`.
   Não use uma chave do site atual, não cole valores no chat e não publique esse arquivo.
5. Crie o diretório `public/static` com `collectstatic` usando o perfil local.
6. Teste `uv run pywrangler dev` e confirme a compatibilidade dos pacotes.
   O simulador pode exigir configuração local adicional dos bindings; não
   trate a passagem dos testes Django como passagem dos testes Workers.
7. Somente após isso configure recursos NOVOS de teste: D1 `afirmasusjp-piloto`
   e R2 Standard `afirmasusjp-piloto-publicos`. A assinatura R2 pode solicitar
   configuração de cobrança; revise os termos antes de ativar.
8. Substitua o UUID zerado do D1 em `wrangler.jsonc`. Configure o host exato do
   Worker em `DJANGO_ALLOWED_HOSTS` e a URL real de mídia em `MEDIA_PUBLIC_URL`.
   O domínio de mídia indicado no exemplo ainda NÃO existe/configurado.
9. Configure `DJANGO_SECRET_KEY` como secret do Worker pelo fluxo interativo
   `uv run pywrangler secret put DJANGO_SECRET_KEY`. Não registre valores no Git.
10. O SQL de bootstrap em `d1-migrations/0001_piloto.sql` é para banco NOVO e
    VAZIO. Contém esquema e permissões, sem contas ou conteúdo. Nunca aplique
    esse bootstrap sobre dados existentes. A execução real no D1 está pendente.
11. Para autenticar, será necessário criar/migrar contas com hashes e permissões
    por um procedimento administrativo separado e privado. O piloto NÃO expõe
    endpoints públicos para criar administradores ou executar migrações.
12. Valide em endereço de teste: login, permissão, upload, objeto presente no R2,
    registro no D1, download, imagem em outro navegador e persistência após novo
    deploy. Só então avance para a migração das páginas e dados existentes.

## Publicação final pretendida

- `afirmasusjp.com.br`: aplicação no Workers.
- `arquivos.afirmasusjp.com.br`: somente arquivos públicos do R2.
- D1: usuários, permissões e registros, após comprovar compatibilidade.
- Estáticos: binding ASSETS do Worker.

O domínio ainda precisa ser registrado e configurado. Não foi verificada sua
disponibilidade. Não existe rota para o domínio final na configuração do piloto.
Após a migração, o computador do usuário só será origem do upload; o conteúdo
permanecerá no R2. Cópias temporárias do acervo antigo só devem ser removidas
depois de conferir a transferência e o backup.

## Custos e restrições verificados em 05/11/2026

R2 Standard: franquia de 10 GB-mês, 1 milhão de operações classe A e 10 milhões
classe B por mês, com saída gratuita. O excedente é cobrado. Workers é separado:
a integração oficial django-cf exige plano pago para produção devido aos limites
de CPU, com assinatura base de US$ 5/mês no Workers Standard, além de eventuais
excedentes. D1 tem franquia própria. Domínio é pago separadamente. Não houve
compra, assinatura, deploy nem cobrança autorizada neste trabalho.

O backend Django/D1 não oferece transações/rollback e há limitações de ORM/admin.
Precisamos verificar as operações existentes antes de migrar o site completo.

Fontes oficiais:
- https://developers.cloudflare.com/workers/languages/python/packages/django/
- https://github.com/cloudflare/workers-py/tree/main/packages/django-cf
- https://developers.cloudflare.com/workers/platform/pricing/
- https://developers.cloudflare.com/r2/pricing/
- https://developers.cloudflare.com/r2/buckets/public-buckets/

