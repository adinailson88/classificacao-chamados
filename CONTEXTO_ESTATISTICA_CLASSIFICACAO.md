# CONTEXTO — Diretriz estatística para classificação de chamados

> Registro metodológico para o repositório `classificacao-chamados`.
> Data: 2026-06-06, America/Bahia.
> Objetivo: orientar o Codex/IA a implementar estatística aderente ao problema real de classificação/reclassificação de chamados, evitando centralizar a análise em teste de normalidade.

## Decisão metodológica

Neste experimento, **normalidade não deve ser tratada como eixo central da análise estatística**.

O repositório não está avaliando uma variável contínua aproximadamente normal. O objeto de
análise é **classificação categórica**: acerto/erro (binário), concordância por categoria
(proporções), comparações **pareadas** entre modelos sobre os mesmos chamados, e séries de
concordância por turno. Para esse objeto, os testes paramétricos clássicos (t de Student,
ANOVA) são inadequados, e o Shapiro-Wilk serve apenas como **diagnóstico secundário** que
justifica a postura não paramétrica — nunca como critério principal. De fato, o Shapiro
rejeitou normalidade nos modelos avaliados, o que reforça a decisão.

## Eixo metodológico (testes aderentes ao problema)

A análise (`src/analise_estatistica.py` → `docs/dados/estatistica.json`) adota:

1. **Correlação confiança × acerto** — Spearman (e ponto-bisserial), por modelo. Mede se
   maior confiança bruta corresponde a maior acerto (entrada para calibração).
2. **Comparação global entre os modelos** — **Cochran's Q** sobre a matriz de acertos
   (mesmas linhas, k modelos): testa se as taxas de acerto são iguais.
3. **Comparação par a par** — **McNemar** (tabelas 2×2 do erro pareado) entre cada par de
   modelos, com **correção de Holm-Bonferroni** (step-down) para controlar o erro familiar
   (FWER) na multiplicidade dos pares.
4. **Ranking por blocos** — **Friedman + Nemenyi** sobre os recortes held-out de
   `comparacao_modelos.json`: ranks médios e diferença crítica (CD).
5. **Incerteza das métricas** — **bootstrap** IC95 para acurácia, e também para
   **macro-F1** e **recall macro** por modelo (robusto a desbalanceamento de categorias).
6. **Concordância** — **Kappa de Cohen** (IA × histórico) por modelo e **Kappa de Fleiss**
   entre as IAs.
7. **Resíduos/tendência da concordância por turno** — regressão linear simples, R²,
   Durbin-Watson (autocorrelação), classificação de tendência (sobe/cai/estável).
8. **Top confusões** — categorias historicamente mais confundidas por modelo (compacto,
   sem texto de chamado).
9. **Calibração** — ECE/MCE/Brier por modelo (`calibracao_modelos.py`) e calibração escalar
   out-of-fold (`calibracao_confianca.py`); softmax/margem alto NÃO é confiança calibrada.

## Histórico × validação humana (regra de leitura)

Enquanto a validação humana for pequena/incompleta, **todos os resultados acima são
"concordância contra a categoria histórica", não acerto validado**. O JSON e o painel
declaram isso explicitamente (`base_de_comparacao`, `observacao`).

A estatística já está **preparada para a verdade validada**: o bloco
`validacao_humana_modelos` em `estatistica.json` deriva a verdade da **conferência dupla**
(coluna **N** = CONFERÊNCIA IA: se "Correto", a categoria certa é a da IA/coluna G; senão
coluna **M** = CONFERÊNCIA GLPI: se "Correto", a categoria certa é a histórica/coluna C) e
mede o acerto **validado** por modelo. Esse bloco popula automaticamente à medida que M/N
forem preenchidas; **nenhuma aba nova é necessária** (lê o snapshot/registros e a aba principal).

## Mapa de implementação

- `src/analise_estatistica.py`: gera todos os blocos acima em `docs/dados/estatistica.json`.
- `.github/workflows/estatistica.yml`: roda o script (workflow_dispatch, após
  "Multimodelo - classificacao completa", e em agendamento periódico) e comita o JSON.
- `docs/index.html` (aba **Estatística**): renderiza correlação, acurácia+IC, Kappa,
  normalidade/resíduos, Cochran Q, Friedman/Nemenyi, **macro-F1 (IC95)**, **pares
  significativos McNemar+Holm**, **matriz IA×GLPI** e **acerto contra a verdade validada**.
- Requisitos: `requirements-estatistica.txt` (numpy, scikit-learn, scipy, statsmodels,
  gspread, google-auth).

## Pendências estatísticas reconhecidas

- Bootstrap **estratificado por categoria** (o atual reamostra linhas; estratificar por
  categoria refina o IC de recall/F1 por categoria).
- **Matriz de confusão completa** vs histórico e, depois, vs validada (hoje há "top confusões").
- Recalcular tudo contra a **verdade validada** como eixo principal quando a amostra de M/N
  for grande e representativa.