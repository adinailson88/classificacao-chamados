# Classificacao de Chamados

Repositorio experimental para avaliacao da classificacao e reclassificacao automatica de chamados, separado do repositorio operacional Malha IA.

O objetivo e manter um experimento rastreavel, com processamento por turnos, logs, metricas, painel publico e preparacao para validacao humana.

## Estado atual

1. A planilha experimental e lida por conta de servico Google Cloud via `gspread`.
2. O ID da planilha nao e versionado; use `SPREADSHEET_ID` ou `spreadsheet_id.local`.
3. A chave da conta de servico nao e versionada; use `credenciais_sa.json` local ou o secret `GCP_SA_KEY` no GitHub Actions.
4. A aba principal e `CHAMADOS_ESQUELETO_REDUZIDO`, com leitura em `A:M`.
5. Os dados reais gerados em `dados/*.json` e `dados/*.jsonl` ficam ignorados no Git.
6. Os dados publicos do dashboard ficam em `docs/dados`.
7. Nenhum script escreve na planilha sem flag explicita `--aplicar`; workflows de reclassificacao rodam em dry-run por padrao.
8. A validacao humana ja pode ser preparada, mas a revisao manual fica **pausada** ate o fortalecimento dos scripts/modelos.

### 7 IAs materializadas (multimodelo)

As **7 IAs estao completas**, com 13.825 chamados por modelo, 0 pendentes e predicao
**out-of-fold** (`kfold_5`, sem vazamento). Concordancia contra a categoria historica:

| Modelo | Concordancia vs historico |
|---|---|
| `linear_svc` | 80,26% |
| `extra_trees` | 78,47% |
| `sgd` | 77,51% |
| `random_forest` | 76,80% |
| `regressao_logistica` | 76,59% |
| `naive_bayes` | 70,07% |
| `lstm` | 67,57% |

Onde cada coisa aparece no painel:

- **`Classificacao`** usa apenas a **Etapa 1 / LSTM single-model** (fonte `registros.json`).
- **`Modelos`**, **`Multimodelo`** e **`Estatistica`** trazem a **comparacao das 7 IAs**.
- `multimodelo_registros.json` foi **removido** porque multiplicava chamados por 7 (exibia
  ~96.775 predicoes como se fossem chamados). **Nao recriar.**

A analise estatistica assume **pressupostos nao parametricos**: Shapiro rejeitou
normalidade nos 7 modelos. Por isso o foco e Spearman, Friedman/Nemenyi, Cochran Q,
McNemar e bootstrap. Todos os numeros sao **contra o historico**, nao contra validacao
humana (`validados=0`).

## Colunas da aba principal

```text
A  ID Chamado
B  TITULO
C  CATEGORIA COMPLETA
D  DESCRICAO GLPI
E  TITULO O.S.M.
F  DESCRICAO O.S.M.
G  Classificacao IA
H  Avaliacao (%)
I  Executor
J  Criticidade Atribuida por IA
K  Comparacao
L  Classificado_Confianca_IA
M  CONFERENCIA GLPI
N  CONFERENCIA IA
O  Classificacao IA - 2
P  CONFERENCIA IA - 2
```

Saida da IA: `G:J`.

`K` compara a classificacao da IA com a categoria historica: `=SE(G="";"";G=C)`.

### Validacao humana (modo de conferencia dupla)

A validacao humana e registrada em DUAS colunas independentes, o que permite avaliar
nao so o acerto da IA, mas tambem a qualidade da propria classificacao historica e,
por consequencia, falsos positivos e falsos negativos:

- `M` (**CONFERENCIA GLPI**): o avaliador marca se a classificacao historica do GLPI
  (coluna `C`) esta `Correto` ou `Errado`. Celula vazia = ainda nao validada.
- `N` (**CONFERENCIA IA**): o avaliador marca se a classificacao da IA (coluna `G`) esta
  `Correto` ou `Errado`. Celula vazia = ainda nao validada.

A combinacao das duas colunas forma uma matriz 2x2 (IA `Correto`/`Errado` x GLPI
`Correto`/`Errado`), que distingue, por exemplo, os casos em que a IA acerta e o
historico erra (a IA corrige o GLPI) dos casos opostos. Convencao de leitura no codigo:
o valor `Correto` (sem distincao de caixa) indica acerto; qualquer outro valor nao vazio
e tratado como `Errado`. A leitura dessas colunas e read-only e nao sobrescreve a planilha.

### Coluna O (`Classificacao IA - 2`): resultado da reclassificacao

A `CONFERENCIA IA` (coluna `N`) refere-se a classificacao ORIGINAL da IA (coluna `G`,
Etapa 1). Quando um chamado e reclassificado (Etapa 2), gravar o novo resultado de volta
em `G` apagaria o registro original e tornaria a conferencia `N` ambigua (o avaliador
disse "Errado" sobre `G`, nao sobre a reclassificacao). Por isso a reclassificacao e
gravada numa coluna propria, `O` (**Classificacao IA - 2**), preservando `G`, `M` e `N`.
Assim e possivel comparar, lado a lado, a classificacao original, o veredito humano e a
reclassificacao. A escrita em `O` e opcional (flag `--gravar-coluna-2` /
input `gravar_coluna_2`), usada com um unico modelo no escopo, e nao toca em nenhuma
outra coluna.

