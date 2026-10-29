# Identidade visual do AfirmaSUS

O tema está em `core/static/core/cover.css`, com navegação e rodapé em
`core/templates/core/base.html` e títulos internos em `page_intro.html`.
O CSS é carregado depois dos componentes externos. Os temas anteriores não
são carregados.

## Referência

[Buildcover](https://buildcover.com/): composição editorial, títulos misturando
serifa e sem serifa, fotografia ampla, controles discretos com cantos de 10px,
ações circulares e transições de cor/opacidade de 250ms. O movimento de entrada
é progressivo e respeita `prefers-reduced-motion`; o conteúdo funciona sem JS.

As fontes ABC Diatype e FK Roman Standard vêm dos arquivos públicos declarados
em `https://buildcover.com/webfonts/webfonts.css` e são servidas localmente.
O arquivo serifado disponibilizado pela referência se chama
`FKRomanStandardTrial-Regular.woff2`.

## Cores

Amostras dos traços e letras de `AfirmaSUS/logo.png`:

| Cor | Valor |
| --- | --- |
| Roxo principal | `#5f175e` |
| Violeta | `#824097` |
| Coral | `#f1505c` |
| Laranja | `#f1902d` |

O fundo principal é roxo, com textos brancos e destaques em laranja. A camada
`core/static/core/cover-dark.css` define essa inversão, as superfícies de roxo
mais escuro e o espaçamento compacto. O fundo bege da imagem não faz parte do tema.
O cabeçalho usa novamente `static/logo_roxo.png`, ao lado do nome do projeto.
O grafismo decorativo compartilhado está em `core/templates/core/intro_art.html`.

## Verificação local

Os testes existentes usam `python manage.py test core --noinput`.
O script opcional `scripts/verify_cover.py` usa Playwright e Chrome instalado,
com o servidor local em `127.0.0.1:8012`. Verifica rotas públicas, renderização
em 1440px e 390px, navegação móvel, filtros e detalhes do mapa e controles de
mídias. As prévias autenticadas usam um usuário em memória, sem criar usuários
nem salvar registros. Capturas e relatório ficam em `.qa-cover/`.

O JavaScript do Plotly em `core/static/core/vendor/plotly.min.js` vem do pacote
Python instalado, evitando incompatibilidade entre o formato dos dados e o
renderizador. Ao atualizar Plotly, atualize esse bundle usando
`plotly.offline.get_plotlyjs()`.
