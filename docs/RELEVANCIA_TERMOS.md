# Relevância de termos por categoria + mapa de correlação

> Ferramenta exploratória de **triagem de taxonomia**. Responde "quais palavras
> caracterizam cada categoria?" e "quais categorias têm vocabulário sobreposto?".
> **Não** é métrica de acurácia, **não** decide categoria e **não** altera o histórico.

## Por que existe

Duas perguntas de pesquisa que o ranking de concordância não responde:

1. **O que define cada categoria, na prática?** Ex.: para hidráulica, esperamos
   `agua`, `vazamento`, `torneira`, `sanitario`. Se os termos característicos de uma
   categoria não fizerem sentido, há ruído na rotulagem ou na própria taxonomia.
2. **Quais categorias se confundem?** Categorias com vocabulário muito parecido são
   candidatas naturais a erro de classificação (histórico **e** IA) e a fusão/revisão
   na taxonomia. É o "mapa de correlação" — análogo a um mapa de geoprocessamento:
   célula **quente** = vocabulário sobreposto (correlação → 1); **fria** = separadas.

## Como mede

| Sinal | Método | Leitura |
|---|---|---|
| `top_log_odds` | Log-odds com **prior de Dirichlet informativo** (Monroe, Colaresi & Quinn, 2008), com z-score robusto | Termo **característico** da categoria frente a todas as outras. É o ranking recomendado para "palavras-chave". O prior evita que termos raros dominem. |
| `top_tfidf` | Peso médio no **centróide TF-IDF** da categoria | Termo frequente **e** discriminante dentro da categoria. |
| Mapa de correlação | **Cosseno** entre centróides TF-IDF de cada par de categorias | 1 = vocabulário sobreposto (candidatas a confusão/fusão); 0 = bem separadas. |

Representação: TF-IDF (1-grama e 2-gramas), `strip_accents`, stopwords PT-BR + ruído de
chamado/OSM (`favor`, `solicito`, `bloco`, `campus`…), `min_df` configurável.

## Privacidade

- Os termos são **agregados sobre todo o corpus**, não texto de um chamado.
- `--min-df` (default 5) descarta tokens raros; tokens puramente numéricos e com < 3
  caracteres são removidos. Isso reduz o risco de expor matrícula/nome que apareça pouco.
- Os JSON publicados (`docs/dados/*.json`) contêm apenas categorias, termos e scores —
  nenhum ID, título ou descrição livre.

## Como rodar

Dry-run (gera os JSON em `docs/dados/`, **não** grava na planilha):

```bash
python src/relevancia_termos.py --top-n 25 --min-df 5 --min-chamados-categoria 10
```

Aplicar (grava também as abas privadas `RELEVANCIA_TERMOS` e `CORRELACAO_CATEGORIAS`):

```bash
python src/relevancia_termos.py --aplicar
```

Via GitHub Actions: workflow **`relevancia_termos.yml`** (manual). Mantém `aplicar=false`
por padrão; sempre commita os JSON agregados. Exemplo:

```bash
gh workflow run relevancia_termos.yml --repo adinailson88/classificacao-chamados \
  -f aplicar=false -f top_n=25 -f min_df=5 -f min_chamados_categoria=10
```

## Saídas

- `docs/dados/termos_relevantes.json` — `termos_por_categoria[cat] = {n_chamados, top_log_odds[], top_tfidf[]}`.
- `docs/dados/correlacao_categorias.json` — `categorias[]`, `matriz[][]` (cosseno),
  `pares_mais_proximos[]`.
- `docs/mapa_correlacao.html` — visualizador standalone (mapa de calor + termos por
  categoria ao clicar). Abre direto pelo GitHub Pages.
- Abas privadas (só com `--aplicar`): `RELEVANCIA_TERMOS`, `CORRELACAO_CATEGORIAS`.

## Como ler no doutorado

- Termos característicos coerentes → evidência de que a categoria tem identidade textual.
- Termos incoerentes ou genéricos → suspeita de categoria "lixeira" ou rotulagem ruidosa.
- Pares de alta correlação → priorizar na **revisão da taxonomia** (etapa 46 do roteiro) e
  cruzar com a matriz de confusão IA×histórico: se duas categorias têm vocabulário
  sobreposto **e** se confundem muito, são candidatas a fusão ou a critério de desambiguação.
- É **triagem**, não veredito: a decisão de fundir/renomear categorias permanece humana.

## Verificação

Lógica validada localmente sobre corpus sintético (5 categorias temáticas, uma com
sobreposição proposital): termos característicos corretos por categoria e o par
`HIDRAULICA × HIDROSSANITARIO` corretamente apontado como o mais próximo. O estado real
das abas/planilha **não** pôde ser verificado neste ambiente (sem credenciais da conta
de serviço).