A reclassificacao (coluna `O`) tem sua propria conferencia humana na coluna `P`
(**CONFERENCIA IA - 2**), que funciona como `M` e `N`: o avaliador marca se a
reclassificacao esta `Correto`/`Errado`. Com isso, o painel mede tambem o acerto validado
da reclassificacao (`acerto_reclass_validado` em `calibracao.json`). O ciclo fica:
a IA reclassifica (`O`) e ENTAO aguarda a conferencia humana (`P`) — nenhum passo
automatico consome `O` antes de `P` ser preenchida.

## Fluxo principal

1. Etapa 1: classificacao progressiva em turnos de 15.
2. Etapa 2: reclassificacao de casos de baixa confianca.
3. Fortalecimento antes da etapa manual: LSTM configuravel, memoria validada, reclassificacao priorizando menor confianca e modelo robusto local.
4. Etapa 3: validacao humana.
5. Etapas finais: matriz de confusao, metricas por categoria, confianca calibrada e indicadores consolidados.

## Objetivo final do modelo

Arquivo de referencia: `OBJETIVO_FINAL_MODELO_IA.txt`.

A meta e chegar a um modelo treinado e calibrado que indique, para a maioria das categorias, se a categoria historica do chamado esta correta ou nao. A confianca minima alvo e `>=95%`, mas essa confianca precisa ser validada/calibrada: softmax alto sozinho nao comprova acerto.

Calibracao preliminar publicada:

- `docs/dados/calibracao_modelos.json`: diagnostico bruto por IA (ECE, Brier, faixa >=95%).
- `docs/dados/calibracao_ajustada_modelos.json`: calibracao escalar out-of-fold de
  `P(previsao correta | confianca_bruta)`, ainda contra historico.
- Resultado atual relevante: `linear_svc` continua melhor em concordancia global (`80,26%`)
  e, apos calibracao escalar, sua faixa ajustada `>=95%` tem `n=5.125` e acerto historico
  `98,36%`. Isso ainda nao substitui validacao humana.

O reforco automatico antes da revisao manual esta em:

1. `config_experimento.json`: define `objetivo_final`, `modelo_ia` e `memoria_validada`.
2. `src/modelo_lstm.py`: aceita perfil LSTM `robusto`.
3. `src/memoria_validada.py`: le apenas exemplos humanos com `categoria_validada` e `usar_para_treino=SIM`.
4. `src/executar_etapa1.py` e `src/executar_etapa2.py`: usam a memoria validada quando ela existir.
5. `src/executar_etapa2.py`: prioriza menor confianca antes de reclassificar.
6. `src/classificacao_multimodelo.py` e `src/reclassificacao_multimodelo.py`: executam o ciclo completo por modelo em abas separadas, com predicao out-of-fold.

## Comandos locais

Validacao de sintaxe:

```bash
python -m py_compile src/classificar_etapa.py src/exportar_etapa.py src/registrar_snapshot_inicial.py
```

Testes sem rede:

```bash
python tests/test_github_first.py
```

Fluxo GitHub-first com conta de servico:

```bash
python src/registrar_snapshot_inicial.py
python src/classificar_etapa.py --modo incremental --modelo producao
python src/exportar_etapa.py
python src/exportar_etapa.py --aplicar
```

Etapa 1 progressiva:

```bash
python src/executar_etapa1.py --modelo producao --max-turnos 60
python src/executar_etapa1.py --modelo producao --max-turnos 60 --aplicar
```

Etapa 2, reclassificacao:

```bash
python src/executar_etapa2.py --modelo producao --max-turnos 40
python src/executar_etapa2.py --modelo producao --max-turnos 40 --aplicar
```

Multimodelo completo:

```bash
python src/classificacao_multimodelo.py --modelos leves --max-turnos 1
python src/reclassificacao_multimodelo.py --modelos leves --max-turnos 1
```

Para gravar resultados na planilha, acrescente `--aplicar` somente depois de revisar o dry-run.

Preparacao da validacao humana:

```bash
python src/preparar_validacao_humana.py --modo divergentes --limite 0
python src/preparar_validacao_humana.py --modo divergentes --limite 0 --aplicar
```

Reset controlado do experimento:

```bash
python src/resetar_experimento.py
python src/resetar_experimento.py --aplicar --confirmar RESETAR
```

## Workflows

