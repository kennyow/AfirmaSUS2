# Publicação gratuita — conta kennyow

Endereço previsto: `https://kennyow.pythonanywhere.com`.
Ainda não há publicação confirmada.

## Etapa atual: enviar o código

1. Entre na conta kennyow em https://www.pythonanywhere.com/.
2. Abra **Files** e confira o diretório `/home/kennyow`.
3. Use **Upload a file** para enviar `afirmasus2-codigo.zip`.
4. Abra **Consoles → Bash** e execute:

```bash
cd /home/kennyow
unzip -n afirmasus2-codigo.zip -d AfirmaSUS2
ls /home/kennyow/AfirmaSUS2/afirmasus_django/manage.py
python3.13 --version
```

O parâmetro `-n` impede sobrescrever arquivos existentes. O ZIP contém código,
templates, estáticos originais e requisitos. Não contém ambiente virtual,
banco, JSON, uploads ou segredos. Os dados serão transferidos separadamente.
Não execute migrações nem inicie a aplicação nesta etapa.

## Caminhos previstos para as próximas etapas

- Código: `/home/kennyow/AfirmaSUS2/afirmasus_django`.
- Ambiente virtual: `/home/kennyow/.virtualenvs/afirmasus`.
- Dados persistentes: `/home/kennyow/afirmasus-dados`.
- Host permitido: `kennyow.pythonanywhere.com`.

Depois de confirmar o upload e o Python disponível, instalaremos as
dependências em ambiente próprio. O WSGI será configurado pela aba Web,
com **Manual configuration**, após preparar dados e variáveis de ambiente.

Referência: https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/