1. `etapa1_turnos.yml`: classificacao progressiva, agendada a cada 15 minutos.
2. `dashboard.yml`: exporta os JSONs publicos do painel para `docs/dados`, agendado a cada 30 minutos.
3. `etapa2_reclassificacao.yml`: reclassificacao, disparo manual.
4. `reclassificacao_robusta.yml`: modelo pesado local, disparo manual.
5. `preparar_validacao.yml`: monta a aba `VALIDACAO_HUMANA`, disparo manual.
6. `resetar.yml`: reset seguro, disparo manual com confirmacao.
7. `classificacao_incremental.yml`: fluxo incremental antigo, mantido manual.
8. `multimodelo_classificacao.yml`: classificacao por modelo em `CLASSIF__<modelo>`, manual, dry-run por padrao.
9. `multimodelo_reclassificacao.yml`: reclassificacao por modelo em `RECLASS__<modelo>`, manual, dry-run por padrao.
10. `reclassificar_validados.yml`: reclassifica AUTOMATICAMENTE os chamados ja validados (colunas `M` e `N` preenchidas) com o modelo robusto, gravando o resultado na coluna `O` (Classificacao IA - 2). Cron a cada 15 min, no maximo 15 chamados por execucao; so treina quando ha validados pendentes.
11. `transformer_ft.yml`: 8o modelo, **BERTimbau com fine-tuning** (contextual, self-attention). PESADO (torch + transformers, fine-tuning em CPU) — manual, timeout alto. Acoes: `reclassificar_validados` (refaz a coluna `O` de todos os validados com o transformer, 1 treino) ou `comparar` (avalia numa janela held-out e grava em `COMPARACAO_MODELOS`, lado a lado com os 7).
12. `iniciar_pipeline.yml`: orquestrador manual que dispara Etapa 1 + reclassificar_validados + dashboard de uma vez.
13. `relevancia_termos.yml`: termos caracteristicos por categoria + mapa de correlacao, manual, dry-run por padrao; commita os JSON agregados.

Nos workflows manuais com input `aplicar`, mantenha `false` ate revisar logs, ganho liquido e impacto esperado.

Dependencias em CI:

- `requirements-leves.txt`: base comum sem TensorFlow (`gspread`, `google-auth`, `numpy`, `scikit-learn`).
- `requirements.txt`: ambiente completo com TensorFlow, usado quando o fluxo realmente precisa de LSTM/producao.
- `requirements-robusto.txt`: transformer local pesado, usado apenas nos fluxos de reclassificacao robusta.

## Dashboard publico

O painel esta em:

```text
docs/index.html
```

Ele consome:

```text
docs/dados/resumo.json
docs/dados/registros.json                 # Etapa 1 / LSTM (aba Classificacao)
docs/dados/log_turnos_classificacao.json
docs/dados/metricas_por_categoria.json
docs/dados/log_turnos_reclassificacao.json
docs/dados/metricas_experimento.json
docs/dados/comparacao_modelos.json
docs/dados/comparacao_categoria.json
docs/dados/comparacao_previsoes.json    # versao sanitizada, sem ID/titulo/observacao
docs/dados/multimodelo_turnos.json        # 7 IAs (abas Modelos / Multimodelo)
docs/dados/multimodelo_metricas.json      # 7 IAs
docs/dados/multimodelo_reclass_turnos.json
docs/dados/estatistica.json               # analise nao parametrica (aba Estatistica)
docs/dados/calibracao.json
docs/dados/calibracao_modelos.json        # diagnostico bruto por IA
docs/dados/calibracao_ajustada_modelos.json # calibracao escalar preliminar por IA
```

O site publicado pelo GitHub Pages deve identificar o projeto como `Classificacao de Chamados - Painel Experimental`. A referencia a Malha IA deve aparecer apenas como contexto de origem, nao como nome principal do site.

## Relevancia de termos + mapa de correlacao (exploratorio)

`src/relevancia_termos.py` calcula, por categoria, os **termos caracteristicos**
(log-odds com prior de Dirichlet + peso TF-IDF — ex.: `agua`, `torneira`, `sanitario`
para hidraulica) e o **mapa de correlacao** entre categorias (cosseno entre centroides
TF-IDF). E uma triagem de **taxonomia**, nao uma metrica de acuracia: nao decide categoria
e nao altera o historico. Saidas agregadas e sanitizadas em `docs/dados/termos_relevantes.json`
e `docs/dados/correlacao_categorias.json`; visualizador (mapa de calor estilo
geoprocessamento) em `docs/mapa_correlacao.html`. Workflow manual `relevancia_termos.yml`,
dry-run por padrao. Detalhes em `docs/RELEVANCIA_TERMOS.md`.

```bash
python src/relevancia_termos.py --top-n 25 --min-df 5 --min-chamados-categoria 10
```

## Documentacao

1. `CONTEXTO.md`: panorama vivo do repositorio, decisoes e proximos passos.
2. `docs/GUIA_TECNICO.md`: explicacao dos scripts, colunas, executores e fluxos.
3. `dados/README.md`: schemas dos artefatos JSON internos.
4. `docs/index.html`: painel publico com graficos, tabelas, metricas e aba de documentacao.
5. `docs/RELEVANCIA_TERMOS.md`: termos caracteristicos por categoria + mapa de correlacao.
6. `docs/RELATORIO_ESTADO_ATUAL.md`: diagnostico tecnico/metodologico desta revisao.

## Apps Script

`apps_script/Code.gs` e legado. O fluxo principal atual usa conta de servico com `gspread`.

Manter Apps Script apenas como referencia historica ou alternativa ate decisao de remocao definitiva.

## Privacidade

Nao versionar credenciais, IDs privados de planilha, tokens, URLs privadas de Web App ou arquivos JSON que contenham texto real de chamados.
